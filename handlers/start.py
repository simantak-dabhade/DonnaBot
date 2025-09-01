"""
Start command handler for Donna Bot
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import Database

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle the /start command and register user"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Register/update user in database
    is_new_user = not db.user_exists(chat_id)
    db.add_user(
        chat_id=chat_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    if is_new_user:
        logger.info(f"New user registered: {user.username} ({chat_id})")
        welcome_msg = f"🎉 Welcome {user.first_name}! You've been registered successfully."
    else:
        logger.info(f"Existing user: {user.username} ({chat_id})")
        welcome_msg = f"👋 Welcome back {user.first_name}!"
    
    total_users = db.get_user_count()
    
    await update.message.reply_text(
        f"🤖 {welcome_msg}\n\n"
        "I'm Donna, your AI personal assistant. I'm here to help you with various tasks.\n\n"
        f"👥 Total registered users: {total_users}\n\n"
        "Available commands:\n"
        "/start - Show this welcome message\n"
        "/help - Get help and information\n"
        "/connect_calendar - Connect your Google Calendar\n"
        "/calendar_status - Check calendar connection status\n"
        "/today - View today's events"
    )