"""
Disconnect calendar command handler for Donna Bot
"""

from telegram import Update
from telegram.ext import ContextTypes
from database import Database


async def disconnect_calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle the /disconnect_calendar command"""
    chat_id = update.effective_chat.id
    
    if not db.is_calendar_connected(chat_id):
        await update.message.reply_text("📅 No calendar is currently connected.")
        return
    
    if db.disconnect_calendar(chat_id):
        await update.message.reply_text(
            "📅 Calendar disconnected successfully.\n\n"
            "Your calendar data has been removed from our database. "
            "Use /connect_calendar if you want to reconnect later."
        )
    else:
        await update.message.reply_text("❌ Error disconnecting calendar. Please try again.")