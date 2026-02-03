from fastapi import FastAPI

app = FastAPI(title="Academic Assignment Helper")

@app.get("/")
async def root():
    return {"message": "hallo fast API"}

# This will later house your /auth/login and /upload routes [cite: 24, 31]