"""
Database models using SQLAlchemy.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ProcessingTask(Base):
    """Model for tracking video processing tasks."""
    
    __tablename__ = 'processing_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    url = Column(String, nullable=False)
    status = Column(String, default='pending')  # pending, processing, completed, failed
    video_title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    temp_dir = Column(String)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<ProcessingTask(id={self.id}, status={self.status})>"


class RateLimit(Base):
    """Model for rate limiting."""
    
    __tablename__ = 'rate_limits'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    request_count = Column(Integer, default=0)
    window_start = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<RateLimit(user_id={self.user_id}, count={self.request_count})>"