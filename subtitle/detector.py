"""
Subtitle detection for videos.
"""
import asyncio
from typing import Dict, List, Optional
import yt_dlp

from utils.logging import setup_logging

logger = setup_logging(__name__)


class SubtitleDetector:
    """Detects available subtitles for videos."""
    
    SUPPORTED_FORMATS = ['srt', 'vtt', 'ass', 'ssa', 'ttml', 'webvtt']
    
    async def detect_subtitles(self, url: str) -> Dict[str, List[Dict]]:
        """
        Detect available subtitles for a video URL.
        
        Args:
            url: Video URL
            
        Returns:
            Dictionary with subtitle information by language
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'writesubtitles': False,
                'writeautomaticsub': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                subtitles = {}
                
                # Check manual subtitles
                if info.get('subtitles'):
                    for lang, subs in info['subtitles'].items():
                        subtitles[lang] = [
                            {
                                'url': sub['url'],
                                'format': sub.get('ext', 'vtt'),
                                'type': 'manual'
                            }
                            for sub in subs
                            if sub.get('ext', 'vtt') in self.SUPPORTED_FORMATS
                        ]
                
                # Check automatic captions
                if info.get('automatic_captions'):
                    for lang, subs in info['automatic_captions'].items():
                        if lang not in subtitles:
                            subtitles[lang] = []
                        subtitles[lang].extend([
                            {
                                'url': sub['url'],
                                'format': sub.get('ext', 'vtt'),
                                'type': 'auto'
                            }
                            for sub in subs
                            if sub.get('ext', 'vtt') in self.SUPPORTED_FORMATS
                        ])
                
                logger.info(f"Detected subtitles for languages: {list(subtitles.keys())}")
                return subtitles
                
        except Exception as e:
            logger.error(f"Failed to detect subtitles: {e}")
            raise
    
    def has_arabic(self, subtitles: Dict[str, List[Dict]]) -> bool:
        """
        Check if Arabic subtitles are available.
        
        Args:
            subtitles: Dictionary of detected subtitles
            
        Returns:
            True if Arabic subtitles found
        """
        arabic_codes = ['ar', 'ara', 'arabic', 'Arabic', 'العربية']
        return any(lang in arabic_codes for lang in subtitles.keys())