"""
Video metadata extraction using yt-dlp.
"""
import asyncio
from typing import Dict, Optional
import yt_dlp

from utils.logging import setup_logging

logger = setup_logging(__name__)


class MetadataExtractor:
    """Extracts video metadata using yt-dlp."""
    
    async def extract_metadata(self, url: str) -> Dict[str, str]:
        """
        Extract video metadata.
        
        Args:
            url: Video URL
            
        Returns:
            Dictionary with title and duration
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                duration = info.get('duration', 0)
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                seconds = duration % 60
                
                if hours > 0:
                    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes}:{seconds:02d}"
                
                metadata = {
                    'title': info.get('title', 'Unknown'),
                    'duration': duration_str,
                }
                
                logger.info(f"Metadata extracted: {metadata['title']}")
                return metadata
                
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            raise