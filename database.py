"""
Database operations for Donna Bot

Simple SQLite database to store user information.
"""

import sqlite3
import logging
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class Database:
    """Handle SQLite database operations for user storage"""
    
    def __init__(self, db_path: str = "donna.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize database and create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    calendar_tokens TEXT,
                    calendar_connected BOOLEAN DEFAULT FALSE,
                    conversation_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Add calendar and conversation columns to existing table if they don't exist
            try:
                conn.execute("ALTER TABLE users ADD COLUMN calendar_tokens TEXT")
                conn.execute("ALTER TABLE users ADD COLUMN calendar_connected BOOLEAN DEFAULT FALSE")
                conn.execute("ALTER TABLE users ADD COLUMN conversation_id TEXT")
            except sqlite3.OperationalError:
                # Columns already exist
                pass
            conn.commit()
        logger.info(f"Database initialized: {self.db_path}")
    
    def add_user(self, chat_id: int, username: Optional[str] = None, 
                 first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Add or update a user in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO users 
                    (chat_id, username, first_name, last_name, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (chat_id, username, first_name, last_name))
                conn.commit()
            logger.info(f"User {username} ({chat_id}) added/updated in database")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error adding user: {e}")
            return False
    
    def get_user(self, chat_id: int) -> Optional[Tuple[int, str, str, str]]:
        """Get user by chat_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT chat_id, username, first_name, last_name FROM users WHERE chat_id = ?",
                    (chat_id,)
                )
                return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Database error getting user: {e}")
            return None
    
    def get_all_users(self) -> list[Tuple[int, str, str, str]]:
        """Get all users from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT chat_id, username, first_name, last_name FROM users ORDER BY created_at"
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database error getting all users: {e}")
            return []
    
    def get_user_count(self) -> int:
        """Get total number of users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM users")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Database error getting user count: {e}")
            return 0
    
    def user_exists(self, chat_id: int) -> bool:
        """Check if user exists in database"""
        return self.get_user(chat_id) is not None
    
    def save_calendar_tokens(self, chat_id: int, tokens: Dict[str, Any]) -> bool:
        """Save calendar tokens for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First, ensure the user exists (INSERT OR IGNORE creates user if not exists)
                conn.execute("""
                    INSERT OR IGNORE INTO users (chat_id, username, first_name, last_name)
                    VALUES (?, 'unknown', 'unknown', NULL)
                """, (chat_id,))
                
                # Then update with calendar tokens
                cursor = conn.execute("""
                    UPDATE users 
                    SET calendar_tokens = ?, calendar_connected = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                """, (json.dumps(tokens), chat_id))
                
                if cursor.rowcount == 0:
                    logger.error(f"Failed to update calendar tokens for user {chat_id} - no rows affected")
                    return False
                    
                conn.commit()
                
            logger.info(f"Calendar tokens saved for user {chat_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error saving calendar tokens: {e}")
            return False
    
    def get_calendar_tokens(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get calendar tokens for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT calendar_tokens FROM users WHERE chat_id = ? AND calendar_connected = TRUE",
                    (chat_id,)
                )
                result = cursor.fetchone()
                if result and result[0]:
                    return json.loads(result[0])
                return None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Database error getting calendar tokens: {e}")
            return None
    
    def disconnect_calendar(self, chat_id: int) -> bool:
        """Remove calendar connection for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE users 
                    SET calendar_tokens = NULL, calendar_connected = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                """, (chat_id,))
                conn.commit()
            logger.info(f"Calendar disconnected for user {chat_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error disconnecting calendar: {e}")
            return False
    
    def is_calendar_connected(self, chat_id: int) -> bool:
        """Check if user has calendar connected"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT calendar_connected FROM users WHERE chat_id = ?",
                    (chat_id,)
                )
                result = cursor.fetchone()
                logger.debug(f"Calendar connection check for {chat_id}: result={result}")
                if result:
                    connected = result[0] is True or result[0] == 1
                    logger.debug(f"Calendar connected status: {connected} (raw value: {result[0]}, type: {type(result[0])})")
                    return connected
                else:
                    logger.debug(f"No user found for chat_id {chat_id}")
                    return False
        except sqlite3.Error as e:
            logger.error(f"Database error checking calendar connection: {e}")
            return False
    
    def save_conversation_id(self, chat_id: int, conversation_id: str) -> bool:
        """Save conversation ID for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE users 
                    SET conversation_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                """, (conversation_id, chat_id))
                conn.commit()
            logger.info(f"Conversation ID saved for user {chat_id}: {conversation_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error saving conversation ID: {e}")
            return False
    
    def get_conversation_id(self, chat_id: int) -> Optional[str]:
        """Get conversation ID for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT conversation_id FROM users WHERE chat_id = ?",
                    (chat_id,)
                )
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
        except sqlite3.Error as e:
            logger.error(f"Database error getting conversation ID: {e}")
            return None