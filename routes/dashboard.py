# Import required modules from Flask
from flask import Blueprint, render_template, session, redirect

# Import Firestore database instance
from firebase_config import db

# Import datetime to work with dates and time
from datetime import datetime

# Import pytz for timezone handling
import pytz


# Create a Blueprint named "dashboard"
# This helps organize routes in Flask apps
dashboard = Blueprint("dashboard", __name__)


# Define route for "/dashboard"
@dashboard.route("/dashboard")
def dashboard_home():

    # 🔒 Check if user is logged in (session exists)
    if "user" not in session:
        return redirect("/")  # Redirect to login page if not logged in

    # Get selected office ID from session
    office_id = session.get("office")

    # Initialize variables (default values)
    office_name = None
    open_time = None
    close_time = None
    tokens_today_count = 0  # Count of today's tokens

    # Set timezone to Sri Lanka (Colombo)
    colombo = pytz.timezone("Asia/Colombo")

    # Get current date and time in Colombo timezone
    now = datetime.now(colombo)

    # Format today's date as string (YYYY-MM-DD)
    today_str = now.strftime("%Y-%m-%d")

    # Proceed only if office_id exists
    if office_id:
        try:
            # Reference to selected office document
            office_ref = db.collection("OFFICES").document(office_id)

            # 🔹 Get office details
            doc = office_ref.get()  # Fetch document

            if doc.exists:  # Check if document exists
                data = doc.to_dict()  # Convert document to dictionary

                # Extract office details
                office_name = data.get("name")
                open_time = data.get("openTime")
                close_time = data.get("closeTime")

            # 🔥 Get ALL tokens from TOKENS collection (no filter applied here)
            tokens = db.collection("TOKENS").stream()

            # Reset today's token count
            tokens_today_count = 0

            # 🔁 Loop through each token document
            for t in tokens:
                data = t.to_dict()  # Convert token document to dictionary

                # Get office reference stored in token
                token_office_ref = data.get("officeid")

                # ✅ Apply manual filtering
                if (
                    token_office_ref  # Ensure office reference exists
                    and token_office_ref.id == office_id   # Match office ID
                    and data.get("Date") == today_str      # Match today's date
                ):
                    tokens_today_count += 1  # Increment count

        except Exception as e:
            # Print any errors in console for debugging
            print("Error:", e)

    # 🎯 Render dashboard template and pass data to HTML
    return render_template(
        "dashboard.html",
        user=session.get("user"),         # Logged-in user
        office_name=office_name,          # Office name
        open_time=open_time,              # Opening time
        close_time=close_time,            # Closing time
        tokens_today=tokens_today_count   # Today's token count
    )