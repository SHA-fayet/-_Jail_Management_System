from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app import mysql
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import MySQLdb.cursors

auth_bp = Blueprint('auth', __name__)

# ======================
#  AUTHENTICATION LOGIC
# ======================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You must log in first!', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required!', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        
        # This check will fail until you run the password hashing utility
        if user and check_password_hash(user['password'], password):
            session.permanent = True # Makes the session last longer
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    session.clear()
    # Add the flash message here so it appears on the login page after redirect
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

# ==============================================================================
# == ONE-TIME PASSWORD HASHING UTILITY (VITAL STEP) ============================
# ==============================================================================
@auth_bp.route('/hash_existing_passwords')
@login_required
@admin_required
def hash_passwords_utility():
    """
    This is a one-time utility to find all plain-text passwords and
    convert them to secure hashes. Run this once after implementing hashing.
    """
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT id, password FROM users WHERE password NOT LIKE 'pbkdf2:sha256%%'")
        users_to_update = cur.fetchall()

        if not users_to_update:
            return "<h1>Password Fix Utility</h1><p>No plain-text passwords found to update. All users appear to be hashed already.</p>"

        count = 0
        for user in users_to_update:
            plain_password = user['password']
            hashed_password = generate_password_hash(plain_password)
            cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user['id']))
            count += 1
        
        mysql.connection.commit()
        cur.close()
        
        message = f"Successfully updated {count} user password(s) to hashes. This utility should now be removed from auth.py for security."
        return f"<h1>Password Fix Complete</h1><p>{message}</p>"
    except Exception as e:
        return f"<h1>An Error Occurred</h1><p>Could not update passwords. Error: {e}</p>"
