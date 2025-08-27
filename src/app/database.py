from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine.url import make_url
from .config import settings

# Ensure DB exists
app_url = make_url(settings.database_url)
admin_url = app_url.set(database="postgres")
admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
with admin_engine.connect() as conn:
    exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": app_url.database}).scalar()
    if not exists:
        conn.execute(text(f'CREATE DATABASE "{app_url.database}"'))

# Main DB engine
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()

from .models.app_models import *

# Create all tables
Base.metadata.create_all(bind=engine)
