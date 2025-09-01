"""
Help command handler for Donna Bot
"""

from telegram import Update
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    await update.message.reply_text(
        "🆘 <b>Donna Bot Help</b>\n\n"
        "I'm an AI assistant powered by OpenAI. Here's what I can do:\n\n"
        "• Answer questions\n"
        "• Help with various tasks\n"
        "• Provide information\n\n"
        "<b>Commands:</b>\n"
        "/start - Welcome message\n"
        "/help - This help message\n"
        "/connect_calendar - Connect Google Calendar\n"
        "/calendar_status - Check calendar connection\n"
        "/today - View today's events\n\n"
        "Just send me any message and I'll try to help!",
        parse_mode='HTML'
    )