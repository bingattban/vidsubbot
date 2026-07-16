"""
Subtitle generation from audio using speech recognition and translation.
"""
import asyncio
from pathlib import Path
from typing import Optional
import ffmpeg

from speech.recognizer import SpeechRecognizer
from translation.translator import TranslationEngine
from utils.logging import setup_logging

logger = setup_logging(__name__)


class SubtitleGenerator:
    """Generates subtitles from video/audio files."""
    
    def __init__(
        self,
        speech_recognizer: SpeechRecognizer,
        translation_engine: TranslationEngine
    ) -> None:
        """
        Initialize subtitle generator.
        
        Args:
            speech_recognizer: Speech recognition service
            translation_engine: Translation service
        """
        self.speech_recognizer = speech_recognizer
        self.translation_engine = translation_engine
    
    async def extract_audio(
        self,
        video_path: Path,
        output_path: Path,
        progress_callback: Optional[callable] = None
    ) -> Path:
        """
        Extract audio from video file.
        
        Args:
            video_path: Path to video file
            output_path: Path for extracted audio
            progress_callback: Optional progress callback
            
        Returns:
            Path to extracted audio file
        """
        try:
            if progress_callback:
                await progress_callback("Extracting audio...")
            
            # Use ffmpeg to extract audio
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream,
                str(output_path),
                acodec='pcm_s16le',
                ac=1,
                ar='16000'
            )
            
            await asyncio.to_thread(
                ffmpeg.run,
                stream,
                overwrite_output=True,
                quiet=True
            )
            
            logger.info(f"Audio extracted: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
            raise
    
    async def generate_subtitles(
        self,
        video_path: Path,
        progress_callback: Optional[callable] = None
    ) -> dict:
        """
        Generate Arabic subtitles for a video.
        
        Args:
            video_path: Path to video file
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with paths to generated subtitle files
        """
        try:
            # Extract audio
            audio_path = video_path.with_suffix('.wav')
            await self.extract_audio(video_path, audio_path, progress_callback)
            
            # Speech recognition
            if progress_callback:
                await progress_callback("Running speech recognition...")
            
            segments = await self.speech_recognizer.transcribe(audio_path)
            
            # Generate original language subtitles
            if progress_callback:
                await progress_callback("Generating subtitles...")
            
            srt_path = video_path.with_suffix('.srt')
            vtt_path = video_path.with_suffix('.vtt')
            
            self._write_srt(segments, srt_path)
            self._write_vtt(segments, vtt_path)
            
            # Translate to Arabic
            if progress_callback:
                await progress_callback("Translating to Arabic...")
            
            arabic_segments = await self.translation_engine.translate_segments(
                segments,
                target_lang='ar'
            )
            
            arabic_srt = video_path.with_stem(video_path.stem + '_arabic').with_suffix('.srt')
            arabic_vtt = video_path.with_stem(video_path.stem + '_arabic').with_suffix('.vtt')
            
            self._write_srt(arabic_segments, arabic_srt)
            self._write_vtt(arabic_segments, arabic_vtt)
            
            # Cleanup audio
            audio_path.unlink(missing_ok=True)
            
            return {
                'original_srt': srt_path,
                'original_vtt': vtt_path,
                'arabic_srt': arabic_srt,
                'arabic_vtt': arabic_vtt,
            }
            
        except Exception as e:
            logger.error(f"Failed to generate subtitles: {e}")
            raise
    
    def _write_srt(self, segments: list, output_path: Path) -> None:
        """
        Write segments to SRT format.
        
        Args:
            segments: List of subtitle segments
            output_path: Output SRT file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, 1):
                start = self._format_timestamp(segment['start'])
                end = self._format_timestamp(segment['end'])
                text = segment['text'].strip()
                
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
    
    def _write_vtt(self, segments: list, output_path: Path) -> None:
        """
        Write segments to VTT format.
        
        Args:
            segments: List of subtitle segments
            output_path: Output VTT file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for segment in segments:
                start = self._format_timestamp(segment['start'], vtt=True)
                end = self._format_timestamp(segment['end'], vtt=True)
                text = segment['text'].strip()
                
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
    
    def _format_timestamp(
        self,
        seconds: float,
        vtt: bool = False
    ) -> str:
        """
        Format timestamp for subtitles.
        
        Args:
            seconds: Time in seconds
            vtt: Whether to use VTT format (period instead of comma)
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        separator = '.' if vtt else ','
        return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"