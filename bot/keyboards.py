"""
Telegram inline keyboards.
"""
from typing import List, Dict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("📹 إرسال رابط / Send URL", callback_data='send_url')],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_download_options_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """
    Get download options keyboard.
    
    Args:
        task_id: Processing task ID
        
    Returns:
        Inline keyboard markup
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "📝 الترجمة العربية / Arabic Subtitle",
                callback_data='download_arabic_subtitle'
            )
        ],
        [
            InlineKeyboardButton(
                "🌐 الترجمة الأصلية / Original Subtitle",
                callback_data='download_original_subtitle'
            )
        ],
        [
            InlineKeyboardButton(
                "🤖 إنشاء ترجمة عربية / Generate Arabic",
                callback_data='generate_arabic_subtitle'
            )
        ],
        [
            InlineKeyboardButton(
                "📹 تنزيل الفيديو / Download Video",
                callback_data='download_video'
            )
        ],
        [
            InlineKeyboardButton(
                "❌ إلغاء / Cancel",
                callback_data='cancel'
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_quality_keyboard(formats: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Get video quality selection keyboard.
    
    Args:
        formats: List of available video formats
        
    Returns:
        Inline keyboard markup
    """
    keyboard = []
    
    # Add quality options
    for fmt in formats[:10]:  # Limit to 10 options
        label = f"🎥 {fmt['resolution']}"
        if fmt['filesize'] != 'Unknown':
            label += f" ({fmt['filesize']})"
        
        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"quality_{fmt['format_id']}"
            )
        ])
    
    # Add cancel button
    keyboard.append([
        InlineKeyboardButton(
            "❌ إلغاء / Cancel",
            callback_data='cancel'
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """
    Get cancel only keyboard.
    
    Args:
        task_id: Processing task ID
        
    Returns:
        Inline keyboard markup
    """
    keyboard = [
        [InlineKeyboardButton("❌ إلغاء / Cancel", callback_data='cancel')],
    ]
    return InlineKeyboardMarkup(keyboard)