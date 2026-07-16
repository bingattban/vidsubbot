"""
Main entry point for the Arabic Subtitle Telegram Bot.
"""
import asyncio
import signal
import sys
from pathlib import Path

from bot.handlers import setup_bot
from core.di_container import DIContainer
from utils.logging import setup_logging
from utils.cleanup import CleanupManager
from config.settings import settings

logger = setup_logging(__name__)


async def main() -> None:
    """Initialize and run the Telegram bot."""
    try:
        # Ensure required directories exist
        Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.download_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
        if settings.log_file:
            Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("Initializing dependency injection container...")
        container = DIContainer()
        await container.initialize()
        
        logger.info("Starting cleanup manager...")
        cleanup_manager = CleanupManager(
            temp_dir=settings.temp_dir,
            cleanup_interval=settings.cleanup_interval,
            file_lifetime=settings.temp_file_lifetime
        )
        cleanup_task = asyncio.create_task(cleanup_manager.start())
        
        logger.info("Setting up bot handlers...")
        application = await setup_bot(container)
        
        # Graceful shutdown handler
        async def shutdown():
            logger.info("Shutting down...")
            cleanup_manager.stop()
            if not cleanup_task.done():
                cleanup_task.cancel()
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass
            
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            await container.cleanup()
            logger.info("Shutdown complete")
            sys.exit(0)
        
        def signal_handler(sig, frame):
            asyncio.create_task(shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Starting bot polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("Arabic Subtitle Bot is running!")
        
        # Keep running until stopped
        stop_signal = asyncio.Event()
        await stop_signal.wait()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())