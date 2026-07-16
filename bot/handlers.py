"""
Telegram bot handlers.
"""
import asyncio
from pathlib import Path
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

from bot.keyboards import (
    get_main_menu_keyboard,
    get_quality_keyboard,
    get_download_options_keyboard,
    get_cancel_keyboard
)
from core.config import settings
from core.di_container import DIContainer
from utils.logging import setup_logging
from utils.validators import validate_url

logger = setup_logging(__name__)


async def setup_bot(container: DIContainer) -> Application:
    """
    Setup Telegram bot application.
    
    Args:
        container: Dependency injection container
        
    Returns:
        Configured Application instance
    """
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Store container in bot data
    application.bot_data['container'] = container
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    return application


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_text(
        f"مرحباً {user.first_name}! 👋\n\n"
        "أرسل رابط فيديو للبدء.\n"
        "سأقوم بتنزيل الترجمة العربية وإنشاءها إذا لزم الأمر.\n\n"
        "Send me a video URL to get started.\n"
        "I'll download and generate Arabic subtitles.",
        reply_markup=get_main_menu_keyboard()
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "🎬 *Arabic Subtitle Bot*\n\n"
        "• Send any video URL\n"
        "• I'll find or create Arabic subtitles\n"
        "• Download the original video\n\n"
        "Supported: YouTube, Vimeo, Twitter, TikTok, and more!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard()
    )


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle text messages (URLs)."""
    container = context.bot_data['container']
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Check rate limit
    if not await container.repository.check_rate_limit(
        user_id,
        settings.rate_limit_per_user,
        settings.rate_limit_window
    ):
        await update.message.reply_text(
            "⚠️ لقد تجاوزت الحد المسموح. حاول مرة أخرى لاحقاً.\n"
            "Rate limit exceeded. Please try again later."
        )
        return
    
    # Validate URL
    if not validate_url(text):
        await update.message.reply_text(
            "❌ رابط غير صالح. أرسل رابط فيديو صحيح.\n"
            "Invalid URL. Please send a valid video URL."
        )
        return
    
    # Create temp directory for this task
    task_id = f"{user_id}_{int(asyncio.get_event_loop().time())}"
    temp_dir = Path(settings.temp_dir) / task_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Create task in database
    task = await container.repository.create_task(user_id, text, str(temp_dir))
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "⏳ جاري معالجة الرابط...\nProcessing URL...",
        reply_markup=get_cancel_keyboard(task.id)
    )
    
    # Store processing message ID
    context.user_data['processing_msg_id'] = processing_msg.message_id
    
    try:
        # Start processing
        await process_video_url(
            update,
            context,
            text,
            temp_dir,
            task.id
        )
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        await update.message.reply_text(
            "❌ فشلت المعالجة. حاول مرة أخرى.\nProcessing failed. Please try again."
        )
        await container.repository.update_task_status(task.id, 'failed')


async def process_video_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    url: str,
    temp_dir: Path,
    task_id: int
) -> None:
    """Process video URL and generate subtitles."""
    container = context.bot_data['container']
    user_id = update.effective_user.id
    
    # Step 1: Extract metadata
    await update_progress(context, "📊 جاري استخراج المعلومات...\nExtracting metadata...")
    metadata = await container.metadata_extractor.extract_metadata(url)
    await container.repository.update_task_status(
        task_id, 'processing', metadata['title']
    )
    
    # Display video info
    await update.message.reply_text(
        f"📹 *{metadata['title']}*\n"
        f"⏱ المدة: {metadata['duration']}\n\n"
        "اختر ما تريد القيام به:\nChoose what to do:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_download_options_keyboard(task_id)
    )
    
    # Store metadata in context
    context.user_data['current_video'] = {
        'url': url,
        'temp_dir': str(temp_dir),
        'metadata': metadata,
        'task_id': task_id
    }


async def handle_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    container = context.bot_data['container']
    data = query.data
    user_data = context.user_data.get('current_video', {})
    
    if not user_data:
        await query.edit_message_text("❌ Session expired. Send a new URL.")
        return
    
    url = user_data['url']
    temp_dir = Path(user_data['temp_dir'])
    task_id = user_data['task_id']
    
    try:
        if data == 'download_arabic_subtitle':
            await handle_arabic_subtitle(query, container, url, temp_dir, task_id)
        
        elif data == 'download_original_subtitle':
            await handle_original_subtitle(query, container, url, temp_dir)
        
        elif data == 'generate_arabic_subtitle':
            await handle_generate_subtitle(query, context, container, url, temp_dir, task_id)
        
        elif data == 'download_video':
            await handle_video_download(query, context, container, url, temp_dir)
        
        elif data.startswith('quality_'):
            format_id = data.replace('quality_', '')
            await handle_quality_selection(query, context, container, url, format_id, temp_dir)
        
        elif data == 'cancel':
            await handle_cancel(query, context, temp_dir, task_id)
        
    except Exception as e:
        logger.error(f"Callback handling failed: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again.",
            reply_markup=get_main_menu_keyboard()
        )


async def handle_arabic_subtitle(
    query,
    container: DIContainer,
    url: str,
    temp_dir: Path,
    task_id: int
) -> None:
    """Handle Arabic subtitle download."""
    await query.edit_message_text("🔍 جاري البحث عن الترجمة العربية...\nSearching for Arabic subtitles...")
    
    # Detect subtitles
    subtitles = await container.subtitle_detector.detect_subtitles(url)
    
    if container.subtitle_detector.has_arabic(subtitles):
        # Download Arabic subtitles
        arabic_code = None
        for code in ['ar', 'ara', 'arabic', 'Arabic']:
            if code in subtitles:
                arabic_code = code
                break
        
        if arabic_code:
            sub_path = temp_dir / f"arabic_subtitle"
            downloaded = await container.subtitle_extractor.download_subtitle(
                subtitles[arabic_code][0]['url'],
                arabic_code,
                sub_path
            )
            
            if downloaded:
                # Convert to SRT
                srt_path = await container.subtitle_extractor.convert_to_srt(downloaded)
                enhanced_path = container.subtitle_extractor.enhance_subtitles(srt_path)
                
                # Send files
                await query.message.reply_document(
                    document=open(enhanced_path, 'rb'),
                    filename=f"arabic_subtitle.srt",
                    caption="✅ الترجمة العربية (SRT)"
                )
                
                # Also send VTT if available
                if downloaded.suffix == '.vtt':
                    await query.message.reply_document(
                        document=open(downloaded, 'rb'),
                        filename=f"arabic_subtitle.vtt",
                        caption="✅ الترجمة العربية (VTT)"
                    )
                
                await container.repository.update_task_status(task_id, 'completed')
                return
    
    await query.edit_message_text(
        "❌ لا توجد ترجمة عربية متاحة.\n"
        "No Arabic subtitles available.\n\n"
        "Use 'Generate Arabic Subtitle' to create one.",
        reply_markup=get_download_options_keyboard(task_id)
    )


async def handle_original_subtitle(
    query,
    container: DIContainer,
    url: str,
    temp_dir: Path
) -> None:
    """Handle original subtitle download."""
    await query.edit_message_text("🔍 Searching for original subtitles...")
    
    subtitles = await container.subtitle_detector.detect_subtitles(url)
    
    if subtitles:
        # Download first available subtitle
        first_lang = list(subtitles.keys())[0]
        sub_path = temp_dir / f"original_subtitle"
        downloaded = await container.subtitle_extractor.download_subtitle(
            subtitles[first_lang][0]['url'],
            first_lang,
            sub_path
        )
        
        if downloaded:
            await query.message.reply_document(
                document=open(downloaded, 'rb'),
                filename=f"original_subtitle_{first_lang}.{downloaded.suffix}",
                caption=f"✅ Original subtitle ({first_lang})"
            )
            return
    
    await query.edit_message_text(
        "❌ No subtitles available.",
        reply_markup=get_download_options_keyboard()
    )


async def handle_generate_subtitle(
    query,
    context,
    container: DIContainer,
    url: str,
    temp_dir: Path,
    task_id: int
) -> None:
    """Handle Arabic subtitle generation."""
    await query.edit_message_text(
        "🎤 جاري إنشاء الترجمة العربية...\n"
        "Generating Arabic subtitles...\n\n"
        "هذا قد يستغرق بعض الوقت.\n"
        "This may take a while."
    )
    
    # Download video first (needed for audio extraction)
    progress_msg = await query.message.reply_text("📥 Downloading video...")
    
    # Get best quality format automatically
    formats = await container.downloader.get_available_formats(url)
    if not formats:
        raise ValueError("No video formats available")
    
    video_path = await container.downloader.download_video(
        url,
        formats[0]['format_id'],
        progress_callback=lambda p: update_progress_message(progress_msg, p)
    )
    
    # Generate subtitles
    await progress_msg.edit_text("🎤 Running speech recognition...")
    
    subtitle_files = await container.subtitle_generator.generate_subtitles(
        video_path,
        progress_callback=lambda p: update_progress_message(progress_msg, p)
    )
    
    # Send generated subtitles
    await progress_msg.edit_text("📤 Uploading subtitles...")
    
    await query.message.reply_document(
        document=open(subtitle_files['arabic_srt'], 'rb'),
        filename="arabic_subtitle.srt",
        caption="✅ Arabic Subtitle (SRT) - Generated"
    )
    
    await query.message.reply_document(
        document=open(subtitle_files['arabic_vtt'], 'rb'),
        filename="arabic_subtitle.vtt",
        caption="✅ Arabic Subtitle (VTT) - Generated"
    )
    
    # Also send original subtitles
    await query.message.reply_document(
        document=open(subtitle_files['original_srt'], 'rb'),
        filename="original_subtitle.srt",
        caption="📝 Original Subtitle (SRT)"
    )
    
    await progress_msg.delete()
    await container.repository.update_task_status(task_id, 'completed')


async def handle_video_download(
    query,
    context,
    container: DIContainer,
    url: str,
    temp_dir: Path
) -> None:
    """Handle video quality selection."""
    await query.edit_message_text("🔍 جاري البحث عن جودات الفيديو...\nFetching video qualities...")
    
    formats = await container.downloader.get_available_formats(url)
    
    if not formats:
        await query.edit_message_text("❌ No video formats available.")
        return
    
    # Store formats in context
    context.user_data['video_formats'] = formats
    
    await query.edit_message_text(
        "📹 اختر جودة الفيديو:\nSelect video quality:",
        reply_markup=get_quality_keyboard(formats)
    )


async def handle_quality_selection(
    query,
    context,
    container: DIContainer,
    url: str,
    format_id: str,
    temp_dir: Path
) -> None:
    """Handle video quality selection and download."""
    formats = context.user_data.get('video_formats', [])
    selected_format = next(
        (f for f in formats if f['format_id'] == format_id),
        None
    )
    
    if not selected_format:
        await query.edit_message_text("❌ Invalid format selection.")
        return
    
    await query.edit_message_text(
        f"📥 جاري تنزيل الفيديو...\n"
        f"Downloading video...\n"
        f"الجودة: {selected_format['resolution']}\n"
        f"Quality: {selected_format['resolution']}"
    )
    
    progress_msg = await query.message.reply_text("⏳ Starting download...")
    
    try:
        video_path = await container.downloader.download_video(
            url,
            format_id,
            progress_callback=lambda p: update_progress_message(progress_msg, p)
        )
        
        await progress_msg.edit_text("📤 Uploading video to Telegram...")
        
        # Send video file
        await query.message.reply_video(
            video=open(video_path, 'rb'),
            caption=f"✅ {selected_format['resolution']} video",
            supports_streaming=True
        )
        
        await progress_msg.delete()
        
    except Exception as e:
        logger.error(f"Video download failed: {e}")
        await progress_msg.edit_text("❌ Download failed. Please try again.")


async def handle_cancel(
    query,
    context,
    temp_dir: Path,
    task_id: int
) -> None:
    """Handle cancel action."""
    container = context.bot_data['container']
    
    # Cleanup temp files
    if temp_dir.exists():
        import shutil
        shutil.rmtree(temp_dir)
    
    await container.repository.update_task_status(task_id, 'cancelled')
    await query.edit_message_text(
        "❌ تم الإلغاء.\nCancelled.",
        reply_markup=get_main_menu_keyboard()
    )


async def update_progress(
    context: ContextTypes.DEFAULT_TYPE,
    message: str
) -> None:
    """Update progress message."""
    if 'processing_msg_id' in context.user_data:
        try:
            await context.bot.edit_message_text(
                chat_id=context.user_data.get('chat_id'),
                message_id=context.user_data['processing_msg_id'],
                text=message
            )
        except Exception:
            pass


async def update_progress_message(
    message,
    progress_text: str
) -> None:
    """Update progress message text."""
    try:
        await message.edit_text(progress_text)
    except Exception:
        pass


async def error_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )
    except Exception:
        pass