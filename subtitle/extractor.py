"""
Subtitle extraction and downloading.
"""
import asyncio
import re
from pathlib import Path
from typing import Optional
import aiohttp
import webvtt

from utils.logging import setup_logging

logger = setup_logging(__name__)


class SubtitleExtractor:
    """Extracts and processes subtitles."""
    
    async def download_subtitle(
        self,
        url: str,
        language: str,
        output_path: Path
    ) -> Optional[Path]:
        """
        Download subtitle from URL.
        
        Args:
            url: Subtitle URL
            language: Language code
            output_path: Output path for subtitle file
            
        Returns:
            Path to downloaded subtitle file
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Save original format
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        original_path = output_path.with_suffix('.vtt')
                        original_path.write_text(content, encoding='utf-8')
                        
                        logger.info(f"Subtitle downloaded: {original_path}")
                        return original_path
                    else:
                        logger.error(f"Failed to download subtitle: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to download subtitle: {e}")
            return None
    
    async def convert_to_srt(self, vtt_path: Path) -> Optional[Path]:
        """
        Convert VTT subtitle to SRT format.
        
        Args:
            vtt_path: Path to VTT file
            
        Returns:
            Path to converted SRT file
        """
        try:
            srt_path = vtt_path.with_suffix('.srt')
            
            # Use webvtt-py for conversion
            vtt = webvtt.read(vtt_path)
            vtt.save_as_srt(srt_path)
            
            logger.info(f"Converted to SRT: {srt_path}")
            return srt_path
            
        except Exception as e:
            logger.error(f"Failed to convert to SRT: {e}")
            return None
    
    def enhance_subtitles(self, srt_path: Path) -> Path:
        """
        Enhance subtitle quality.
        
        Args:
            srt_path: Path to SRT file
            
        Returns:
            Path to enhanced SRT file
        """
        try:
            content = srt_path.read_text(encoding='utf-8')
            
            # Remove duplicates
            lines = content.split('\n')
            seen = set()
            unique_lines = []
            for line in lines:
                if line.strip() and line.strip() not in seen:
                    seen.add(line.strip())
                    unique_lines.append(line)
                elif not line.strip():
                    unique_lines.append(line)
            
            content = '\n'.join(unique_lines)
            
            # Merge broken sentences
            content = re.sub(r'(?<=[a-z])\n(?=[a-z])', ' ', content)
            
            # Improve punctuation
            content = re.sub(r'([.!?])([A-Z])', r'\1 \2', content)
            
            # Save enhanced version
            enhanced_path = srt_path.with_stem(srt_path.stem + '_enhanced')
            enhanced_path.write_text(content, encoding='utf-8')
            
            logger.info(f"Subtitle enhanced: {enhanced_path}")
            return enhanced_path
            
        except Exception as e:
            logger.error(f"Failed to enhance subtitle: {e}")
            return srt_path