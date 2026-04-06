from flask import Blueprint, render_template, session, redirect
from firebase_config import db
from datetime import datetime
import pytz

dashboard = Blueprint("dashboard", __name__)

@dashboard.route("/dashboard")
def dashboard_home():
    #  Check login
    if "user" not in session:
        print(" No user in session, redirecting to login")
        return redirect("/")

    # ✅ Get office_id from session
    office_id = session.get("office_id")
    
    if not office_id:
        print(" No office_id in session, redirecting to login")
        return redirect("/")

    office_name = None
    open_time = None
    close_time = None

    # Sri Lanka time
    colombo = pytz.timezone("Asia/Colombo")
    now = datetime.now(colombo)

    #  Fetch office data
    if office_id:
        try:
            doc = db.collection("OFFICES").document(office_id).get()

            if doc.exists:
                data = doc.to_dict()
                office_name = data.get("name")
                open_time = data.get("openTime")
                close_time = data.get("closeTime")
                print(f"✅ Office data loaded: {office_name}")
            else:
                print(f"❌ Office not found: {office_id}")

        except Exception as e:
            print(f"❌ Error fetching office: {e}")

    # PASS all data to template
    return render_template(
        "dashboard.html",
        user=session.get("user"),
        office_name=office_name,
        open_time=open_time,
        close_time=close_time,
        office_id=office_id,
        current_time=now.strftime("%Y-%m-%d %H:%M:%S")
    )