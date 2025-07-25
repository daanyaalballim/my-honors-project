from database import get_db_connection
import bcrypt
from config import Config

def register_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if username already exists
    cursor.execute("SELECT username FROM Users WHERE username = ?", (username,))
    if cursor.fetchone():
        return False
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Insert new user
    cursor.execute(
        "INSERT INTO Users (username, password_hash) VALUES (?, ?)",
        (username, password_hash)
    )
    conn.commit()
    conn.close()
    return True

def verify_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT user_id, username, password_hash FROM Users WHERE username = ?",
        (username,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
        return {
            'user_id': user['user_id'],
            'username': user['username']
        }
    return None