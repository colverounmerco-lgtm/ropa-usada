from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Mensaje(db.Model):
    __tablename__ = "mensajes"

    id         = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    de_admin   = db.Column(db.Boolean, default=False)
    contenido  = db.Column(db.Text, nullable=False)
    leido      = db.Column(db.Boolean, default=False)
    fecha      = db.Column(db.DateTime, default=datetime.utcnow)

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol           = db.Column(db.String(20), nullable=False)
    whatsapp      = db.Column(db.String(30), nullable=True)
    tienda_nombre = db.Column(db.String(100), nullable=True)
    ciudad        = db.Column(db.String(60), nullable=True)
    wallet_saldo  = db.Column(db.Float, default=0.0)
    activo        = db.Column(db.Boolean, default=True)
    creado_en     = db.Column(db.DateTime, default=datetime.utcnow)

    prendas   = db.relationship("Prenda", backref="vendedor", lazy=True)
    recargas  = db.relationship("RecargaWallet", backref="vendedor", lazy=True)
    retiros   = db.relationship("RetiroWallet", backref="vendedor", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def es_vendedor(self):
        return self.rol == "vendedor"

    @property
    def es_comprador(self):
        return self.rol == "comprador"

    @property
    def es_admin(self):
        return self.rol == "admin"

    @property
    def puede_vender(self):
        return self.wallet_saldo >= 1.0


COMISION_PORCENTAJE = 0.10


class Prenda(db.Model):
    __tablename__ = "prendas"

    id               = db.Column(db.Integer, primary_key=True)
    vendedor_id      = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    nombre           = db.Column(db.String(100), nullable=False)
    descripcion      = db.Column(db.Text, nullable=False)
    precio_vendedor  = db.Column(db.Float, nullable=False)
    talla            = db.Column(db.String(10), nullable=False)
    categoria        = db.Column(db.String(50), nullable=False)
    estado           = db.Column(db.String(20), nullable=False)
    imagen            = db.Column(db.String(255), nullable=True)
    cantidad          = db.Column(db.Integer, default=1, nullable=False)
    unidades_vendidas = db.Column(db.Integer, default=0, nullable=False)
    vendido           = db.Column(db.Boolean, default=False)
    destacado         = db.Column(db.Boolean, default=False)
    creado_en         = db.Column(db.DateTime, default=datetime.utcnow)
    # Doble confirmación de venta
    pendiente_conf    = db.Column(db.Boolean, default=False)
    token_conf        = db.Column(db.String(40), nullable=True)
    fecha_pendiente   = db.Column(db.DateTime, nullable=True)
    comprador_nombre  = db.Column(db.String(100), nullable=True)
    disputado         = db.Column(db.Boolean, default=False)

    @property
    def precio_comprador(self):
        return round(self.precio_vendedor * (1 + COMISION_PORCENTAJE), 2)

    @property
    def monto_comision(self):
        return round(self.precio_vendedor * COMISION_PORCENTAJE, 2)

    @property
    def imagen_url(self):
        if self.imagen:
            return self.imagen if self.imagen.startswith('http') else f"/static/uploads/{self.imagen}"
        return "/static/img/sin-foto.png"

    @property
    def estado_badge(self):
        return {"Excelente": "badge-verde", "Muy bueno": "badge-azul", "Bueno": "badge-amarillo"}.get(self.estado, "badge-gris")


class RecargaWallet(db.Model):
    __tablename__ = "recargas_wallet"

    id              = db.Column(db.Integer, primary_key=True)
    vendedor_id     = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    monto           = db.Column(db.Float, nullable=False)
    comprobante     = db.Column(db.String(255), nullable=False)
    estado          = db.Column(db.String(20), default="pendiente")  # pendiente/aprobada/rechazada
    admin_nota      = db.Column(db.Text, nullable=True)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)


class RetiroWallet(db.Model):
    __tablename__ = "retiros_wallet"

    id               = db.Column(db.Integer, primary_key=True)
    vendedor_id      = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    monto            = db.Column(db.Float, nullable=False)
    datos_bancarios  = db.Column(db.Text, nullable=False)
    estado           = db.Column(db.String(20), default="pendiente")  # pendiente/aprobado/rechazado
    admin_nota       = db.Column(db.Text, nullable=True)
    comision_retiro  = db.Column(db.Float, default=0.0)
    fecha_solicitud  = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)


class MovimientoWallet(db.Model):
    __tablename__ = "movimientos_wallet"

    id          = db.Column(db.Integer, primary_key=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    tipo        = db.Column(db.String(20), nullable=False)  # recarga/comision/retiro
    monto       = db.Column(db.Float, nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)
    fecha       = db.Column(db.DateTime, default=datetime.utcnow)


class PreguntaCompra(db.Model):
    __tablename__ = "preguntas_compra"

    id     = db.Column(db.Integer, primary_key=True)
    texto  = db.Column(db.String(200), nullable=False)
    orden  = db.Column(db.Integer, default=0)
    activa = db.Column(db.Boolean, default=True)
