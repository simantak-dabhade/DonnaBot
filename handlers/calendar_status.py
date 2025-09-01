"""
Calendar status command handler for Donna Bot
"""

from telegram import Update
from telegram.ext import ContextTypes
from database import Database


async def calendar_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """Handle the /calendar_status command"""
    chat_id = update.effective_chat.id
    
    if db.is_calendar_connected(chat_id):
        await update.message.reply_text(
            "📅 <b>Calendar Status: Connected</b> ✅\n\n"
            "Your Google Calendar is connected and ready to use!\n\n"
            "<b>Available commands:</b>\n"
            "/today - View today's events\n"
            "/disconnect_calendar - Disconnect calendar",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "📅 <b>Calendar Status: Not Connected</b> ❌\n\n"
            "Your Google Calendar is not connected.\n\n"
            "Use /connect_calendar to set up the connection.",
            parse_mode='HTML'
        )