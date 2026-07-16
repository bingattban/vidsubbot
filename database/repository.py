"""
Database repository for managing data persistence.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.models import Base, ProcessingTask, RateLimit
from utils.logging import setup_logging

logger = setup_logging(__name__)


class DatabaseRepository:
    """Repository for database operations."""
    
    def __init__(self, session_factory: async_sessionmaker) -> None:
        """
        Initialize repository.
        
        Args:
            session_factory: Async session factory
        """
        self.session_factory = session_factory
    
    async def initialize(self) -> None:
        """Create database tables."""
        async with self.session_factory() as session:
            async with session.bind.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    async def create_task(
        self,
        user_id: int,
        url: str,
        temp_dir: str
    ) -> ProcessingTask:
        """
        Create a new processing task.
        
        Args:
            user_id: Telegram user ID
            url: Video URL
            temp_dir: Temporary directory path
            
        Returns:
            Created task
        """
        async with self.session_factory() as session:
            task = ProcessingTask(
                user_id=user_id,
                url=url,
                temp_dir=temp_dir,
                status='pending'
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task
    
    async def update_task_status(
        self,
        task_id: int,
        status: str,
        video_title: Optional[str] = None
    ) -> None:
        """
        Update task status.
        
        Args:
            task_id: Task ID
            status: New status
            video_title: Optional video title
        """
        async with self.session_factory() as session:
            stmt = update(ProcessingTask).where(
                ProcessingTask.id == task_id
            ).values(status=status)
            
            if video_title:
                stmt = stmt.values(video_title=video_title)
            
            if status == 'completed':
                stmt = stmt.values(completed_at=datetime.utcnow())
            
            await session.execute(stmt)
            await session.commit()
    
    async def get_user_tasks(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[ProcessingTask]:
        """
        Get recent tasks for a user.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of tasks to return
            
        Returns:
            List of tasks
        """
        async with self.session_factory() as session:
            stmt = (
                select(ProcessingTask)
                .where(ProcessingTask.user_id == user_id)
                .order_by(ProcessingTask.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def check_rate_limit(
        self,
        user_id: int,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Check if user is within rate limit.
        
        Args:
            user_id: Telegram user ID
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        async with self.session_factory() as session:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)
            
            # Get or create rate limit record
            stmt = select(RateLimit).where(
                RateLimit.user_id == user_id,
                RateLimit.window_start >= window_start
            )
            result = await session.execute(stmt)
            rate_limit = result.scalar_one_or_none()
            
            if not rate_limit:
                rate_limit = RateLimit(
                    user_id=user_id,
                    request_count=1,
                    window_start=now
                )
                session.add(rate_limit)
                await session.commit()
                return True
            
            if rate_limit.request_count >= max_requests:
                return False
            
            rate_limit.request_count += 1
            await session.commit()
            return True
    
    async def cleanup_old_tasks(self, hours: int = 3) -> None:
        """
        Remove old completed tasks.
        
        Args:
            hours: Age in hours after which to remove tasks
        """
        async with self.session_factory() as session:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            stmt = delete(ProcessingTask).where(
                ProcessingTask.created_at < cutoff
            )
            await session.execute(stmt)
            
            # Also cleanup rate limits
            stmt = delete(RateLimit).where(
                RateLimit.window_start < cutoff
            )
            await session.execute(stmt)
            
            await session.commit()