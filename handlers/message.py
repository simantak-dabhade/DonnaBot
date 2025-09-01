"""
Message handler for Donna Bot - handles non-command text messages
"""

import logging
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from database import Database
from openai import OpenAI

logger = logging.getLogger(__name__)

# Define calendar function tools for OpenAI
CALENDAR_TOOLS = [
    {
        "type": "function",
        "name": "get_today_events",
        "description": "Get all calendar events scheduled for today",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function", 
        "name": "get_week_events",
        "description": "Get all calendar events scheduled for this week (Monday to Sunday)",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


async def execute_calendar_function(function_name: str, arguments: dict, chat_id: int, db: Database, oauth_handler):
    """Execute calendar function calls from OpenAI"""
    try:
        # Check if calendar is connected
        if not db.is_calendar_connected(chat_id):
            return {"error": "Calendar not connected. Please use /connect_calendar to set up your calendar first."}
        
        # Get calendar tokens
        tokens = db.get_calendar_tokens(chat_id)
        if not tokens:
            return {"error": "Calendar tokens not found. Please reconnect your calendar."}
        
        if function_name == "get_today_events":
            events, updated_tokens = oauth_handler.get_today_events(tokens)
            # Save updated tokens if they changed
            if updated_tokens != tokens:
                db.save_calendar_tokens(chat_id, updated_tokens)
            
            if not events:
                return {"events": [], "message": "No events scheduled for today."}
            
            # Format events for the model
            formatted_events = []
            for event in events:
                start_time = event['start']
                if 'T' in start_time:  # DateTime format
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_str = start_dt.strftime("%I:%M %p")
                else:  # All-day event
                    time_str = "All day"
                
                formatted_events.append({
                    "title": event['summary'],
                    "time": time_str,
                    "location": event['location'] if event['location'] else None,
                    "description": event['description'] if event['description'] else None
                })
            
            return {"events": formatted_events, "date": datetime.now().strftime("%A, %B %d")}
        
        elif function_name == "get_week_events":
            events, updated_tokens = oauth_handler.get_week_events(tokens)
            # Save updated tokens if they changed
            if updated_tokens != tokens:
                db.save_calendar_tokens(chat_id, updated_tokens)
            
            if not events:
                return {"events": [], "message": "No events scheduled for this week."}
            
            # Format events for the model
            formatted_events = []
            for event in events:
                start_time = event['start']
                if 'T' in start_time:  # DateTime format
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    date_str = start_dt.strftime("%A, %B %d")
                    time_str = start_dt.strftime("%I:%M %p")
                else:  # All-day event
                    start_dt = datetime.fromisoformat(start_time)
                    date_str = start_dt.strftime("%A, %B %d")
                    time_str = "All day"
                
                formatted_events.append({
                    "title": event['summary'],
                    "date": date_str,
                    "time": time_str,
                    "location": event['location'] if event['location'] else None,
                    "description": event['description'] if event['description'] else None
                })
            
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            week_range = f"{start_of_week.strftime('%B %d')} - {end_of_week.strftime('%B %d')}"
            
            return {"events": formatted_events, "week_range": week_range}
        
        else:
            return {"error": f"Unknown function: {function_name}"}
            
    except Exception as e:
        logger.error(f"Error executing calendar function {function_name}: {e}", exc_info=True)
        return {"error": f"Failed to fetch calendar data: {str(e)}"}


async def reset_conversation_for_user(chat_id: int, db: Database, openai_client: OpenAI, reason: str = ""):
    """Reset conversation for a user due to corruption or errors"""
    logger.warning(f"Resetting conversation for user {chat_id}. Reason: {reason}")
    
    try:
        # Create new conversation
        conversation = openai_client.conversations.create(
            metadata={"user_id": str(chat_id), "reset_reason": reason},
            items=[]  # Start with empty conversation
        )
        
        # Save new conversation ID
        if db.save_conversation_id(chat_id, conversation.id):
            logger.info(f"New conversation created for user {chat_id}: {conversation.id}")
            return conversation.id
        else:
            logger.error(f"Failed to save new conversation ID for user {chat_id}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to reset conversation for user {chat_id}: {e}", exc_info=True)
        return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                        db: Database, openai_client: OpenAI, oauth_handler):
    """Handle non-command text messages"""
    message_text = update.message.text
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    logger.info(f"Received message from user {user.username} ({chat_id}): {message_text}")
    
    try:
        # Check if user has existing conversation
        conversation_id = db.get_conversation_id(chat_id)
        
        if conversation_id:
            logger.info(f"Using existing conversation for user {chat_id}: {conversation_id}")
        else:
            logger.info(f"Creating new conversation for user {chat_id}")
            # Create new conversation
            conversation = openai_client.conversations.create(
                metadata={"user_id": str(chat_id), "username": user.username or "unknown"},
                items=[
                    {"type": "message", "role": "user", "content": message_text}
                ]
            )
            conversation_id = conversation.id
            db.save_conversation_id(chat_id, conversation_id)
            logger.info(f"Created new conversation for user {chat_id}: {conversation_id}")
        
        # Make response using existing or new conversation with error recovery
        max_retries = 1
        retry_count = 0
        response = None
        
        while retry_count <= max_retries and response is None:
            try:
                if conversation_id:
                    # Use existing conversation
                    logger.info(f"Making response with existing conversation {conversation_id} (attempt {retry_count + 1})")
                    response = openai_client.responses.create(
                        model="gpt-5-mini",
                        conversation=conversation_id,
                        input=message_text,
                        instructions="You are Donna, a helpful AI personal assistant. You're integrated with a Telegram bot that can help users with calendar management and general questions. Be friendly and concise in your responses.",
                        tools=CALENDAR_TOOLS,
                        tool_choice="auto"
                    )
                else:
                    # This shouldn't happen since we just created the conversation above,
                    # but handle it as a fallback
                    logger.warning(f"No conversation ID found for user {chat_id} after creation")
                    response = openai_client.responses.create(
                        model="gpt-5-mini", 
                        input=message_text,
                        instructions="You are Donna, a helpful AI personal assistant. You're integrated with a Telegram bot that can help users with calendar management and general questions. Be friendly and concise in your responses.",
                        tools=CALENDAR_TOOLS,
                        tool_choice="auto"
                    )
                break  # Success, exit retry loop
                
            except Exception as e:
                if "No tool output found for function call" in str(e) and retry_count < max_retries:
                    logger.warning(f"Conversation {conversation_id} appears corrupted (pending function call). Resetting...")
                    conversation_id = await reset_conversation_for_user(
                        chat_id, db, openai_client, 
                        reason="Corrupted conversation state with pending function call"
                    )
                    retry_count += 1
                    continue
                else:
                    # Re-raise the exception if it's not a conversation corruption or we've exhausted retries
                    raise
        
        logger.info(f"OpenAI response created: {response.id}, status: {response.status}")
        
        # Process response - handle both function calls and text responses
        if response.status == "completed" and response.output:
            for output_item in response.output:
                # Handle function calls
                if output_item.type == "function_call":
                    logger.info(f"Function call requested: {output_item.name}")
                    
                    # Parse function arguments
                    try:
                        arguments = json.loads(output_item.arguments) if output_item.arguments else {}
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse function arguments: {output_item.arguments}")
                        arguments = {}
                    
                    # Execute the calendar function
                    function_result = await execute_calendar_function(
                        output_item.name, arguments, chat_id, db, oauth_handler
                    )
                    
                    logger.info(f"Function {output_item.name} executed with result: {function_result}")
                    
                    # Provide a direct response based on the function result
                    # The OpenAI Responses API doesn't seem to support manual tool_outputs submission
                    if "events" in function_result and function_result["events"]:
                        events_text = ""
                        for event in function_result["events"]:
                            events_text += f"• {event['title']} at {event['time']}"
                            if event.get('location'):
                                events_text += f" ({event['location']})"
                            events_text += "\n"
                        
                        if output_item.name == "get_today_events":
                            date_info = function_result.get('date', 'today')
                            await update.message.reply_text(
                                f"Here's what you have scheduled for {date_info}:\n\n{events_text}"
                            )
                        elif output_item.name == "get_week_events":
                            week_info = function_result.get('week_range', 'this week')
                            await update.message.reply_text(
                                f"Here's what you have scheduled for {week_info}:\n\n{events_text}"
                            )
                        else:
                            await update.message.reply_text(
                                f"Here's what I found on your calendar:\n\n{events_text}"
                            )
                    elif "error" in function_result:
                        await update.message.reply_text(function_result["error"])
                    else:
                        if output_item.name == "get_today_events":
                            await update.message.reply_text("You have no events scheduled for today.")
                        elif output_item.name == "get_week_events":
                            await update.message.reply_text("You have no events scheduled for this week.")
                        else:
                            await update.message.reply_text("No events found.")
                    
                    return
                
                # Handle regular text responses  
                elif output_item.type == "message" and output_item.role == "assistant":
                    for content_item in output_item.content:
                        if content_item.type == "output_text":
                            assistant_response = content_item.text
                            logger.info(f"Sending response to user {chat_id}: {assistant_response}")
                            await update.message.reply_text(assistant_response)
                            return
            
            # If we couldn't find any processable content
            logger.warning(f"No processable content found in response {response.id}")
            await update.message.reply_text("I received your message but couldn't generate a proper response. Please try again.")
        else:
            logger.error(f"Response failed or incomplete. Status: {response.status}, Error: {response.error}")
            await update.message.reply_text("Sorry, I encountered an issue processing your message. Please try again later.")
        
    except Exception as e:
        logger.error(f"Error handling message for user {chat_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error processing your message. Please try again later."
        )