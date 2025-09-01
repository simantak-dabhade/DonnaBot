"""
OAuth callback handler for Google Calendar integration

Flask web server to handle Google OAuth2 callbacks.
Based on legacy implementation with URL parameters.
"""

import logging
import threading
import secrets
from flask import Flask, request, redirect, jsonify, session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from database import Database

logger = logging.getLogger(__name__)

# Storage for OAuth flows and user data
flow_store = {}
chat_id_store = {}

class OAuthHandler:
    """Handle OAuth2 callbacks from Google"""
    
    def __init__(self, database: Database):
        self.app = Flask(__name__)
        self.app.secret_key = secrets.token_urlsafe(32)
        self.db = database
        self.server_thread = None
        self.scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes for OAuth handling"""
        
        @self.app.route('/start_google_auth')
        def start_google_auth():
            """Start Google OAuth flow with chat_id as parameter"""
            try:
                logger.info("=== Starting Google OAuth flow ===")
                
                state = secrets.token_urlsafe()
                session[f'oauth_state_{state}'] = state
                logger.debug(f"Generated OAuth state: {state}")
                
                # Get chat_id from URL parameter
                chat_id = request.args.get('chat_id')
                if not chat_id:
                    logger.error("Missing chat_id parameter in OAuth request")
                    return "❌ Missing chat_id parameter", 400
                
                logger.info(f"OAuth flow requested for chat_id: {chat_id}")
                
                # Create OAuth flow for web application
                logger.debug("Creating OAuth flow from credentials.json")
                flow = Flow.from_client_secrets_file(
                    'credentials.json',
                    scopes=self.scopes
                )
                flow.redirect_uri = 'http://localhost:8080/oauth2callback'
                logger.debug(f"Set redirect URI: {flow.redirect_uri}")
                
                auth_url, _ = flow.authorization_url(
                    prompt='consent', 
                    access_type='offline', 
                    state=state
                )
                logger.info(f"Generated OAuth URL: {auth_url}")
                
                # Store flow and chat_id for callback
                flow_store[state] = flow
                chat_id_store[state] = chat_id
                logger.debug(f"Stored flow and chat_id for state: {state}")
                
                # Redirect user to Google OAuth
                logger.info(f"Redirecting user to Google OAuth for chat_id: {chat_id}")
                return redirect(auth_url)
                
            except FileNotFoundError as e:
                logger.error(f"Credentials file not found: {e}")
                return "❌ OAuth configuration error: credentials.json not found", 500
            except Exception as e:
                logger.error(f"Error starting OAuth flow: {e}", exc_info=True)
                return f"❌ OAuth flow error: {str(e)}", 500
        
        @self.app.route('/oauth2callback')
        def oauth2callback():
            """Handle OAuth callback from Google"""
            try:
                logger.info("=== OAuth callback received ===")
                logger.debug(f"Callback request args: {dict(request.args)}")
                
                # Validate state parameter
                returned_state = request.args.get('state')
                logger.debug(f"Returned state: {returned_state}")
                
                if not returned_state:
                    logger.error("Missing state parameter in callback")
                    return "❌ Missing state parameter", 400
                
                stored_state = session.get(f'oauth_state_{returned_state}')
                logger.debug(f"Stored state: {stored_state}")
                
                if not stored_state or stored_state != returned_state:
                    logger.error(f"Invalid state parameter. Returned: {returned_state}, Stored: {stored_state}")
                    return "❌ Invalid state parameter", 400
                
                auth_code = request.args.get('code')
                error = request.args.get('error')
                
                if error:
                    logger.error(f"OAuth error from Google: {error}")
                    return f"❌ Authorization failed: {error}", 400
                
                if not auth_code:
                    logger.error("Missing authorization code in callback")
                    return "❌ Missing authorization code", 400
                
                logger.debug(f"Authorization code received (length: {len(auth_code)})")
                
                # Get stored flow and chat_id
                flow = flow_store.get(returned_state)
                chat_id = chat_id_store.get(returned_state)
                
                if not flow or not chat_id:
                    logger.error(f"Missing flow or chat_id in storage for state: {returned_state}")
                    logger.debug(f"Available states: {list(flow_store.keys())}")
                    return "❌ Session expired, please try again", 400
                
                logger.info(f"Processing OAuth callback for chat_id: {chat_id}")
                
                # Exchange code for tokens
                logger.debug("Exchanging authorization code for tokens")
                flow.fetch_token(code=auth_code)
                credentials = flow.credentials
                logger.info("Successfully obtained OAuth tokens")
                
                # Convert credentials to dict for storage
                tokens = {
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes,
                    'expiry': credentials.expiry.isoformat() if credentials.expiry else None
                }
                logger.debug(f"Token data prepared for storage (has refresh_token: {bool(tokens.get('refresh_token'))})")
                
                # Save tokens to database
                logger.debug("Saving tokens to database")
                if self.db.save_calendar_tokens(int(chat_id), tokens):
                    logger.info(f"✅ Calendar successfully connected for user {chat_id}")
                    
                    # Clean up storage
                    flow_store.pop(returned_state, None)
                    chat_id_store.pop(returned_state, None)
                    session.pop(f'oauth_state_{returned_state}', None)
                    logger.debug("Cleaned up temporary OAuth storage")
                    
                    return """
                    <html>
                        <body style='font-family: Arial, sans-serif; text-align: center; padding: 50px;'>
                            <h2>✅ Calendar Connected Successfully!</h2>
                            <p>You can now close this tab and return to Telegram.</p>
                            <p>Your calendar is now connected to Donna Bot.</p>
                            <script>
                                setTimeout(function(){ window.close(); }, 3000);
                            </script>
                        </body>
                    </html>
                    """
                else:
                    logger.error(f"Failed to save tokens to database for user {chat_id}")
                    return "❌ Failed to save calendar connection", 500
                    
            except Exception as e:
                logger.error(f"OAuth callback error: {e}", exc_info=True)
                return f"❌ Authorization failed: {str(e)}", 500
        
        @self.app.route('/health')
        def health_check():
            """Health check endpoint"""
            return jsonify({'status': 'ok'})
    
    def start_server(self, host='localhost', port=8080):
        """Start Flask server in background thread"""
        if self.server_thread and self.server_thread.is_alive():
            logger.info("OAuth server already running")
            return
        
        logger.info(f"=== Starting OAuth server on {host}:{port} ===")
        
        def run_server():
            try:
                logger.debug(f"Flask app routes registered: {[rule.rule for rule in self.app.url_map.iter_rules()]}")
                self.app.run(host=host, port=port, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"Flask server error: {e}", exc_info=True)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(f"✅ OAuth server started successfully on http://{host}:{port}")
        logger.info(f"Available endpoints:")
        logger.info(f"  - Health check: http://{host}:{port}/health")
        logger.info(f"  - OAuth start: http://{host}:{port}/start_google_auth?chat_id=<ID>")
        logger.info(f"  - OAuth callback: http://{host}:{port}/oauth2callback")
    
    def stop_server(self):
        """Stop Flask server"""
        # Flask doesn't have a built-in way to stop, but since we're using daemon threads,
        # they'll stop when the main program exits
        if self.server_thread:
            logger.info("OAuth server will stop when main program exits")
    
    def generate_auth_url(self, chat_id: int) -> str:
        """Generate authorization URL for a specific user"""
        # Return URL to our start_google_auth endpoint with chat_id parameter
        return f"http://localhost:8080/start_google_auth?chat_id={chat_id}"
    
    def _get_service(self, token_data: dict):
        """Get authenticated Calendar service and refresh tokens if needed"""
        try:
            # Create credentials from stored token data
            creds = Credentials.from_authorized_user_info(token_data)
            
            # Refresh token if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                
                # Update token data with new access token
                token_data.update({
                    'token': creds.token,
                    'expiry': creds.expiry.isoformat() if creds.expiry else None
                })
            
            # Build Calendar service
            service = build('calendar', 'v3', credentials=creds)
            return service, token_data
            
        except Exception as e:
            logger.error(f"Error creating calendar service: {e}")
            raise
    
    def get_upcoming_events(self, token_data: dict, max_results: int = 10):
        """Get upcoming calendar events"""
        try:
            service, updated_tokens = self._get_service(token_data)
            
            # Get events from now
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No Title'),
                    'start': start,
                    'description': event.get('description', ''),
                    'location': event.get('location', '')
                })
            
            return formatted_events, updated_tokens
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            raise
    
    def get_today_events(self, token_data: dict):
        """Get today's calendar events"""
        try:
            service, updated_tokens = self._get_service(token_data)
            
            # Get start and end of today
            today = datetime.now().date()
            start_of_day = datetime.combine(today, datetime.min.time()).isoformat() + 'Z'
            end_of_day = datetime.combine(today, datetime.max.time()).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No Title'),
                    'start': start,
                    'description': event.get('description', ''),
                    'location': event.get('location', '')
                })
            
            return formatted_events, updated_tokens
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting today's events: {e}")
            raise
    
    def get_week_events(self, token_data: dict):
        """Get this week's calendar events"""
        try:
            service, updated_tokens = self._get_service(token_data)
            
            # Get start and end of current week (Monday to Sunday)
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())  # Monday
            end_of_week = start_of_week + timedelta(days=6)  # Sunday
            
            start_of_week_str = datetime.combine(start_of_week, datetime.min.time()).isoformat() + 'Z'
            end_of_week_str = datetime.combine(end_of_week, datetime.max.time()).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_of_week_str,
                timeMax=end_of_week_str,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No Title'),
                    'start': start,
                    'description': event.get('description', ''),
                    'location': event.get('location', '')
                })
            
            return formatted_events, updated_tokens
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting week's events: {e}")
            raise