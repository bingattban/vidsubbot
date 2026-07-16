"""
Video downloader using yt-dlp.
"""
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yt_dlp

from utils.logging import setup_logging

logger = setup_logging(__name__)


class VideoDownloader:
    """Handles video downloading using yt-dlp."""
    
    def __init__(self, download_dir: Path) -> None:
        """
        Initialize the downloader.
        
        Args:
            download_dir: Directory for temporary downloads
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_available_formats(
        self, 
        url: str
    ) -> List[Dict[str, str]]:
        """
        Get available video formats for a URL.
        
        Args:
            url: Video URL
            
        Returns:
            List of format dictionaries with resolution and filesize
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                formats = []
                seen_qualities = set()
                
                for fmt in info.get('formats', []):
                    # Filter for video formats only (no audio-only)
                    if fmt.get('vcodec', 'none') == 'none':
                        continue
                    
                    height = fmt.get('height', 0)
                    if not height:
                        continue
                    
                    # Create quality identifier
                    quality_id = f"{height}p"
                    if quality_id in seen_qualities:
                        continue
                    
                    seen_qualities.add(quality_id)
                    
                    filesize = fmt.get('filesize', 0)
                    filesize_str = (
                        f"{filesize / 1024 / 1024:.1f} MB" 
                        if filesize 
                        else "Unknown"
                    )
                    
                    formats.append({
                        'format_id': fmt['format_id'],
                        'resolution': quality_id,
                        'filesize': filesize_str,
                        'ext': fmt.get('ext', 'mp4'),
                    })
                
                # Sort by resolution (highest first)
                formats.sort(
                    key=lambda x: int(x['resolution'].replace('p', '')),
                    reverse=True
                )
                
                return formats
                
        except Exception as e:
            logger.error(f"Failed to get formats: {e}")
            raise
    
    async def download_video(
        self,
        url: str,
        format_id: str,
        progress_callback: Optional[callable] = None
    ) -> Path:
        """
        Download video with specified format.
        
        Args:
            url: Video URL
            format_id: Format identifier to download
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to downloaded video file
        """
        try:
            output_template = str(self.download_dir / "%(title)s.%(ext)s")
            
            def progress_hook(d):
                if d['status'] == 'downloading' and progress_callback:
                    total = d.get('total_bytes', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    if total:
                        progress = (downloaded / total) * 100
                        asyncio.create_task(
                            progress_callback(f"Downloading: {progress:.1f}%")
                        )
            
            ydl_opts = {
                'format': format_id,
                'outtmpl': output_template,
                'progress_hooks': [progress_hook],
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=True)
                video_path = Path(ydl.prepare_filename(info))
                
                logger.info(f"Video downloaded: {video_path}")
                return video_path
                
        except Exception as e:
            logger.error(f"Failed to download video: {e}")
            raise