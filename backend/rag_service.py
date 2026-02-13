import google.generativeai as genai
from sqlalchemy.orm import Session
from models import AcademicSource
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class RAGService:
    @staticmethod
    def get_embedding(text: str):
        """Generates a 768-dimension vector using Gemini 004."""
        result = genai.embed_content(
            model="gemini-embedding-001",
            content=text,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return result['embedding']

    @staticmethod
    def find_similar_sources(db: Session, query_text: str, limit: int = 3):
        """Finds the most relevant academic sources using vector similarity."""
        query_embedding = RAGService.get_embedding(query_text)
        
        # Use the <-> operator for L2 distance or <=> for cosine distance
        return db.query(AcademicSource).order_by(
            AcademicSource.embedding.l2_distance(query_embedding)
        ).limit(limit).all()