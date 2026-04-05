from flask import Blueprint, render_template, session, redirect
from firebase_config import db
from datetime import datetime
import pytz

dashboard = Blueprint("dashboard", __name__)

@dashboard.route("/dashboard")
def dashboard_home():

    # 🔒 Check login
    if "user" not in session:
        return redirect("/")

    # ✅ Get office_id from session (IMPORTANT)
    office_id = session.get("office_id")

    office_name = None
    open_time = None
    close_time = None

    # Sri Lanka time
    colombo = pytz.timezone("Asia/Colombo")
    now = datetime.now(colombo)

    # ✅ Fetch office data
    if office_id:
        try:
            doc = db.collection("OFFICES").document(office_id).get()

            if doc.exists:
                data = doc.to_dict()
                office_name = data.get("name")
                open_time = data.get("openTime")
                close_time = data.get("closeTime")

        except Exception as e:
            print("Error:", e)

    # ✅ PASS office_id to template
    return render_template(
        "dashboard.html",
        user=session.get("user"),
        office_name=office_name,
        open_time=open_time,
        close_time=close_time,
        office_id=office_id
    )