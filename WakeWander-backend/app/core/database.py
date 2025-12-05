from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()

engine_args = {
    "pool_pre_ping": True,
    "pool_size": 5,
    "max_overflow": 10,
}

if "supabase" in settings.DATABASE_URL:
    engine_args["connect_args"] = {"sslmode": "require"}

engine = create_engine(settings.DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
