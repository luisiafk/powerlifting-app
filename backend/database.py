import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

database_url_from_env = os.getenv("DATABASE_URL")

if os.getenv("RENDER") and not database_url_from_env:
    raise RuntimeError(
        "DATABASE_URL no esta configurada en Render. "
        "Asocia una base de datos Postgres al servicio para tener persistencia."
    )

DATABASE_URL = database_url_from_env or "sqlite:///./powerlifting.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USING_SQLITE_FALLBACK = not bool(database_url_from_env)

if DATABASE_URL.startswith("sqlite:///"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_info() -> dict:
    """Devuelve datos no sensibles para verificar persistencia en despliegue."""
    backend = "sqlite" if DATABASE_URL.startswith("sqlite:///") else "postgres"

    if backend == "sqlite":
        location = DATABASE_URL.replace("sqlite:///", "")
        return {
            "backend": backend,
            "using_sqlite_fallback": USING_SQLITE_FALLBACK,
            "location": location,
            "persistent_recommended": False,
        }

    # Para Postgres: no exponer credenciales, solo host y nombre de DB.
    safe = DATABASE_URL.split("@")[-1]
    host_and_db = safe.split("?")[0]
    host = host_and_db.split("/")[0]
    db_name = host_and_db.split("/")[-1] if "/" in host_and_db else "unknown"

    return {
        "backend": backend,
        "using_sqlite_fallback": USING_SQLITE_FALLBACK,
        "host": host,
        "database": db_name,
        "persistent_recommended": True,
    }
