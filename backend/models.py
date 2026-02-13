from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime ,TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector # Required for the RAG embedding column
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String)
    student_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    assignments = relationship("Assignment", back_populates="student")

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    filename = Column(String)
    original_text = Column(Text)
    topic = Column(String)
    academic_level = Column(String)
    word_count = Column(Integer)
    uploaded_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="assignments")
    analysis = relationship("AnalysisResult", back_populates="assignment", uselist=False)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    suggested_sources = Column(JSONB)
    plagiarism_score = Column(Float)
    flagged_sections = Column(JSONB)
    research_suggestions = Column(Text)
    citation_recommendations = Column(Text)
    confidence_score = Column(Float)
    analyzed_at = Column(TIMESTAMP,  server_default=func.now())

    assignment = relationship("Assignment", back_populates="analysis")


class AcademicSource(Base):
    __tablename__ = "academic_sources"
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    authors = Column(String)
    publication_year = Column(Integer)
    abstract = Column(Text)
    full_text = Column(Text)
    source_type = Column(String)
    embedding = Column(Vector(768))