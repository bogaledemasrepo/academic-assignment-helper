import models
from database import engine
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, auth, database # Assuming you have a database.py for session management

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Academic Assignment Helper")

@app.get("/")
async def root():
    return {"message": "Healthy fast API"}

@app.post("/auth/register")
def register(student_data: dict, db: Session = Depends(database.get_db)):
    # Hash password before saving [cite: 16]
    hashed_pwd = auth.get_password_hash(student_data['password'])
    new_student = models.Student(
        email=student_data['email'],
        password_hash=hashed_pwd,
        full_name=student_data.get('full_name')
    )
    db.add(new_student)
    db.commit()
    return {"message": "Student registered successfully"}

@app.post("/auth/login")
def login(credentials: dict, db: Session = Depends(database.get_db)):
    # Validate student credentials [cite: 25]
    user = db.query(models.Student).filter(models.Student.email == credentials['email']).first()
    if not user or not auth.verify_password(credentials['password'], user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Issue JWT on login with permissions [cite: 17, 24]
    access_token = auth.create_access_token(data={"sub": user.email, "role": "student"})
    return {"access_token": access_token, "token_type": "bearer"}