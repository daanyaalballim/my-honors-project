import sqlite3
from sqlite3 import Connection
from config import Config
from typing import Dict, List, Optional

def get_db_connection() -> Connection:
    """Create and return a database connection."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    
    # Create Users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Chats table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Chats (
            chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users (user_id)
        )
    ''')
    
    # Create Messages table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,  -- 'user' or 'assistant'
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES Chats (chat_id),
            FOREIGN KEY (user_id) REFERENCES Users (user_id)
        )
    ''')

    try:
        conn.execute('ALTER TABLE Users ADD COLUMN language TEXT DEFAULT "english"')
        conn.execute('ALTER TABLE Users ADD COLUMN tone TEXT DEFAULT "warm"')
        conn.execute('ALTER TABLE Users ADD COLUMN persona_type TEXT DEFAULT "predefined"')
        conn.execute('ALTER TABLE Users ADD COLUMN persona_key TEXT DEFAULT "peer_mentor"')
        conn.execute('ALTER TABLE Users ADD COLUMN custom_persona TEXT DEFAULT ""')
        conn.execute('ALTER TABLE Users ADD COLUMN explanation_style TEXT DEFAULT "detailed"')
        conn.commit()
    except sqlite3.OperationalError:
        pass 
    
    conn.commit()
    conn.close()

def add_user(username: str, password_hash: str) -> int:
    """Add a new user to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Users (username, password_hash) VALUES (?, ?)",
        (username, password_hash)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def verify_user(username: str, password_hash: str) -> Optional[Dict]:
    """Verify user credentials."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username FROM Users WHERE username = ? AND password_hash = ?",
        (username, password_hash)
    )
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def create_new_chat(user_id: int) -> int:
    """Create a new chat session for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Chats (user_id) VALUES (?)",
        (user_id,)
    )
    chat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return chat_id

def get_user_chats(user_id: int) -> List[Dict]:
    """Get all chat sessions for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT chat_id, created_at FROM Chats WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    chats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return chats

def get_chat_messages(chat_id: int) -> List[Dict]:
    """Get all messages for a chat session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT message_id, role, content, timestamp FROM Messages WHERE chat_id = ? ORDER BY timestamp ASC",
        (chat_id,)
    )
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def get_recent_messages(chat_id: int, limit: int = 5) -> List[Dict]:
    """Get recent messages for a chat session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM Messages WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
        (chat_id, limit)
    )
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages[::-1]  # Reverse to maintain chronological order

def add_message_to_chat(chat_id: int, user_id: int, role: str, content: str):
    """Add a message to a chat session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Messages (chat_id, user_id, role, content) VALUES (?, ?, ?, ?)",
        (chat_id, user_id, role, content)
    )
    conn.commit()
    conn.close()

init_db()