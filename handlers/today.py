"""
Today command handler for Donna Bot
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database import Database
from oauth_handler import OAuthHandler

logger = logging.getLogger(__name__)


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                       db: Database, oauth_handler: OAuthHandler):
    """Handle the /today command"""
    chat_id = update.effective_chat.id
    
    if not db.is_calendar_connected(chat_id):
        await update.message.reply_text(
            "📅 Calendar not connected! Use /connect_calendar to set it up first."
        )
        return
    
    try:
        tokens = db.get_calendar_tokens(chat_id)
        if not tokens:
            await update.message.reply_text("❌ Calendar tokens not found. Please reconnect your calendar.")
            return
        
        events, updated_tokens = oauth_handler.get_today_events(tokens)
        
        # Save updated tokens if they changed
        if updated_tokens != tokens:
            db.save_calendar_tokens(chat_id, updated_tokens)
        
        if not events:
            await update.message.reply_text("📅 No events scheduled for today.")
            return
        
        today_str = datetime.now().strftime("%A, %B %d")
        message = f"📅 <b>Today's Events ({today_str}):</b>\n\n"
        
        for event in events:
            start_time = event['start']
            if 'T' in start_time:  # DateTime format
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                time_str = start_dt.strftime("%I:%M %p")
            else:  # All-day event
                time_str = "All day"
            
            message += f"• <b>{event['summary']}</b>\n"
            message += f"  🕐 {time_str}\n"
            if event['location']:
                message += f"  📍 {event['location']}\n"
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error getting today's events: {e}")
        await update.message.reply_text("❌ Sorry, there was an error fetching today's events. Please try again later.")