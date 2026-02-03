from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Use Environment Variable with a fallback for local safety
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://mrbg:mrbg@db:5432/academic_helper"
)

# Create the engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create the Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Initializes the database by enabling the pgvector extension.
    This must run before models.Base.metadata.create_all()
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        print("✅ pgvector extension enabled.")

def get_db():
    """
    Dependency to get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()