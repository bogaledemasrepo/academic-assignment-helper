from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, EmailStr
import google.generativeai as genai
from sqlalchemy.orm import Session
from docx import Document
import fitz 
import httpx
import models, auth, database 
import json, os
from models import AcademicSource
from database import get_db 
import models, auth, database
from rag_service import RAGService


# 1. Initialize DB once
database.init_db()
models.Base.metadata.create_all(bind=database.engine)

# Configure Gemini for Embeddings
genai.configure(api_key="AIzaSyCF5ZEZpeplxplIUgDEQ5hV-H4Qlmn9CCY")

app = FastAPI(title="Academic Assignment Helper")

@app.get("/")
async def root():
    return {"message": "Healthy fast API"}

@app.post("/auth/register")
def register(email: str, password: str, full_name: str, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.Student).filter(models.Student.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Use the direct bcrypt hashing we defined above
    hashed_pw = auth.get_password_hash(password)
    new_student = models.Student(
        email=email, 
        password_hash=hashed_pw, 
        full_name=full_name
    )
    
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return {"message": "Student registered", "user_id": new_student.id}

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@app.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(database.get_db)):
    # Access via request.email and request.password
    user = db.query(models.Student).filter(models.Student.email == request.email).first()
    
    if not user or not auth.verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Helper to extract text based on file type
def extract_text(file: UploadFile):
    content = ""
    if file.filename.endswith(".pdf"):
        doc = fitz.open(stream=file.file.read(), filetype="pdf")
        for page in doc:
            content += page.get_text()
    elif file.filename.endswith(".docx"):
        doc = Document(file.file)
        content = "\n".join([para.text for para in doc.paragraphs])
    else:
        # Fallback for .txt files
        content = file.file.read().decode("utf-8")
    return content

@app.post("/assignments/upload")
async def upload_assignment(
    topic: str,
    academic_level: str,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    # This now extracts the real student from the JWT session
    current_student: models.Student = Depends(auth.get_current_user) 
):
    # 1. Extract text from the file
    text_content = extract_text(file)
    word_count = len(text_content.split())

    # 2. Save to PostgreSQL using current_student.id
    new_assignment = models.Assignment(
        student_id=current_student.id, # <--- SECURE ID
        filename=file.filename,
        original_text=text_content,
        topic=topic,
        academic_level=academic_level,
        word_count=word_count
    )
    
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)

    # 3. Trigger n8n for AI Analysis
    # n8n_webhook_url = "https://mrbg.app.n8n.cloud/webhook/assignment-upload"
    n8n_webhook_url = "http://n8n:5678/webhook-test/assignment-upload"
    async with httpx.AsyncClient() as client:
        try:
            await client.post(n8n_webhook_url, json={
                "assignment_id": new_assignment.id,
                "student_email": current_student.email,
                "text": text_content,
                "topic": topic
            })
        except httpx.RequestError:
            print("⚠️ n8n is offline, but assignment was saved to DB.")

    return {
        "message": "Assignment uploaded successfully",
        "assignment_id": new_assignment.id,
        "student": current_student.full_name
    }

@app.get("/sources", tags=["RAG"])
def search_sources(query: str, db: Session = Depends(database.get_db)):
    """Search academic sources via RAG as required by documentation."""
    results = RAGService.find_similar_sources(db, query)
    return {"results": results}


@app.post("/seed")
async def seed_academic_sources(db: Session = Depends(database.get_db)):
    """
    Seeds the academic_sources table from the sample_academic_sources.json file.
    Generates 768-dim embeddings for each source via Gemini.
    """
    json_path = os.path.join("data", "sample_academic_sources.json")
    
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail=f"JSON file not found at {json_path}")

    try:
        with open(json_path, "r") as f:
            sources_data = json.load(f)

        seeded_count = 0
        for item in sources_data:
            # Prevent duplicate entries
            if db.query(models.AcademicSource).filter_by(title=item['title']).first():
                continue

            # Generate the vector embedding required for RAG search
            embedding_vector = RAGService.get_embedding(item['full_text'])

            new_source = models.AcademicSource(
                title=item['title'],
                authors=item['authors'],
                publication_year=item['publication_year'],
                abstract=item['abstract'],
                full_text=item['full_text'],
                source_type=item['source_type'],
                embedding=embedding_vector # Fits Column(Vector(768))
            )
            db.add(new_source)
            seeded_count += 1

        db.commit()
        return {"message": f"Successfully seeded {seeded_count} sources."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis/{id}", tags=["Assignments"])
def get_analysis_results(
    id: int, 
    db: Session = Depends(database.get_db),
    current_student: models.Student = Depends(auth.get_current_user)
):
    """
    Retrieves analysis results and suggestions for a specific assignment.
    Must be secured with JWT and belong to the requesting student.
    """
    # 1. Fetch the assignment and verify ownership
    assignment = db.query(models.Assignment).filter(
        models.Assignment.id == id,
        models.Assignment.student_id == current_student.id
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found or unauthorized")

    # 2. Fetch the analysis results associated with this assignment
    analysis = db.query(models.AnalysisResult).filter(
        models.AnalysisResult.assignment_id == id
    ).first()

    if not analysis:
        return {
            "assignment_topic": assignment.topic,
            "status": "Processing",
            "message": "AI analysis is still in progress. Please check back shortly."
        }

    # 3. Return structured data as required by the schema
    return {
        "assignment_id": assignment.id,
        "topic": assignment.topic,
        "results": {
            "plagiarism_score": analysis.plagiarism_score,
            "flagged_sections": analysis.flagged_sections,
            "suggested_sources": analysis.suggested_sources,
            "research_suggestions": analysis.research_suggestions,
            "citation_recommendations": analysis.citation_recommendations,
            "confidence_score": analysis.confidence_score,
            "analyzed_at": analysis.analyzed_at
        }
    }