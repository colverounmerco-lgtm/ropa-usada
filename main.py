from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from config import config
from models import db, Usuario, Prenda, RecargaWallet, RetiroWallet, MovimientoWallet, Mensaje, COMISION_PORCENTAJE
from datetime import datetime
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

# ─── RUTAS PÚBLICAS ───────────────────────────

@app.route('/')
def index():
    categoria  = request.args.get('categoria', '')
    talla      = request.args.get('talla', '')
    precio_max = request.args.get('precio_max', '')

    query = Prenda.query.join(Usuario).filter(
        Prenda.vendido == False,
        Usuario.activo == True,
        Usuario.wallet_saldo > 0
    )
    if categoria:
        query = query.filter(Prenda.categoria == categoria)
    if talla:
        query = query.filter(Prenda.talla == talla)
    if precio_max:
        try:
            query = query.filter(Prenda.precio_vendedor * 1.07 <= float(precio_max))
        except ValueError:
            pass

    prendas    = query.order_by(Prenda.destacado.desc(), Prenda.creado_en.desc()).all()
    categorias = [c[0] for c in db.session.query(Prenda.categoria).join(Usuario).filter(
        Prenda.vendido == False, Usuario.wallet_saldo > 0).distinct().all()]
    tallas     = [t[0] for t in db.session.query(Prenda.talla).join(Usuario).filter(
        Prenda.vendido == False, Usuario.wallet_saldo > 0).distinct().all()]

    return render_template('index.html',
        prendas=prendas, categorias=categorias, tallas=tallas,
        filtro_categoria=categoria, filtro_talla=talla, filtro_precio_max=precio_max
    )


@app.route('/producto/<int:id>')
def producto(id):
    prenda = Prenda.query.get_or_404(id)
    relacionadas = Prenda.query.join(Usuario).filter(
        Prenda.categoria == prenda.categoria,
        Prenda.vendido == False,
        Prenda.id != id,
        Usuario.wallet_saldo > 0
    ).limit(4).all()
    return render_template('producto.html', prenda=prenda, relacionadas=relacionadas)

@app.route('/terminos')
def terminos():
    return render_template('terminos.html')

