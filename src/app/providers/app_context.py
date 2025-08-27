from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..config import settings

class AppContext:
    """Simplified context for single-tenant application"""
    
    def __init__(self):
        self.bucket = settings.minio_bucket
        self.qdrant_collection = "chunks"  # Single collection for all chunks
    
    def get_db_session(self) -> Session:
        """Get database session for the application"""
        return SessionLocal()
    
    def close_session(self, session: Session):
        """Close database session"""
        session.close()
