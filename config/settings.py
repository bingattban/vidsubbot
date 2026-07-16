"""
Application settings using Pydantic Settings.
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    
    All settings can be overridden via environment variables or .env file.
    """
    
    # Telegram Bot Configuration
    telegram_bot_token: str
    
    # Path Configuration
    temp_dir: Path = Path("/tmp/arabic-subtitle-bot")
    download_dir: Path = Path("/tmp/arabic-subtitle-bot/downloads")
    database_path: Path = Path("data/bot.db")
    
    # Whisper Configuration
    whisper_model: str = "base"
    whisper_compute_type: str = "int8"
    whisper_device: str = "cpu"
    
    # Translation Configuration
    translation_engine: str = "argos"
    libretranslate_url: Optional[str] = None
    
    # Cleanup Configuration
    cleanup_interval: int = 3600
    temp_file_lifetime: int = 10800
    
    # Performance Configuration
    max_concurrent_tasks: int = 3
    worker_count: int = 2
    
    # Rate Limiting Configuration
    rate_limit_per_user: int = 10
    rate_limit_window: int = 3600
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[Path] = Path("logs/bot.log")
    
    # Database Configuration
    database_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False