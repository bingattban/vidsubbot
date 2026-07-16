"""
Dependency injection container for the application.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from database.repository import DatabaseRepository
from download.downloader import VideoDownloader
from download.metadata import MetadataExtractor
from speech.recognizer import SpeechRecognizer
from subtitle.detector import SubtitleDetector
from subtitle.extractor import SubtitleExtractor
from subtitle.generator import SubtitleGenerator
from translation.translator import TranslationEngine
from config.settings import settings
from utils.logging import setup_logging

logger = setup_logging(__name__)


class DIContainer:
    """Dependency injection container for managing service instances."""
    
    def __init__(self) -> None:
        """Initialize the DI container."""
        self._engine = None
        self._session_factory = None
        self._repository: Optional[DatabaseRepository] = None
        self._downloader: Optional[VideoDownloader] = None
        self._metadata_extractor: Optional[MetadataExtractor] = None
        self._speech_recognizer: Optional[SpeechRecognizer] = None
        self._subtitle_detector: Optional[SubtitleDetector] = None
        self._subtitle_extractor: Optional[SubtitleExtractor] = None
        self._subtitle_generator: Optional[SubtitleGenerator] = None
        self._translation_engine: Optional[TranslationEngine] = None
    
    async def initialize(self) -> None:
        """Initialize all services asynchronously."""
        try:
            # Initialize database engine
            self._engine = create_async_engine(
                f"sqlite+aiosqlite:///{settings.database_path}",
                echo=False
            )
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Initialize repository
            self._repository = DatabaseRepository(self._session_factory)
            await self._repository.initialize()
            
            # Initialize download services
            self._downloader = VideoDownloader(settings.download_dir)
            self._metadata_extractor = MetadataExtractor()
            
            # Initialize speech recognition
            self._speech_recognizer = SpeechRecognizer(
                model_size=settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type
            )
            
            # Initialize subtitle services
            self._subtitle_detector = SubtitleDetector()
            self._subtitle_extractor = SubtitleExtractor()
            
            # Initialize translation engine
            self._translation_engine = TranslationEngine()
            
            # Initialize subtitle generator
            self._subtitle_generator = SubtitleGenerator(
                self._speech_recognizer,
                self._translation_engine
            )
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    @property
    def repository(self) -> DatabaseRepository:
        """Get database repository instance."""
        if not self._repository:
            raise RuntimeError("Database repository not initialized. Call initialize() first.")
        return self._repository
    
    @property
    def downloader(self) -> VideoDownloader:
        """Get video downloader instance."""
        if not self._downloader:
            raise RuntimeError("Video downloader not initialized. Call initialize() first.")
        return self._downloader
    
    @property
    def metadata_extractor(self) -> MetadataExtractor:
        """Get metadata extractor instance."""
        if not self._metadata_extractor:
            raise RuntimeError("Metadata extractor not initialized. Call initialize() first.")
        return self._metadata_extractor
    
    @property
    def speech_recognizer(self) -> SpeechRecognizer:
        """Get speech recognizer instance."""
        if not self._speech_recognizer:
            raise RuntimeError("Speech recognizer not initialized. Call initialize() first.")
        return self._speech_recognizer
    
    @property
    def subtitle_detector(self) -> SubtitleDetector:
        """Get subtitle detector instance."""
        if not self._subtitle_detector:
            raise RuntimeError("Subtitle detector not initialized. Call initialize() first.")
        return self._subtitle_detector
    
    @property
    def subtitle_extractor(self) -> SubtitleExtractor:
        """Get subtitle extractor instance."""
        if not self._subtitle_extractor:
            raise RuntimeError("Subtitle extractor not initialized. Call initialize() first.")
        return self._subtitle_extractor
    
    @property
    def subtitle_generator(self) -> SubtitleGenerator:
        """Get subtitle generator instance."""
        if not self._subtitle_generator:
            raise RuntimeError("Subtitle generator not initialized. Call initialize() first.")
        return self._subtitle_generator
    
    @property
    def translation_engine(self) -> TranslationEngine:
        """Get translation engine instance."""
        if not self._translation_engine:
            raise RuntimeError("Translation engine not initialized. Call initialize() first.")
        return self._translation_engine
    
    async def cleanup(self) -> None:
        """Cleanup and dispose all resources."""
        try:
            if self._engine:
                await self._engine.dispose()
                logger.info("Database engine disposed")
            
            self._repository = None
            self._downloader = None
            self._metadata_extractor = None
            self._speech_recognizer = None
            self._subtitle_detector = None
            self._subtitle_extractor = None
            self._subtitle_generator = None
            self._translation_engine = None
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")