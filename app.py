import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
import bcrypt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'registration'),
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('todos'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []
        if not name: errors.append('Name is required')
        if not email: errors.append('Email is required')
        if not password: errors.append('Password is required')
        if not confirm_password: errors.append('Confirm password is required')
        if password and confirm_password and password != confirm_password:
            errors.append('Passwords do not match')

        if errors:
            return render_template('register.html', errors=errors, name=name, email=email)

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    return render_template('register.html', errors=['Email Already Exists'], name=name, email=email)
                
                sql = "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)"
                cursor.execute(sql, (email, name, hashed_pw))
                conn.commit()
                
                user_id = cursor.lastrowid
                session['user_id'] = user_id
                session['user_name'] = name
                return redirect(url_for('todos'))
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        errors = []
        if not email: errors.append('Email is required')
        if not password: errors.append('Password is required')

        if errors:
            return render_template('login.html', errors=errors, email=email)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id, name, password_hash FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()

                if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                    session['user_id'] = user['user_id']
                    session['user_name'] = user['name']
                    return redirect(url_for('todos'))
                else:
                    return render_template('login.html', errors=['Invalid email or password'], email=email)
        finally:
            conn.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/todos')
def todos():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT todo_id, title, is_done, created_at FROM todos WHERE user_id = %s ORDER BY todo_id DESC", (user_id,))
            todo_list = cursor.fetchall()
            return render_template('todos.html', todos=todo_list, user_name=session.get('user_name'))
    finally:
        conn.close()

@app.route('/todos/add', methods=['POST'])
def add_todo():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form.get('title', '').strip()
    if not title:
        flash('Title is required')
        return redirect(url_for('todos'))
    if len(title) > 200:
        flash('Title is too long')
        return redirect(url_for('todos'))

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO todos (user_id, title) VALUES (%s, %s)", (user_id, title))
            conn.commit()
    finally:
        conn.close()

    return redirect(url_for('todos'))

@app.route('/todos/update/<int:todo_id>', methods=['POST'])
def update_todo(todo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    title = request.form.get('title', '').strip()
    is_done = 1 if request.form.get('is_done') == 'on' else 0

    if not title:
        flash('Title is required')
        return redirect(url_for('todos'))
    if len(title) > 200:
        flash('Title is too long')
        return redirect(url_for('todos'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE todos SET title = %s, is_done = %s WHERE todo_id = %s AND user_id = %s", (title, is_done, todo_id, user_id))
            conn.commit()
    finally:
        conn.close()

    return redirect(url_for('todos'))

@app.route('/todos/delete/<int:todo_id>', methods=['POST'])
def delete_todo(todo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM todos WHERE todo_id = %s AND user_id = %s", (todo_id, user_id))
            conn.commit()
    finally:
        conn.close()

    return redirect(url_for('todos'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)