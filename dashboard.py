# app/routes/dashboard.py
from flask import Blueprint, render_template, session, redirect, url_for
from app import mysql
from datetime import date # Import the date object
import MySQLdb.cursors # Import the cursor library

dashboard_bp = Blueprint('dashboard', __name__)

def update_released_inmates():
    """
    This function updates the status of inmates whose release date has passed.
    It now lives in this file to prevent circular import errors.
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE inmates 
            SET status = 'Released'
            WHERE status = 'Active' AND release_date < %s
        """, (date.today(),))
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Error in update_released_inmates: {e}")


@dashboard_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    role = session.get('role')
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor) # Use DictCursor for consistency

    # Automatically update released inmates when the dashboard is accessed
    update_released_inmates()

    # Common stats
    cur.execute("SELECT COUNT(*) AS count FROM inmates WHERE status = 'Active'")
    active_inmates = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) AS count FROM inmates WHERE status = 'Released'")
    released_inmates = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) AS count FROM visitors WHERE visit_date = CURDATE()")
    today_visitors = cur.fetchone()['count']

    cur.execute("""
        SELECT name, release_date 
        FROM inmates 
        WHERE release_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        AND status = 'Active'
    """)
    upcoming_releases = cur.fetchall()
    
    # Fetch any recent alerts to display on the dashboard
    try:
        cur.execute("SELECT message FROM alerts ORDER BY created_at DESC LIMIT 5")
        recent_alerts_tuples = cur.fetchall()
        recent_alerts = [item['message'] for item in recent_alerts_tuples]
    except Exception:
        recent_alerts = []

    # Chart data logic
    cur.execute("""
        SELECT DATE_FORMAT(admission_date, '%%Y-%%m') AS month, COUNT(*) AS count
        FROM inmates
        WHERE admission_date >= CURDATE() - INTERVAL 12 MONTH
        GROUP BY month
        ORDER BY month ASC
    """)
    chart_data = cur.fetchall()

    chart_labels = [row['month'] for row in chart_data]
    chart_values = [row['count'] for row in chart_data]

    cur.close()

    return render_template(
        'dashboard.html',
        role=role,
        active_inmates=active_inmates,
        released_inmates=released_inmates,
        today_visitors=today_visitors,
        upcoming_releases=upcoming_releases,
        recent_alerts=recent_alerts,
        chart_labels=chart_labels,
        chart_values=chart_values
    )
