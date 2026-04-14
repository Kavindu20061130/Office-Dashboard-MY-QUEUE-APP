from flask import Blueprint, render_template, session, redirect, url_for

# Create the blueprint
counter_control = Blueprint('counter_control', __name__, url_prefix='/counter-control')

@counter_control.route('/')
@counter_control.route('/dashboard')
def counter_dashboard_home():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Using countercontrol.html template
    return render_template('countercontrol.html', 
                         office_name=session.get('office_name'),
                         office_id=session.get('office_id'))