import os
import sys
from dotenv import load_dotenv

load_dotenv()

def get_env(key, default=None, required=True):
    valor = os.getenv(key, default)
    if required and not valor:
        print(f"❌ Falta la variable de entorno: {key}")
        print(f"   Agrégala a tu archivo .env")
        sys.exit(1)
    return valor

class Config:
    SECRET_KEY     = get_env("SECRET_KEY")
    ADMIN_EMAIL    = get_env("ADMIN_EMAIL")
    ADMIN_PASSWORD = get_env("ADMIN_PASSWORD")
    NOMBRE_TIENDA  = get_env("NOMBRE_TIENDA", default="Mi Marketplace", required=False)
    BANCO_NOMBRE   = get_env("BANCO_NOMBRE", default="Banco XYZ", required=False)
    BANCO_CUENTA   = get_env("BANCO_CUENTA", default="0000000000", required=False)
    BANCO_TITULAR  = get_env("BANCO_TITULAR", default="Tu Nombre", required=False)
    DEBUG          = get_env("DEBUG", default="false", required=False).lower() == "true"

    CLOUDINARY_CLOUD_NAME = get_env("CLOUDINARY_CLOUD_NAME", required=False)
    CLOUDINARY_API_KEY    = get_env("CLOUDINARY_API_KEY", required=False)
    CLOUDINARY_API_SECRET = get_env("CLOUDINARY_API_SECRET", required=False)

    # Railway provee postgres://, convertir a postgresql+pg8000:// para producción
    _db_url = get_env("DATABASE_URL", default="sqlite:///ropa.db", required=False)
    if _db_url and _db_url.startswith("postgres://"):
        DATABASE_URL = _db_url.replace("postgres://", "postgresql+pg8000://", 1)
    elif _db_url and _db_url.startswith("postgresql://"):
        DATABASE_URL = _db_url.replace("postgresql://", "postgresql+pg8000://", 1)
    else:
        DATABASE_URL = _db_url or "sqlite:///ropa.db"

config = Config()
