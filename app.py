from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from auth import register_user, verify_user, update_user_profile
from database import get_user_chats, get_chat_messages, create_new_chat, add_message_to_chat
from chat_handler import process_query
import os
from dotenv import load_dotenv
from datetime import datetime
from constants import LANGUAGES, LEARNING_STYLES, TONE_PRESETS, PREDEFINED_PERSONAS

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')


@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    """Custom datetime formatter filter"""
    if isinstance(value, str):
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


@app.route('/profile', methods=['GET'])
def profile():
    from database import get_db_connection
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM Users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    
    return render_template('profile.html', user=dict(user), LANGUAGES=LANGUAGES,
                         TONE_PRESETS=TONE_PRESETS,
                         PREDEFINED_PERSONAS=PREDEFINED_PERSONAS,
                         LEARNING_STYLES=LEARNING_STYLES)

@app.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    updates = {
        'language': request.form.get('language'),
        'tone': request.form.get('tone'),
        'persona_type': request.form.get('persona_type'),
        'persona_key': request.form.get('persona_key'),
        'custom_persona': request.form.get('custom_persona'),
        'explanation_style': request.form.get('explanation_style')
    }
    
    update_user_profile(user_id, updates)
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        if 'new_chat' in request.form:
            chat_id = create_new_chat(user_id)
            return redirect(url_for('chat', chat_id=chat_id))
        chat_id = request.form.get('chat_id')
        message = request.form.get('message')
        
        if message and chat_id:
            add_message_to_chat(chat_id, user_id, 'user', message)
            ai_response = process_query(user_id, message, chat_id)
            add_message_to_chat(chat_id, user_id, 'assistant', ai_response)
            
            return jsonify({'response': ai_response})
    
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