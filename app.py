from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from auth import register_user, verify_user
from database import get_user_chats, get_chat_messages, create_new_chat, add_message_to_chat
from chat_handler import process_query
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')


@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    """Custom datetime formatter filter"""
    if isinstance(value, str):
        # If it's a string from SQLite, parse it first
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value
    return value.strftime(format)


@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('chat'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = verify_user(username, password)
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if register_user(username, password):
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists', 'danger')
    return render_template('register.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        # Handle new chat creation
        if 'new_chat' in request.form:
            chat_id = create_new_chat(user_id)
            return redirect(url_for('chat', chat_id=chat_id))
        
        # Handle message submission
        chat_id = request.form.get('chat_id')
        message = request.form.get('message')
        
        if message and chat_id:
            # Add user message to database
            add_message_to_chat(chat_id, user_id, 'user', message)
            
            # Process query and get AI response
            ai_response = process_query(user_id, message, chat_id)
            
            # Add AI response to database
            add_message_to_chat(chat_id, user_id, 'assistant', ai_response)
            
            return jsonify({'response': ai_response})
    
    # Get or create chat
    chat_id = request.args.get('chat_id')
    if not chat_id:
        chats = get_user_chats(user_id)
        chat_id = chats[0]['chat_id'] if chats else create_new_chat(user_id)
    
    messages = get_chat_messages(chat_id)
    chats = get_user_chats(user_id)
    
    return render_template('chat.html', 
                         messages=messages, 
                         chats=chats, 
                         current_chat_id=chat_id,
                         username=session['username'])

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    chats = get_user_chats(user_id)
    return render_template('history.html', chats=chats)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)