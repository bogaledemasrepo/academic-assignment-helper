from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base # <--- Make sure this is imported
from sqlalchemy.orm import relationship
import datetime

# This is the "Base" that was missing!
Base = declarative_base() 

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String)
    # ... rest of your student columns