# ─── AUTENTICACIÓN ────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('usuario_id'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        rol      = request.form.get('rol')
        nombre   = request.form.get('nombre', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not all([rol, nombre, email, password]):
            flash('Completa todos los campos', 'error')
            return render_template('auth/register.html')
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('auth/register.html')
        if Usuario.query.filter_by(email=email).first():
            flash('Este email ya está registrado', 'error')
            return render_template('auth/register.html')

        usuario = Usuario(nombre=nombre, email=email, rol=rol)
        usuario.set_password(password)

        if rol == 'vendedor':
            whatsapp = request.form.get('whatsapp', '').strip()
            tienda   = request.form.get('tienda_nombre', '').strip()
            if not whatsapp:
                flash('Los vendedores deben ingresar su número de WhatsApp', 'error')
                return render_template('auth/register.html')
            usuario.whatsapp      = whatsapp
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

    return render_template('auth/register.html')

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

@app.route('/wallet/retirar', methods=['GET', 'POST'])
@vendedor_requerido
def wallet_retirar():
    vendedor = Usuario.query.get(session['usuario_id'])
    if request.method == 'POST':
        monto           = float(request.form.get('monto', 0))
        datos_bancarios = request.form.get('datos_bancarios', '').strip()

        if monto < 1.0:
            flash('El monto mínimo de retiro es $1.00', 'error')
            return render_template('vendedor/retirar.html', vendedor=vendedor)
        if monto > vendedor.wallet_saldo:
            flash(f'Saldo insuficiente. Tu saldo es ${vendedor.wallet_saldo:.2f}', 'error')
            return render_template('vendedor/retirar.html', vendedor=vendedor)
        if not datos_bancarios:
            flash('Ingresa tus datos bancarios para el retiro', 'error')
            return render_template('vendedor/retirar.html', vendedor=vendedor)

        retiro = RetiroWallet(
            vendedor_id=vendedor.id,
            monto=monto,
            datos_bancarios=datos_bancarios
        )
        db.session.add(retiro)
        db.session.commit()
        flash('✅ Solicitud de retiro enviada. El administrador la procesará pronto.', 'success')
        return redirect(url_for('wallet'))

    return render_template('vendedor/retirar.html', vendedor=vendedor)

# ─── PANEL VENDEDOR ───────────────────────────

@app.route('/mi-tienda')
@vendedor_requerido
def vendedor_dashboard():
    vendedor = Usuario.query.get(session['usuario_id'])
    prendas  = Prenda.query.filter_by(vendedor_id=vendedor.id).order_by(Prenda.creado_en.desc()).all()
    return render_template('vendedor/dashboard.html',
        vendedor=vendedor,
        prendas=prendas,
        disponibles=sum(1 for p in prendas if not p.vendido),
        vendidas=sum(1 for p in prendas if p.vendido)
    )

@app.route('/mi-tienda/agregar', methods=['GET', 'POST'])
@vendedor_requerido
def vendedor_agregar():
    vendedor = Usuario.query.get(session['usuario_id'])
    if not vendedor.puede_vender:
        flash('Necesitas saldo en tu wallet para publicar prendas.', 'error')
        return redirect(url_for('wallet_recargar'))

    if request.method == 'POST':
        imagen = guardar_archivo(request.files.get('imagen'))
        prenda = Prenda(
            vendedor_id     = vendedor.id,
            nombre          = request.form['nombre'],
            descripcion     = request.form['descripcion'],
            precio_vendedor = float(request.form['precio']),
            talla           = request.form['talla'],
            categoria       = request.form['categoria'],
            estado          = request.form['estado'],
            imagen          = imagen,
            destacado       = 'destacado' in request.form
        )
        db.session.add(prenda)
        db.session.commit()
        flash('✅ Prenda publicada exitosamente', 'success')
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
        prenda.nombre          = request.form['nombre']
        prenda.descripcion     = request.form['descripcion']
        prenda.precio_vendedor = float(request.form['precio'])
        prenda.talla           = request.form['talla']
        prenda.categoria       = request.form['categoria']
        prenda.estado          = request.form['estado']
        prenda.destacado       = 'destacado' in request.form
        db.session.commit()
        flash('✅ Prenda actualizada', 'success')
        return redirect(url_for('vendedor_dashboard'))
    return render_template('vendedor/editar.html', prenda=prenda)

@app.route('/mi-tienda/vender/<int:id>', methods=['POST'])
@vendedor_requerido
def vendedor_vender(id):
    prenda   = Prenda.query.get_or_404(id)
    vendedor = Usuario.query.get(session['usuario_id'])

    if prenda.vendedor_id != vendedor.id:
        return redirect(url_for('vendedor_dashboard'))

    if not prenda.vendido:
        comision = prenda.monto_comision
        if vendedor.wallet_saldo < comision:
            flash(f'Saldo insuficiente para cubrir la comisión (${comision:.2f}). Recarga tu wallet.', 'error')
            return redirect(url_for('vendedor_dashboard'))

        prenda.vendido        = True
        vendedor.wallet_saldo = round(vendedor.wallet_saldo - comision, 2)

        mov = MovimientoWallet(
            vendedor_id = vendedor.id,
            tipo        = 'comision',
            monto       = -comision,
            descripcion = f'Comisión 7% por venta de "{prenda.nombre}"'
        )
        db.session.add(mov)

        if vendedor.wallet_saldo <= 0:
            vendedor.wallet_saldo = 0
            flash(f'⚠️ Prenda marcada como vendida. Tu wallet llegó a $0 — recarga para seguir vendiendo.', 'warning')
        else:
            flash(f'✅ Vendida. Comisión descontada: ${comision:.2f}. Saldo restante: ${vendedor.wallet_saldo:.2f}', 'success')
    else:
        prenda.vendido = False
        flash('Prenda marcada como disponible', 'success')

    db.session.commit()
    return redirect(url_for('vendedor_dashboard'))

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
    return render_template('admin/dashboard.html',
        total_usuarios    = Usuario.query.filter(Usuario.rol != 'admin').count(),
        total_vendedores  = Usuario.query.filter_by(rol='vendedor').count(),
        total_compradores = Usuario.query.filter_by(rol='comprador').count(),
        total_prendas     = Prenda.query.count(),
        total_vendidas    = Prenda.query.filter_by(vendido=True).count(),
        recargas_pendientes = recargas_pendientes,
        retiros_pendientes  = retiros_pendientes,
        wallet_total      = db.session.query(db.func.sum(Usuario.wallet_saldo)).scalar() or 0
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

    mov = MovimientoWallet(
        vendedor_id = retiro.vendedor_id,
        tipo        = 'retiro',
        monto       = -retiro.monto,
        descripcion = f'Retiro aprobado por admin'
    )
    db.session.add(mov)
    db.session.commit()
    flash(f'✅ Retiro de ${retiro.monto:.2f} aprobado', 'success')
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
