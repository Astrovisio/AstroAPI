import os

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

# Ensure data directory exists
os.makedirs("./data/astrovisio_files", exist_ok=True)

DATABASE_URL = "sqlite:///./data/astrovisio_files/prod.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(
    class_=Session, autocommit=False, autoflush=False, bind=engine
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
