"""
Connect calendar command handler for Donna Bot
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import Database
from oauth_handler import OAuthHandler

logger = logging.getLogger(__name__)


async def connect_calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 db: Database, oauth_handler: OAuthHandler):
    """Handle the /connect_calendar command"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    logger.info(f"=== Calendar connection requested by user {user.username} ({chat_id}) ===")
    
    # Check if already connected
    if db.is_calendar_connected(chat_id):
        logger.info(f"User {chat_id} already has calendar connected")
        await update.message.reply_text(
            "📅 Your Google Calendar is already connected!\n\n"
            "Use /calendar_status to see connection details or /today to view your calendar."
        )
        return
    
    try:
        logger.debug(f"Generating OAuth URL for chat_id: {chat_id}")
        
        # Generate OAuth URL
        auth_url = oauth_handler.generate_auth_url(chat_id)
        logger.info(f"Generated OAuth URL for user {chat_id}: {auth_url}")
        
        if not auth_url:
            logger.error(f"OAuth URL generation returned empty result for user {chat_id}")
            await update.message.reply_text("❌ Failed to generate calendar connection link. Please try again later.")
            return
        
        await update.message.reply_text(
            "🔗 <b>Connect Your Google Calendar</b>\n\n"
            "To connect your Google Calendar, please:\n"
            "1. Click the link below\n"
            "2. Sign in with your Google account\n"
            "3. Grant calendar permissions\n"
            "4. You'll be redirected to a success page\n\n"
            f"<a href='{auth_url}'>🔗 Connect Calendar</a>\n\n"
            "<i>Note: The link will open in your browser</i>\n\n"
            f"📋 Raw link: <code>{auth_url}</code>",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        logger.info(f"Calendar connection link sent to user {chat_id}")
        
    except Exception as e:
        logger.error(f"Error in connect_calendar_command for user {chat_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Sorry, there was an error setting up calendar connection.\n\n"
            "Please check that the bot is properly configured and try again later."
        )