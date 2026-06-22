from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from functools import wraps
from config import config
from models import db, Usuario, Prenda, RecargaWallet, RetiroWallet, MovimientoWallet, Mensaje, PreguntaCompra, SolicitudCompra, COMISION_PORCENTAJE
from datetime import datetime, timedelta
import secrets
from sqlalchemy import text, inspect as sa_inspect
import os
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.config['SECRET_KEY']                     = config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI']        = config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH']             = 5 * 1024 * 1024

cloudinary.config(
    cloud_name = config.CLOUDINARY_CLOUD_NAME,
    api_key    = config.CLOUDINARY_API_KEY,
    api_secret = config.CLOUDINARY_API_SECRET
)

EXTENSIONES = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

db.init_app(app)

with app.app_context():
    db.create_all()
    # Migración: agregar columnas de cantidad si no existen
    cols_prendas  = [c['name'] for c in sa_inspect(db.engine).get_columns('prendas')]
    cols_usuarios = [c['name'] for c in sa_inspect(db.engine).get_columns('usuarios')]
    with db.engine.connect() as conn:
        if 'cantidad' not in cols_prendas:
            conn.execute(text("ALTER TABLE prendas ADD COLUMN cantidad INTEGER NOT NULL DEFAULT 1"))
            conn.commit()
        if 'unidades_vendidas' not in cols_prendas:
            conn.execute(text("ALTER TABLE prendas ADD COLUMN unidades_vendidas INTEGER NOT NULL DEFAULT 0"))
            conn.commit()
        if 'ciudad' not in cols_usuarios:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN ciudad VARCHAR(60)"))
            conn.commit()
        for col, ddl in [
            ('pendiente_conf',   'ALTER TABLE prendas ADD COLUMN pendiente_conf BOOLEAN DEFAULT FALSE'),
            ('token_conf',       'ALTER TABLE prendas ADD COLUMN token_conf VARCHAR(40)'),
            ('fecha_pendiente',  'ALTER TABLE prendas ADD COLUMN fecha_pendiente TIMESTAMP'),
            ('comprador_nombre', 'ALTER TABLE prendas ADD COLUMN comprador_nombre VARCHAR(100)'),
            ('disputado',        'ALTER TABLE prendas ADD COLUMN disputado BOOLEAN DEFAULT FALSE'),
        ]:
            if col not in cols_prendas:
                conn.execute(text(ddl))
                conn.commit()
        # comision_retiro en retiros_wallet
        cols_retiros = [c['name'] for c in sa_inspect(db.engine).get_columns('retiros_wallet')]
        if 'comision_retiro' not in cols_retiros:
            conn.execute(text("ALTER TABLE retiros_wallet ADD COLUMN comision_retiro FLOAT DEFAULT 0"))
            conn.commit()
    if not Usuario.query.filter_by(rol='admin').first():
        admin = Usuario(nombre='Admin', email=config.ADMIN_EMAIL, rol='admin')
        admin.set_password(config.ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()

def extension_ok(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENSIONES

def guardar_archivo(archivo):
    if archivo and archivo.filename and extension_ok(archivo.filename):
        resultado = cloudinary.uploader.upload(archivo, folder="ropa-usada")
        return resultado['secure_url']
    return None

# ─── Decoradores ──────────────────────────────
def login_requerido(f):
    @wraps(f)
    def d(*args, **kwargs):
        if not session.get('usuario_id'):
            flash('Debes iniciar sesión', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return d

def vendedor_requerido(f):
    @wraps(f)
    def d(*args, **kwargs):
        if not session.get('usuario_id'):
            return redirect(url_for('login'))
        u = Usuario.query.get(session['usuario_id'])
        if not u or not u.es_vendedor:
            flash('Acceso solo para vendedores', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return d

def admin_requerido(f):
    @wraps(f)
    def d(*args, **kwargs):
        if not session.get('usuario_id'):
            return redirect(url_for('login'))
        u = Usuario.query.get(session['usuario_id'])
        if not u or not u.es_admin:
            flash('Acceso solo para administradores', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return d

def enviar_confirmaciones_pendientes(usuario_id):
    limite = datetime.utcnow() - timedelta(minutes=3)
    pendientes = SolicitudCompra.query.filter(
        SolicitudCompra.comprador_id == usuario_id,
        SolicitudCompra.confirmacion_enviada == False,
        SolicitudCompra.confirmado.is_(None),
        SolicitudCompra.fecha_click <= limite
    ).all()
    for s in pendientes:
        texto = (
            f'__CONFIRMAR__:{s.id}\n'
            f'¿Compraste "{s.prenda.nombre}" (${s.prenda.precio_comprador:.2f})? '
            f'Confirma si realizaste la compra con el vendedor.'
        )
        db.session.add(Mensaje(usuario_id=s.comprador_id, de_admin=True, contenido=texto))
        s.confirmacion_enviada = True
    if pendientes:
        db.session.commit()

@app.before_request
def verificar_confirmaciones():
    uid = session.get('usuario_id')
    if not uid:
        return
    u = Usuario.query.get(uid)
    if u and u.es_comprador:
        enviar_confirmaciones_pendientes(uid)

@app.context_processor
def vars_globales():
    usuario = None
    mensajes_no_leidos = 0
    if session.get('usuario_id'):
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario and not usuario.es_admin:
            mensajes_no_leidos = Mensaje.query.filter_by(
                usuario_id=usuario.id, de_admin=True, leido=False).count()
        elif usuario and usuario.es_admin:
            mensajes_no_leidos = Mensaje.query.filter_by(
                de_admin=False, leido=False).count()
    return {'nombre_tienda': config.NOMBRE_TIENDA, 'usuario_actual': usuario,
            'banco_nombre': config.BANCO_NOMBRE, 'banco_cuenta': config.BANCO_CUENTA,
            'banco_titular': config.BANCO_TITULAR,
            'mensajes_no_leidos': mensajes_no_leidos}

# ─── PWA ─────────────────────────────────────
@app.route('/manifest.json')
def pwa_manifest():
    name = config.NOMBRE_TIENDA
    short = name[:12] if len(name) > 12 else name
    manifest = {
        "name": name,
        "short_name": short,
        "description": f"Compra, vende y ofrece servicios en {name}",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#1E3A5F",
        "theme_color": "#1E3A5F",
        "lang": "es-EC",
        "categories": ["shopping", "business"],
        "icons": [
            {"src": "/static/icons/icon-192.svg", "sizes": "192x192", "type": "image/svg+xml", "purpose": "any maskable"},
            {"src": "/static/icons/icon-512.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"}
        ]
    }
    from flask import make_response
    resp = make_response(jsonify(manifest))
    resp.headers['Content-Type'] = 'application/manifest+json'
    return resp

@app.route('/sw.js')
def pwa_sw():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/.well-known/assetlinks.json')
def pwa_assetlinks():
    package = os.getenv('TWA_PACKAGE', '')
    fingerprint = os.getenv('TWA_FINGERPRINT', '')
    if not package or not fingerprint:
        return jsonify([])
    links = [{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": package,
            "sha256_cert_fingerprints": [fingerprint]
        }
    }]
    return jsonify(links)

# ─── RUTAS PÚBLICAS ───────────────────────────

@app.route('/')
def index():
    busqueda   = request.args.get('q', '').strip()
    categoria  = request.args.get('categoria', '')
    talla      = request.args.get('talla', '')
    precio_max = request.args.get('precio_max', '')
    ciudad     = request.args.get('ciudad', '')

    query = Prenda.query.join(Usuario).filter(
        Prenda.vendido == False,
        Usuario.activo == True,
        Usuario.wallet_saldo >= 1.0
    )
    if busqueda:
        query = query.filter(Prenda.nombre.ilike(f'%{busqueda}%'))
    if categoria:
        query = query.filter(Prenda.categoria == categoria)
    if talla:
        query = query.filter(Prenda.talla == talla)
    if precio_max:
        try:
            query = query.filter(Prenda.precio_vendedor * 1.10 <= float(precio_max))
        except ValueError:
            pass
    if ciudad:
        query = query.filter(Usuario.ciudad == ciudad)

    prendas    = query.order_by(Prenda.destacado.desc(), Prenda.creado_en.desc()).all()
    categorias = [c[0] for c in db.session.query(Prenda.categoria).join(Usuario).filter(
        Prenda.vendido == False, Usuario.wallet_saldo >= 1.0).distinct().all()]
    tallas     = [t[0] for t in db.session.query(Prenda.talla).join(Usuario).filter(
        Prenda.vendido == False, Usuario.wallet_saldo >= 1.0).distinct().all()]
    ciudades   = [c[0] for c in db.session.query(Usuario.ciudad).join(Prenda).filter(
        Prenda.vendido == False, Usuario.wallet_saldo >= 1.0,
        Usuario.ciudad != None, Usuario.ciudad != '').distinct().all()]

    return render_template('index.html',
        prendas=prendas, categorias=categorias, tallas=tallas, ciudades=ciudades,
        filtro_categoria=categoria, filtro_talla=talla, filtro_precio_max=precio_max,
        filtro_ciudad=ciudad, busqueda=busqueda
    )


@app.route('/producto/<int:id>')
def producto(id):
    prenda = Prenda.query.get_or_404(id)
    relacionadas = Prenda.query.join(Usuario).filter(
        Prenda.categoria == prenda.categoria,
        Prenda.vendido == False,
        Prenda.id != id,
        Usuario.wallet_saldo >= 1.0
    ).limit(4).all()
    return render_template('producto.html', prenda=prenda, relacionadas=relacionadas)

@app.route('/comprar/<int:prenda_id>')
@login_requerido
def comprar(prenda_id):
    prenda   = Prenda.query.get_or_404(prenda_id)
    usuario  = Usuario.query.get(session['usuario_id'])
    if prenda.vendido or prenda.cantidad <= 0:
        flash('Este artículo ya no está disponible.', 'error')
        return redirect(url_for('producto', id=prenda_id))

    solicitud = SolicitudCompra(comprador_id=usuario.id, prenda_id=prenda.id)
    db.session.add(solicitud)
    db.session.commit()

    nombre_tienda = config.NOMBRE_TIENDA
    msg = (
        f'Hola! Vi tu publicación *{prenda.nombre}* por ${prenda.precio_comprador:.2f} '
        f'en {nombre_tienda}.\n\n'
        f'Mis datos:\n'
        f'• Nombre: {usuario.nombre}\n'
        f'• WhatsApp: {usuario.whatsapp}\n'
        f'• Ciudad: {usuario.ciudad or "—"}\n'
        f'• Email: {usuario.email}\n\n'
        f'¿Está disponible?'
    )
    import urllib.parse
    wa_url = f'https://wa.me/{prenda.vendedor.whatsapp}?text={urllib.parse.quote(msg)}'
    return redirect(wa_url)

@app.route('/confirmar-compra/<int:solicitud_id>/si')
@login_requerido
def confirmar_compra_si(solicitud_id):
    s       = SolicitudCompra.query.get_or_404(solicitud_id)
    usuario = Usuario.query.get(session['usuario_id'])
    if s.comprador_id != usuario.id:
        flash('No tienes permiso para confirmar esta solicitud.', 'error')
        return redirect(url_for('chat'))
    if s.confirmado is not None:
        flash('Esta solicitud ya fue procesada.', 'info')
        return redirect(url_for('chat'))
    prenda = s.prenda
    if prenda.cantidad <= 0 or prenda.vendido:
        flash('El artículo ya no tiene stock disponible.', 'error')
        s.confirmado = False
        s.fecha_confirmacion = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('chat'))

    prenda.cantidad          -= 1
    prenda.unidades_vendidas += 1
    if prenda.cantidad <= 0:
        prenda.vendido = True

    vendedor = prenda.vendedor
    comision = prenda.monto_comision
    vendedor.wallet_saldo = round(vendedor.wallet_saldo - comision, 2)
    if vendedor.wallet_saldo < 0:
        vendedor.wallet_saldo = 0
    db.session.add(MovimientoWallet(
        vendedor_id = vendedor.id,
        tipo        = 'comision',
        monto       = -comision,
        descripcion = f'Comisión 10% — "{prenda.nombre}" confirmada por comprador {usuario.nombre}'
    ))

    s.confirmado         = True
    s.fecha_confirmacion = datetime.utcnow()

    db.session.add(Mensaje(
        usuario_id = usuario.id,
        de_admin   = True,
        contenido  = f'✅ ¡Gracias por confirmar! La compra de "{prenda.nombre}" quedó registrada.'
    ))
    db.session.commit()
    flash('✅ Compra confirmada. ¡Gracias!', 'success')
    return redirect(url_for('chat'))

@app.route('/confirmar-compra/<int:solicitud_id>/no')
@login_requerido
def confirmar_compra_no(solicitud_id):
    s       = SolicitudCompra.query.get_or_404(solicitud_id)
    usuario = Usuario.query.get(session['usuario_id'])
    if s.comprador_id != usuario.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('chat'))
    if s.confirmado is not None:
        flash('Esta solicitud ya fue procesada.', 'info')
        return redirect(url_for('chat'))

    s.confirmado         = False
    s.fecha_confirmacion = datetime.utcnow()
    db.session.add(Mensaje(
        usuario_id = usuario.id,
        de_admin   = True,
        contenido  = f'Entendido. Si tienes algún problema o dudas, escríbenos aquí y te ayudamos.'
    ))
    db.session.commit()
    flash('Solicitud cancelada.', 'info')
    return redirect(url_for('chat'))

@app.route('/terminos')
def terminos():
    return render_template('terminos.html')

# ─── AUTENTICACIÓN ────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('usuario_id'):
        return redirect(url_for('index'))
    rol_default = request.args.get('rol', 'comprador')
    if request.method == 'POST':
        rol      = request.form.get('rol', 'comprador').strip()
        if rol not in ('vendedor', 'comprador'):
            rol = 'comprador'
        nombre   = request.form.get('nombre', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        whatsapp = request.form.get('whatsapp', '').strip()
        ciudad   = request.form.get('ciudad', '').strip()

        if not all([nombre, email, password, whatsapp, ciudad]):
            flash('Completa todos los campos obligatorios', 'error')
            return render_template('auth/register.html', rol_default=rol)
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('auth/register.html', rol_default=rol)
        if Usuario.query.filter_by(email=email).first():
            flash('Este email ya está registrado', 'error')
            return render_template('auth/register.html', rol_default=rol)

        usuario = Usuario(nombre=nombre, email=email, rol=rol,
                          whatsapp=whatsapp, ciudad=ciudad)
        usuario.set_password(password)

        if rol == 'vendedor':
            tienda = request.form.get('tienda_nombre', '').strip()
            usuario.tienda_nombre = tienda or nombre

        db.session.add(usuario)
        db.session.commit()
        session['usuario_id']  = usuario.id
        session['usuario_rol'] = usuario.rol
        flash(f'¡Bienvenido/a {nombre}!', 'success')

        if rol == 'vendedor':
            flash('Para comenzar a vender, recarga tu wallet con mínimo $1.00', 'info')
            return redirect(url_for('wallet_recargar'))
        return redirect(url_for('index'))

    return render_template('auth/register.html', rol_default=rol_default)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('usuario_id'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        usuario  = Usuario.query.filter_by(email=email).first()

        if not usuario or not usuario.check_password(password):
            flash('Email o contraseña incorrectos', 'error')
            return render_template('auth/login.html')
        if not usuario.activo:
            flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
            return render_template('auth/login.html')

        session['usuario_id']  = usuario.id
        session['usuario_rol'] = usuario.rol

        if usuario.es_admin:
            return redirect(url_for('admin_dashboard'))
        if usuario.es_vendedor:
            return redirect(url_for('vendedor_dashboard'))
        return redirect(url_for('index'))

    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─── WALLET ───────────────────────────────────

@app.route('/wallet')
@vendedor_requerido
def wallet():
    vendedor    = Usuario.query.get(session['usuario_id'])
    movimientos = MovimientoWallet.query.filter_by(vendedor_id=vendedor.id)\
                    .order_by(MovimientoWallet.fecha.desc()).limit(50).all()
    recargas    = RecargaWallet.query.filter_by(vendedor_id=vendedor.id)\
                    .order_by(RecargaWallet.fecha_solicitud.desc()).all()
    retiros     = RetiroWallet.query.filter_by(vendedor_id=vendedor.id)\
                    .order_by(RetiroWallet.fecha_solicitud.desc()).all()
    return render_template('vendedor/wallet.html',
        vendedor=vendedor, movimientos=movimientos,
        recargas=recargas, retiros=retiros)

@app.route('/wallet/recargar', methods=['GET', 'POST'])
@vendedor_requerido
def wallet_recargar():
    vendedor = Usuario.query.get(session['usuario_id'])
    if request.method == 'POST':
        monto = request.form.get('monto', '')
        comprobante = guardar_archivo(request.files.get('comprobante'))

        if not monto or float(monto) < 1.0:
            flash('El monto mínimo de recarga es $1.00', 'error')
            return render_template('vendedor/recargar.html', vendedor=vendedor)
        if not comprobante:
            flash('Debes subir el comprobante de transferencia', 'error')
            return render_template('vendedor/recargar.html', vendedor=vendedor)

        recarga = RecargaWallet(
            vendedor_id=vendedor.id,
            monto=float(monto),
            comprobante=comprobante
        )
        db.session.add(recarga)
        db.session.commit()
        flash('✅ Solicitud de recarga enviada. El administrador la revisará pronto.', 'success')
        return redirect(url_for('wallet'))

    return render_template('vendedor/recargar.html', vendedor=vendedor)

RETIRO_MINIMO   = 5.0
RETIRO_COMISION = 0.04

@app.route('/wallet/retirar', methods=['GET', 'POST'])
@vendedor_requerido
def wallet_retirar():
    vendedor = Usuario.query.get(session['usuario_id'])
    if request.method == 'POST':
        try:
            monto = round(float(request.form.get('monto', 0)), 2)
        except ValueError:
            monto = 0.0
        datos_bancarios = request.form.get('datos_bancarios', '').strip()

        if monto < RETIRO_MINIMO:
            flash(f'El monto mínimo de retiro es ${RETIRO_MINIMO:.2f}', 'error')
            return render_template('vendedor/retirar.html', vendedor=vendedor,
                                   retiro_minimo=RETIRO_MINIMO, retiro_comision=RETIRO_COMISION)
        if monto > vendedor.wallet_saldo:
            flash(f'Saldo insuficiente. Tu saldo es ${vendedor.wallet_saldo:.2f}', 'error')
            return render_template('vendedor/retirar.html', vendedor=vendedor,
                                   retiro_minimo=RETIRO_MINIMO, retiro_comision=RETIRO_COMISION)
        if not datos_bancarios:
            flash('Ingresa tus datos bancarios para el retiro', 'error')
            return render_template('vendedor/retirar.html', vendedor=vendedor,
                                   retiro_minimo=RETIRO_MINIMO, retiro_comision=RETIRO_COMISION)

        comision = round(monto * RETIRO_COMISION, 2)
        retiro = RetiroWallet(
            vendedor_id=vendedor.id,
            monto=monto,
            comision_retiro=comision,
            datos_bancarios=datos_bancarios
        )
        db.session.add(retiro)
        db.session.commit()
        neto = round(monto - comision, 2)
        flash(f'✅ Solicitud de retiro enviada. Recibirás ${neto:.2f} (${monto:.2f} − 4% de comisión).', 'success')
        return redirect(url_for('wallet'))

    return render_template('vendedor/retirar.html', vendedor=vendedor,
                           retiro_minimo=RETIRO_MINIMO, retiro_comision=RETIRO_COMISION)

# ─── HELPERS CONFIRMACIÓN ─────────────────────

def _confirmar_venta(prenda):
    vendedor = prenda.vendedor
    comision = prenda.monto_comision
    vendedor.wallet_saldo = round(vendedor.wallet_saldo - comision, 2)
    if vendedor.wallet_saldo < 0:
        vendedor.wallet_saldo = 0
    mov = MovimientoWallet(
        vendedor_id = vendedor.id,
        tipo        = 'comision',
        monto       = -comision,
        descripcion = f'Comisión 10% — "{prenda.nombre}" (unidad #{prenda.unidades_vendidas})'
    )
    db.session.add(mov)
    prenda.pendiente_conf = False
    if prenda.cantidad <= 0:
        prenda.vendido = True
    db.session.commit()

def auto_confirmar_expirados():
    limite = datetime.utcnow() - timedelta(hours=48)
    expirados = Prenda.query.filter(
        Prenda.pendiente_conf == True,
        Prenda.fecha_pendiente <= limite
    ).all()
    for p in expirados:
        _confirmar_venta(p)

# ─── PANEL VENDEDOR ───────────────────────────

@app.route('/mi-tienda')
@vendedor_requerido
def vendedor_dashboard():
    auto_confirmar_expirados()
    vendedor  = Usuario.query.get(session['usuario_id'])
    prendas   = Prenda.query.filter_by(vendedor_id=vendedor.id).order_by(Prenda.creado_en.desc()).all()
    now       = datetime.utcnow()
    pendientes = []
    disputadas = []
    for p in prendas:
        if p.pendiente_conf and p.fecha_pendiente:
            horas = max(0, 48 - (now - p.fecha_pendiente).total_seconds() / 3600)
            pendientes.append({'prenda': p, 'horas': round(horas, 1)})
        elif p.disputado:
            disputadas.append(p)
    return render_template('vendedor/dashboard.html',
        vendedor=vendedor,
        prendas=prendas,
        pendientes=pendientes,
        disputadas=disputadas,
        disponibles=sum(1 for p in prendas if not p.vendido and not p.pendiente_conf and not p.disputado),
        vendidas=sum(1 for p in prendas if p.vendido),
        total_vendidas=sum(p.unidades_vendidas for p in prendas)
    )

@app.route('/mi-tienda/agregar', methods=['GET', 'POST'])
@vendedor_requerido
def vendedor_agregar():
    vendedor = Usuario.query.get(session['usuario_id'])
    if not vendedor.puede_vender:
        flash('Necesitas mínimo $1.00 en tu wallet para publicar artículos.', 'error')
        return redirect(url_for('wallet_recargar'))

    if request.method == 'POST':
        imagen = guardar_archivo(request.files.get('imagen'))
        prenda = Prenda(
            vendedor_id     = vendedor.id,
            nombre          = request.form['nombre'],
            descripcion     = request.form['descripcion'],
            precio_vendedor = float(request.form['precio']),
            talla           = request.form.get('talla', '').strip(),
            categoria       = request.form['categoria'],
            estado          = request.form['estado'],
            imagen          = imagen,
            cantidad        = max(1, int(request.form.get('cantidad', 1))),
            destacado       = 'destacado' in request.form
        )
        db.session.add(prenda)
        db.session.commit()
        flash('✅ Artículo publicado exitosamente', 'success')
        return redirect(url_for('vendedor_dashboard'))
    return render_template('vendedor/agregar.html')

@app.route('/mi-tienda/editar/<int:id>', methods=['GET', 'POST'])
@vendedor_requerido
def vendedor_editar(id):
    prenda = Prenda.query.get_or_404(id)
    if prenda.vendedor_id != session['usuario_id']:
        return redirect(url_for('vendedor_dashboard'))
    if request.method == 'POST':
        nueva_imagen = guardar_archivo(request.files.get('imagen'))
        if nueva_imagen:
            prenda.imagen = nueva_imagen
        nueva_cantidad = max(0, int(request.form.get('cantidad', prenda.cantidad)))
        prenda.nombre          = request.form['nombre']
        prenda.descripcion     = request.form['descripcion']
        prenda.precio_vendedor = float(request.form['precio'])
        prenda.talla           = request.form.get('talla', '').strip()
        prenda.categoria       = request.form['categoria']
        prenda.estado          = request.form['estado']
        prenda.cantidad        = nueva_cantidad
        prenda.destacado       = 'destacado' in request.form
        if nueva_cantidad > 0 and prenda.vendido:
            prenda.vendido = False
        db.session.commit()
        flash('✅ Artículo actualizado', 'success')
        return redirect(url_for('vendedor_dashboard'))
    return render_template('vendedor/editar.html', prenda=prenda)

@app.route('/mi-tienda/vender/<int:id>', methods=['POST'])
@vendedor_requerido
def vendedor_vender(id):
    prenda   = Prenda.query.get_or_404(id)
    vendedor = Usuario.query.get(session['usuario_id'])

    if prenda.vendedor_id != vendedor.id:
        return redirect(url_for('vendedor_dashboard'))
    if prenda.cantidad <= 0:
        flash('Sin stock disponible.', 'error')
        return redirect(url_for('vendedor_dashboard'))
    if prenda.pendiente_conf:
        flash('Ya hay una venta pendiente de confirmación para este artículo.', 'warning')
        return redirect(url_for('vendedor_dashboard'))

    comprador_nombre = request.form.get('comprador_nombre', '').strip() or 'Comprador'
    token = secrets.token_urlsafe(20)

    prenda.cantidad          -= 1
    prenda.unidades_vendidas += 1
    prenda.pendiente_conf     = True
    prenda.token_conf         = token
    prenda.fecha_pendiente    = datetime.utcnow()
    prenda.comprador_nombre   = comprador_nombre

    db.session.commit()
    flash(f'pendiente:{token}', 'pendiente')
    return redirect(url_for('vendedor_dashboard'))

@app.route('/mi-tienda/cancelar-pendiente/<int:id>', methods=['POST'])
@vendedor_requerido
def vendedor_cancelar_pendiente(id):
    prenda   = Prenda.query.get_or_404(id)
    vendedor = Usuario.query.get(session['usuario_id'])
    if prenda.vendedor_id != vendedor.id:
        return redirect(url_for('vendedor_dashboard'))
    prenda.cantidad          += 1
    prenda.unidades_vendidas  = max(0, prenda.unidades_vendidas - 1)
    prenda.pendiente_conf     = False
    prenda.token_conf         = None
    prenda.fecha_pendiente    = None
    prenda.comprador_nombre   = None
    db.session.commit()
    flash('Venta cancelada. El artículo vuelve al catálogo.', 'info')
    return redirect(url_for('vendedor_dashboard'))

@app.route('/confirmar/<token>', methods=['GET', 'POST'])
def confirmar_venta(token):
    prenda = Prenda.query.filter_by(token_conf=token).first_or_404()

    if not prenda.pendiente_conf:
        resultado = 'ya_disputado' if prenda.disputado else 'ya_confirmado'
        return render_template('confirmar.html', prenda=prenda, resultado=resultado, horas=None)

    # Auto-confirm si pasaron 48h
    if prenda.fecha_pendiente:
        delta = datetime.utcnow() - prenda.fecha_pendiente
        if delta.total_seconds() > 48 * 3600:
            _confirmar_venta(prenda)
            return render_template('confirmar.html', prenda=prenda, resultado='auto_confirmado', horas=None)

    if request.method == 'POST':
        accion = request.form.get('accion')
        if accion == 'confirmar':
            _confirmar_venta(prenda)
            return render_template('confirmar.html', prenda=prenda, resultado='confirmado', horas=None)
        elif accion == 'disputar':
            prenda.disputado      = True
            prenda.pendiente_conf = False
            db.session.commit()
            return render_template('confirmar.html', prenda=prenda, resultado='disputado', horas=None)

    horas = max(0, 48 - (datetime.utcnow() - prenda.fecha_pendiente).total_seconds() / 3600)
    return render_template('confirmar.html', prenda=prenda, resultado=None, horas=round(horas, 1))

@app.route('/mi-tienda/eliminar/<int:id>', methods=['POST'])
@vendedor_requerido
def vendedor_eliminar(id):
    prenda = Prenda.query.get_or_404(id)
    if prenda.vendedor_id != session['usuario_id']:
        return redirect(url_for('vendedor_dashboard'))
    db.session.delete(prenda)
    db.session.commit()
    flash('🗑️ Prenda eliminada', 'success')
    return redirect(url_for('vendedor_dashboard'))

# ─── PANEL ADMIN ──────────────────────────────

@app.route('/admin')
@admin_requerido
def admin_dashboard():
    recargas_pendientes = RecargaWallet.query.filter_by(estado='pendiente').count()
    retiros_pendientes  = RetiroWallet.query.filter_by(estado='pendiente').count()
    disputas_pendientes = Prenda.query.filter_by(disputado=True).count()
    return render_template('admin/dashboard.html',
        total_usuarios      = Usuario.query.filter(Usuario.rol != 'admin').count(),
        total_vendedores    = Usuario.query.filter_by(rol='vendedor').count(),
        total_compradores   = Usuario.query.filter_by(rol='comprador').count(),
        total_prendas       = Prenda.query.count(),
        total_vendidas      = Prenda.query.filter_by(vendido=True).count(),
        recargas_pendientes = recargas_pendientes,
        retiros_pendientes  = retiros_pendientes,
        disputas_pendientes = disputas_pendientes,
        wallet_total        = db.session.query(db.func.sum(Usuario.wallet_saldo)).scalar() or 0
    )

@app.route('/admin/usuarios')
@admin_requerido
def admin_usuarios():
    usuarios = Usuario.query.filter(Usuario.rol != 'admin').order_by(Usuario.creado_en.desc()).all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/toggle/<int:id>', methods=['POST'])
@admin_requerido
def admin_toggle_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    usuario.activo = not usuario.activo
    db.session.commit()
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/recargas')
@admin_requerido
def admin_recargas():
    recargas = RecargaWallet.query.order_by(
        RecargaWallet.estado == 'pendiente',
        RecargaWallet.fecha_solicitud.desc()
    ).all()
    return render_template('admin/recargas.html', recargas=recargas)

@app.route('/admin/recargas/aprobar/<int:id>', methods=['POST'])
@admin_requerido
def admin_aprobar_recarga(id):
    recarga = RecargaWallet.query.get_or_404(id)
    if recarga.estado != 'pendiente':
        flash('Esta recarga ya fue procesada', 'error')
        return redirect(url_for('admin_recargas'))

    recarga.estado           = 'aprobada'
    recarga.fecha_resolucion = datetime.utcnow()
    recarga.vendedor.wallet_saldo = round(recarga.vendedor.wallet_saldo + recarga.monto, 2)

    mov = MovimientoWallet(
        vendedor_id = recarga.vendedor_id,
        tipo        = 'recarga',
        monto       = recarga.monto,
        descripcion = f'Recarga aprobada por admin'
    )
    db.session.add(mov)
    db.session.commit()
    flash(f'✅ Recarga de ${recarga.monto:.2f} aprobada para {recarga.vendedor.nombre}', 'success')
    return redirect(url_for('admin_recargas'))

@app.route('/admin/recargas/rechazar/<int:id>', methods=['POST'])
@admin_requerido
def admin_rechazar_recarga(id):
    recarga          = RecargaWallet.query.get_or_404(id)
    recarga.estado   = 'rechazada'
    recarga.admin_nota = request.form.get('nota', '')
    recarga.fecha_resolucion = datetime.utcnow()
    db.session.commit()
    flash(f'Recarga rechazada', 'success')
    return redirect(url_for('admin_recargas'))

@app.route('/admin/retiros')
@admin_requerido
def admin_retiros():
    retiros = RetiroWallet.query.order_by(
        RetiroWallet.estado == 'pendiente',
        RetiroWallet.fecha_solicitud.desc()
    ).all()
    return render_template('admin/retiros.html', retiros=retiros)

@app.route('/admin/retiros/aprobar/<int:id>', methods=['POST'])
@admin_requerido
def admin_aprobar_retiro(id):
    retiro = RetiroWallet.query.get_or_404(id)
    if retiro.estado != 'pendiente':
        flash('Este retiro ya fue procesado', 'error')
        return redirect(url_for('admin_retiros'))
    if retiro.vendedor.wallet_saldo < retiro.monto:
        flash('El vendedor no tiene saldo suficiente', 'error')
        return redirect(url_for('admin_retiros'))

    retiro.estado            = 'aprobado'
    retiro.fecha_resolucion  = datetime.utcnow()
    retiro.vendedor.wallet_saldo = round(retiro.vendedor.wallet_saldo - retiro.monto, 2)
    comision = retiro.comision_retiro or 0.0
    neto     = round(retiro.monto - comision, 2)

    mov = MovimientoWallet(
        vendedor_id = retiro.vendedor_id,
        tipo        = 'retiro',
        monto       = -retiro.monto,
        descripcion = f'Retiro aprobado — neto ${neto:.2f} (comisión 4%: ${comision:.2f})'
    )
    db.session.add(mov)
    db.session.commit()
    flash(f'✅ Retiro aprobado. Vendedor recibe ${neto:.2f} (comisión ${comision:.2f})', 'success')
    return redirect(url_for('admin_retiros'))

@app.route('/admin/retiros/rechazar/<int:id>', methods=['POST'])
@admin_requerido
def admin_rechazar_retiro(id):
    retiro           = RetiroWallet.query.get_or_404(id)
    retiro.estado    = 'rechazado'
    retiro.admin_nota = request.form.get('nota', '')
    retiro.fecha_resolucion = datetime.utcnow()
    db.session.commit()
    flash('Retiro rechazado', 'success')
    return redirect(url_for('admin_retiros'))

@app.route('/admin/prendas')
@admin_requerido
def admin_prendas():
    prendas = Prenda.query.order_by(Prenda.creado_en.desc()).all()
    return render_template('admin/prendas.html', prendas=prendas)

@app.route('/admin/prendas/eliminar/<int:id>', methods=['POST'])
@admin_requerido
def admin_eliminar_prenda(id):
    prenda = Prenda.query.get_or_404(id)
    db.session.delete(prenda)
    db.session.commit()
    flash('🗑️ Prenda eliminada', 'success')
    return redirect(url_for('admin_prendas'))

@app.route('/admin/disputas')
@admin_requerido
def admin_disputas():
    disputas = Prenda.query.filter_by(disputado=True).order_by(Prenda.fecha_pendiente.desc()).all()
    return render_template('admin/disputas.html', disputas=disputas)

@app.route('/admin/disputas/<int:id>/confirmar', methods=['POST'])
@admin_requerido
def admin_disputas_confirmar(id):
    prenda = Prenda.query.get_or_404(id)
    _confirmar_venta(prenda)
    prenda.disputado = False
    db.session.commit()
    flash(f'✅ Venta de "{prenda.nombre}" confirmada. Comisión descontada al vendedor.', 'success')
    return redirect(url_for('admin_disputas'))

@app.route('/admin/disputas/<int:id>/cancelar', methods=['POST'])
@admin_requerido
def admin_disputas_cancelar(id):
    prenda = Prenda.query.get_or_404(id)
    prenda.cantidad          += 1
    prenda.unidades_vendidas  = max(0, prenda.unidades_vendidas - 1)
    prenda.disputado          = False
    prenda.vendido            = False
    prenda.token_conf         = None
    prenda.comprador_nombre   = None
    prenda.fecha_pendiente    = None
    db.session.commit()
    flash(f'❌ Venta cancelada. "{prenda.nombre}" vuelve al catálogo sin cargo al vendedor.', 'info')
    return redirect(url_for('admin_disputas'))

# ─── ADMIN PREGUNTAS ──────────────────────────

@app.route('/admin/preguntas', methods=['GET', 'POST'])
@admin_requerido
def admin_preguntas():
    if request.method == 'POST':
        texto = request.form.get('texto', '').strip()
        if texto:
            orden = db.session.query(db.func.max(PreguntaCompra.orden)).scalar() or 0
            db.session.add(PreguntaCompra(texto=texto, orden=orden + 1))
            db.session.commit()
            flash('✅ Pregunta añadida', 'success')
        return redirect(url_for('admin_preguntas'))
    preguntas = PreguntaCompra.query.order_by(PreguntaCompra.orden).all()
    return render_template('admin/preguntas.html', preguntas=preguntas)

@app.route('/admin/preguntas/<int:id>/eliminar', methods=['POST'])
@admin_requerido
def admin_preguntas_eliminar(id):
    p = PreguntaCompra.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Pregunta eliminada', 'info')
    return redirect(url_for('admin_preguntas'))

@app.route('/admin/preguntas/<int:id>/toggle', methods=['POST'])
@admin_requerido
def admin_preguntas_toggle(id):
    p = PreguntaCompra.query.get_or_404(id)
    p.activa = not p.activa
    db.session.commit()
    return redirect(url_for('admin_preguntas'))

# ─── CHAT ─────────────────────────────────────

@app.route('/chat')
@login_requerido
def chat():
    usuario = Usuario.query.get(session['usuario_id'])
    if usuario.es_admin:
        return redirect(url_for('admin_mensajes'))
    Mensaje.query.filter_by(usuario_id=usuario.id, de_admin=True, leido=False).update({'leido': True})
    db.session.commit()
    mensajes = Mensaje.query.filter_by(usuario_id=usuario.id).order_by(Mensaje.fecha.asc()).all()
    return render_template('chat.html', mensajes=mensajes, usuario=usuario)

@app.route('/chat/enviar', methods=['POST'])
@login_requerido
def chat_enviar():
    usuario = Usuario.query.get(session['usuario_id'])
    contenido = request.form.get('contenido', '').strip()
    if contenido:
        msg = Mensaje(usuario_id=usuario.id, de_admin=False, contenido=contenido)
        db.session.add(msg)
        db.session.commit()
    return redirect(url_for('chat'))

@app.route('/admin/mensajes')
@admin_requerido
def admin_mensajes():
    subq = db.session.query(Mensaje.usuario_id).distinct().subquery()
    usuarios = Usuario.query.filter(Usuario.id.in_(subq)).all()
    conversaciones = []
    for u in usuarios:
        no_leidos = Mensaje.query.filter_by(usuario_id=u.id, de_admin=False, leido=False).count()
        ultimo = Mensaje.query.filter_by(usuario_id=u.id).order_by(Mensaje.fecha.desc()).first()
        conversaciones.append({'usuario': u, 'no_leidos': no_leidos, 'ultimo': ultimo})
    conversaciones.sort(key=lambda x: x['ultimo'].fecha, reverse=True)
    return render_template('admin/mensajes.html', conversaciones=conversaciones)

@app.route('/admin/mensajes/<int:usuario_id>', methods=['GET', 'POST'])
@admin_requerido
def admin_chat_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if request.method == 'POST':
        contenido = request.form.get('contenido', '').strip()
        if contenido:
            msg = Mensaje(usuario_id=usuario_id, de_admin=True, contenido=contenido)
            db.session.add(msg)
            db.session.commit()
        return redirect(url_for('admin_chat_usuario', usuario_id=usuario_id))
    Mensaje.query.filter_by(usuario_id=usuario_id, de_admin=False, leido=False).update({'leido': True})
    db.session.commit()
    mensajes = Mensaje.query.filter_by(usuario_id=usuario_id).order_by(Mensaje.fecha.asc()).all()
    return render_template('admin/chat_usuario.html', mensajes=mensajes, usuario=usuario)

if __name__ == '__main__':
    app.run(debug=config.DEBUG, port=5000)
