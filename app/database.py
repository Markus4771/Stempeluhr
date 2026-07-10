import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

ENV_PATHS = [
    Path("/etc/stempeluhr/stempeluhr.env"),
    Path("/opt/stempeluhr/.env"),
]
for ENV_PATH in ENV_PATHS:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
        break

DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql").lower()

if DATABASE_TYPE == "postgresql":
    DB_HOST = os.getenv("DATABASE_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")
    DB_NAME = os.getenv("DATABASE_NAME", "stempeluhr")
    DB_USER = os.getenv("DATABASE_USER", "stempeluhr")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD", "stempeluhr_passwort_aendern")

    DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
    )
else:
    DATABASE_URL = "sqlite:////opt/stempeluhr/data/stempeluhr.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
