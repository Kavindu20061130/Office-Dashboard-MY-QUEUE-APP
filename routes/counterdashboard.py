from flask import Blueprint, render_template

# Create Blueprint
counterdashboard = Blueprint("counterdashboard", __name__)

# Route
@counterdashboard.route("/counterdashboard")
def counter_dashboard_home():
    return render_template("counterdashboard.html")