from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import mysql
from datetime import datetime, date # Import date
from .auth import login_required
import uuid
import MySQLdb.cursors

visit_request_bp = Blueprint('visit_request', __name__)


# ==============================================================================
# == REGULAR APPLICATION ROUTES FOR THE VISITOR ONLY ================================================


@visit_request_bp.route('/visit_request', methods=['GET', 'POST'])
def visit_request():
    if request.method == 'POST':
        visitor_name = request.form['visitor_name']
        inmate_name = request.form['inmate_name']
        date_requested = request.form.get('date_requested') or datetime.now().strftime('%Y-%m-%d')
        
        tracking_id = uuid.uuid4().hex

        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO visit_requests (visitor_name, inmate_name, date_requested, tracking_id) VALUES (%s, %s, %s, %s)",
                (visitor_name, inmate_name, date_requested, tracking_id)
            )
            notification_message = f"New visit request from '{visitor_name}' for inmate '{inmate_name}'."
            cur.execute("INSERT INTO notifications (message, target_audience) VALUES (%s, 'staff')", (notification_message,))
            mysql.connection.commit()
        finally:
            cur.close()
        
        return redirect(url_for('visit_request.confirmation', tracking_id=tracking_id))
    
    return render_template('visit_request_form.html')

@visit_request_bp.route('/visit_request/confirmation')
def confirmation():
    tracking_id = request.args.get('tracking_id')
    return render_template('visit_request_confirmation.html', tracking_id=tracking_id)

@visit_request_bp.route('/check_visit_status', methods=['GET', 'POST'])
def check_visit_status():
    if request.method == 'POST':
        tracking_id = request.form.get('tracking_id')
        if not tracking_id:
            return render_template('check_visit_status.html')

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM visit_requests WHERE tracking_id = %s", (tracking_id,))
        visit_request = cur.fetchone()
        cur.close()

        if visit_request:
            return render_template('check_visit_status.html', visit_request=visit_request)
        else:
            return render_template('check_visit_status.html', not_found=True)

    return render_template('check_visit_status.html')


@visit_request_bp.route('/manage_visits')
@login_required
def manage_visits():
    if session.get('role') not in ['admin', 'jailer']:
        return "Unauthorized", 403

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM visit_requests ORDER BY date_requested DESC")
    visits = cur.fetchall()
    cur.close()
    return render_template('manage_visits.html', visits=visits)


@visit_request_bp.route('/update_visit_status/<int:id>/<status>')
@login_required
def update_visit_status(id, status):
    if session.get('role') not in ['admin', 'jailer']:
        return "Unauthorized", 403

    if status not in ['Approved', 'Rejected']:
        flash('Invalid status!', 'danger')
        return redirect(url_for('visit_request.manage_visits'))

    cur = mysql.connection.cursor()
    cur.execute("UPDATE visit_requests SET status = %s WHERE id = %s", (status, id))
    mysql.connection.commit()
    cur.close()

    flash(f'Visit {status.lower()}!', 'success')
    return redirect(url_for('visit_request.manage_visits'))



# == VISITOR CHECK-IN FEATURE to check if the visitor is valid or not ==================================================

@visit_request_bp.route('/visitor_check_in', methods=['GET', 'POST'])
# ** FIX: Removed @login_required decorator to make this page public **
def visitor_check_in():
    message = None
    if request.method == 'POST':
        tracking_id = request.form.get('tracking_id')
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # 1. Find the visit request by tracking ID
        cur.execute("SELECT * FROM visit_requests WHERE tracking_id = %s", (tracking_id,))
        visit = cur.fetchone()

        if not visit:
            message = "Check-in Failed: Invalid Tracking ID."
        elif visit['status'] != 'Approved':
            message = f"Check-in Failed: Visit status is '{visit['status']}', not 'Approved'."
        elif visit['date_requested'] != date.today():
            message = f"Check-in Failed: Visit is scheduled for {visit['date_requested'].strftime('%Y-%m-%d')}, not today."
        else:
            # All checks passed, proceed with check-in
            try:
                # Find the inmate's ID from their name
                cur.execute("SELECT id FROM inmates WHERE name = %s", (visit['inmate_name'],))
                inmate = cur.fetchone()
                if not inmate:
                    raise Exception(f"Inmate '{visit['inmate_name']}' not found in database.")
                
                inmate_id = inmate['id']
                
                # Insert a new record into the main visitors table
                cur.execute(
                    "INSERT INTO visitors (visitor_name, inmate_id, visit_date, relation) VALUES (%s, %s, %s, %s)",
                    (visit['visitor_name'], inmate_id, date.today(), 'N/A') # Assuming 'relation' can be 'N/A'
                )
                
                # Update the original request to prevent re-use
                cur.execute("UPDATE visit_requests SET status = 'Completed' WHERE id = %s", (visit['id'],))
                
                mysql.connection.commit()
                message = f"Check-in Successful: Visitor '{visit['visitor_name']}' has been logged for inmate '{visit['inmate_name']}'."
            except Exception as e:
                mysql.connection.rollback()
                message = f"An error occurred: {e}"
            finally:
                cur.close()

        return render_template('visitor_check_in.html', message=message)

    # For a GET request, just show the page
    return render_template('visitor_check_in.html')
