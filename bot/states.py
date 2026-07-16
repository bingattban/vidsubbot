"""
Telegram bot conversation states.
"""
from telegram.ext import ConversationHandler

# Conversation states
(
    SELECTING_ACTION,
    WAITING_FOR_URL,
    PROCESSING_VIDEO,
    SELECTING_QUALITY,
    DOWNLOADING,
) = range(5)