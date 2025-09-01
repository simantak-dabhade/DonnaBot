# Donna

- Donna is a modern, conversational AI personal assistant built with Python, Telegram Bot API, and OpenAI GPT-5 Mini.
  She helps you manage your calendar, answer questions, and handle everyday tasks through natural, human-like conversations.

✨ Features

Core Capabilities
• 🗣 Natural Conversations – Chat naturally, with context remembered across turns.
• 📅 Google Calendar Integration – Connect, view, and manage events.
• 🤖 Smart Function Calling – Automatically checks your calendar when relevant.
• 🧠 Persistent Memory – Keeps track of conversation state.
• ⚡ Error Recovery – Handles failures gracefully and keeps the chat going.

Project structure

```
donna/
├── main.py                # Bot initialization and configuration
├── database.py            # SQLite operations (users + conversations)
├── oauth_handler.py       # Google Calendar OAuth2 integration
├── handlers/              # Command and message handlers
│   ├── start.py
│   ├── help.py
│   ├── connect_calendar.py
│   ├── calendar_status.py
│   ├── today.py
│   ├── disconnect_calendar.py
│   └── message.py
├── credentials.json       # Google OAuth2 credentials
├── pyproject.toml         # Dependencies and config
└── donna.db               # SQLite database (auto-created)
```

## 🚀 Setup & Installation

Prerequisites
• Python 3.13+
• uv package manager
• Google Cloud Console account (Calendar API enabled)
• Telegram Bot Token (from @BotFather)
• OpenAI API Key

### 1. Clone and install

```
git clone <repository-url>
cd donna
uv sync
```

### 2. Configure env

create a .env file

```
TELEGRAM_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Google Calendar Setup

    1.	Create or select a Google Cloud project.
    2.	Enable Google Calendar API.
    3.	Create OAuth2 credentials → choose Web application.
    4.	Add redirect URI: http://localhost:8080/oauth2callback.
    5.	Download credentials.json and place it in the project root.

### 4. Run!

```
uv run python main.py
```

run the `/start` or `/connect_calendar`, then chat in natural lanugage!
