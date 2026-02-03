from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Important: "db" matches the service name in docker-compose.yml
SQLALCHEMY_DATABASE_URL = "postgresql://student:secure_password@db:5432/academic_helper"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()