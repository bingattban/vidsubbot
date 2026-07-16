"""
Speech recognition using Faster-Whisper.
"""
import asyncio
from pathlib import Path
from typing import List, Optional
from faster_whisper import WhisperModel

from utils.logging import setup_logging

logger = setup_logging(__name__)


class SpeechRecognizer:
    """Offline speech recognition using Faster-Whisper."""
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8"
    ) -> None:
        """
        Initialize speech recognizer.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
            device: Device to use (cpu, cuda)
            compute_type: Compute type (int8, float16, float32)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model: Optional[WhisperModel] = None
        
        logger.info(f"Initialized speech recognizer with model: {model_size}")
    
    async def load_model(self) -> None:
        """Load the Whisper model if not already loaded."""
        if self.model is None:
            try:
                self.model = await asyncio.to_thread(
                    WhisperModel,
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
                logger.info(f"Whisper model {self.model_size} loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise
    
    async def transcribe(
        self,
        audio_path: Path,
        progress_callback: Optional[callable] = None
    ) -> List[dict]:
        """
        Transcribe audio file to text segments.
        
        Args:
            audio_path: Path to audio file
            progress_callback: Optional progress callback
            
        Returns:
            List of segments with start, end, and text
        """
        try:
            await self.load_model()
            
            if progress_callback:
                await progress_callback("Transcribing audio...")
            
            segments = []
            
            # Run transcription in thread pool
            result = await asyncio.to_thread(
                self.model.transcribe,
                str(audio_path),
                beam_size=5,
                word_timestamps=True
            )
            
            for segment in result[0]:
                segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip(),
                })
            
            logger.info(f"Transcription complete: {len(segments)} segments")
            return segments
            
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            raise