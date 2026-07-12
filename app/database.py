import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

GENERAL_ENV_PATHS = [
    Path("/etc/stempeluhr/stempeluhr.env"),
    Path("/opt/stempeluhr/.env"),
]
DATABASE_SECRET_PATH = Path("/etc/stempeluhr/secrets/database.conf")

for env_path in GENERAL_ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path, override=False)
        break

# Secrets überschreiben gleichnamige allgemeine Variablen. Dadurch bleiben alte
# Installationen kompatibel, während neue Installationen das Passwort getrennt
# und mit strengeren Dateirechten verwalten.
if DATABASE_SECRET_PATH.exists():
    load_dotenv(DATABASE_SECRET_PATH, override=True)

DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql").lower()

if DATABASE_TYPE == "postgresql":
    DB_HOST = os.getenv("DATABASE_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DATABASE_PORT", "5432"))
    DB_NAME = os.getenv("DATABASE_NAME", "stempeluhr")
    DB_USER = os.getenv("DATABASE_USER", "stempeluhr")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "")

    DATABASE_URL = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

    connect_args = {}
    if DB_HOST in {"127.0.0.1", "localhost"}:
        connect_args["sslmode"] = "disable"

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
        connect_args=connect_args,
    )
else:
    DATABASE_URL = "sqlite:////opt/stempeluhr/data/stempeluhr.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
