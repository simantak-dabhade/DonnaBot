#!/usr/bin/env python3
"""
Donna Bot - Simple AI Personal Assistant

A clean, simple Telegram bot powered by OpenAI.
"""

import asyncio
import logging
import os
from typing import Optional
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from database import Database
from oauth_handler import OAuthHandler
from openai import OpenAI
from handlers.start import start_command
from handlers.help import help_command
from handlers.connect_calendar import connect_calendar_command
from handlers.calendar_status import calendar_status_command
from handlers.today import today_command
from handlers.disconnect_calendar import disconnect_calendar_command
from handlers.message import handle_message

# Load environment variables from .env file
load_dotenv()

# Configure logging with debug level for detailed OAuth debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class DonnaBot:
    """Simple Donna bot implementation"""
    
    def __init__(self):
        self.telegram_token: Optional[str] = None
        self.app: Optional[Application] = None
        self.db = Database()
        self.oauth_handler = OAuthHandler(self.db)
        self.openai_client = OpenAI()
        
    def load_config(self):
        """Load configuration from environment variables"""
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        
        if not self.telegram_token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required") 
        logger.info("Configuration loaded successfully")
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting Donna Bot...")
        
        # Initialize Telegram bot
        self.app = Application.builder().token(self.telegram_token).build()
        
        # Start OAuth handler
        self.oauth_handler.start_server()
        
        # Add command handlers with partial application to pass dependencies
        self.app.add_handler(CommandHandler("start", 
            lambda update, context: start_command(update, context, self.db)))
        self.app.add_handler(CommandHandler("help", help_command))
        self.app.add_handler(CommandHandler("connect_calendar", 
            lambda update, context: connect_calendar_command(update, context, self.db, self.oauth_handler)))
        self.app.add_handler(CommandHandler("calendar_status", 
            lambda update, context: calendar_status_command(update, context, self.db)))
        self.app.add_handler(CommandHandler("today", 
            lambda update, context: today_command(update, context, self.db, self.oauth_handler)))
        self.app.add_handler(CommandHandler("disconnect_calendar", 
            lambda update, context: disconnect_calendar_command(update, context, self.db)))
        
        # Add message handler for non-command text (should be last)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
            lambda update, context: handle_message(update, context, self.db, self.openai_client, self.oauth_handler)))
        
        logger.info("Donna Bot started successfully!")
        
        # Start polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        try:
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()


async def main():
    """Main entry point"""
    bot = DonnaBot()
    
    try:
        bot.load_config()
        await bot.start()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))