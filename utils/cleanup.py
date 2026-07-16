"""
Temporary file cleanup manager.
"""
import asyncio
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from utils.logging import setup_logging

logger = setup_logging(__name__)


class CleanupManager:
    """Manages automatic cleanup of temporary files."""
    
    def __init__(
        self,
        temp_dir: Path,
        cleanup_interval: int = 3600,
        file_lifetime: int = 10800
    ) -> None:
        """
        Initialize cleanup manager.
        
        Args:
            temp_dir: Temporary directory to clean
            cleanup_interval: Cleanup interval in seconds (default: 1 hour)
            file_lifetime: File lifetime in seconds (default: 3 hours)
        """
        self.temp_dir = Path(temp_dir)
        self.cleanup_interval = cleanup_interval
        self.file_lifetime = file_lifetime
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def start(self) -> None:
        """Start the cleanup scheduler."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"Cleanup manager started (interval: {self.cleanup_interval}s, "
            f"lifetime: {self.file_lifetime}s)"
        )
    
    def stop(self) -> None:
        """Stop the cleanup scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Cleanup manager stopped")
    
    async def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        while self._running:
            try:
                await self._cleanup()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup(self) -> None:
        """Perform cleanup of old temporary files."""
        try:
            if not self.temp_dir.exists():
                return
            
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.file_lifetime)
            cleaned_count = 0
            freed_space = 0
            
            for item in self.temp_dir.iterdir():
                try:
                    # Check if item is older than lifetime
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    
                    if mtime < cutoff:
                        if item.is_file():
                            size = item.stat().st_size
                            item.unlink()
                            freed_space += size
                            cleaned_count += 1
                        elif item.is_dir():
                            # Calculate directory size before deletion
                            size = sum(
                                f.stat().st_size
                                for f in item.rglob('*')
                                if f.is_file()
                            )
                            shutil.rmtree(item)
                            freed_space += size
                            cleaned_count += 1
                            
                except Exception as e:
                    logger.warning(f"Failed to clean {item}: {e}")
            
            if cleaned_count > 0:
                freed_mb = freed_space / (1024 * 1024)
                logger.info(
                    f"Cleaned {cleaned_count} items, "
                    f"freed {freed_mb:.1f} MB"
                )
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")