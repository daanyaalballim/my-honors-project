from database import get_db_connection
import bcrypt
from config import Config

def register_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM Users WHERE username = ?", (username,))
    if cursor.fetchone():
        return False
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
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


def update_user_profile(user_id, updates):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    valid_fields = ['language', 'tone', 'persona_type', 'persona_key', 'custom_persona', 'explanation_style']
    updates = {k: v for k, v in updates.items() if k in valid_fields}
    
    if updates:
        set_clause = ", ".join(f"{field} = ?" for field in updates.keys())
        values = list(updates.values())
        values.append(user_id)
        
        cursor.execute(
            f"UPDATE Users SET {set_clause} WHERE user_id = ?",
            values
        )
        conn.commit()
    
    conn.close()