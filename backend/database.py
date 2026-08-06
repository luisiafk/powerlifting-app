"""Configuración de la base de datos."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

database_url_from_env = os.getenv("DATABASE_URL")

if not database_url_from_env:
    raise RuntimeError(
        "DATABASE_URL no está configurada. "
        "En Render: agrega la variable de entorno con tu URL de PostgreSQL."
    )

# Render usa postgresql://, pero algunas versiones antiguas usan postgres://
database_url = database_url_from_env
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Crear engine
engine = create_engine(
    database_url,
    pool_pre_ping=True,  # Verifica conexión antes de usarla
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Generador de sesiones para las rutas."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
