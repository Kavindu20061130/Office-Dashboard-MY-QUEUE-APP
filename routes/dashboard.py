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

    # 🔹 Counters
    counters = db.collection("COUNTERS").stream()
    counters_list = list(counters)

    counters_count = sum(
        1 for c in counters_list if c.to_dict().get("status") == "active"
    )

     # FETCH TOKENS
    tokens = db.collection("TOKENS").stream()
    tokens_list = list(tokens)

    print("TOTAL TOKENS:", len(tokens_list))

    # 🔹 Waiting
    waiting_count = sum(
        1 for t in tokens_list if t.to_dict().get("status") == "waiting"
    )

    # 🔹 Served
    served_count = sum(
        1 for t in tokens_list if t.to_dict().get("status") == "served"
    )

    # 🔹 Tokens Today
    today = now.date()
    tokens_today = 0

    for t in tokens_list:
        data = t.to_dict()
        booked_time = data.get("bookedtime")

        if booked_time:
            if hasattr(booked_time, "to_datetime"):
                booked_dt = booked_time.to_datetime()
            else:
                booked_dt = booked_time

            # Convert to Colombo timezone
            booked_dt = booked_dt.astimezone(colombo)

            # Compare ONLY date
            if booked_dt.date() == now.date():
                tokens_today += 1
    
    # 🔹 Fetch Queues
    queues = db.collection("QUEUES").stream()
    queues_list = []

    for q in queues:
        data = q.to_dict()
        office_ref = data.get("officeId")

        print("-----")
        print("RAW REF:", office_ref)
        print("REF ID:", getattr(office_ref, "id", "NO ID"))
        print("SESSION:", office_id)

        
        if office_ref and getattr(office_ref, "id", None) == office_id:
            print("MATCH FOUND ✅")

            queues_list.append({
                "name": data.get("name"),
                "service": data.get("serviceId").id if data.get("serviceId") else "N/A",
                "counters": data.get("counterId").id if data.get("counterId") else "N/A",
                "limit": data.get("maxCapacity"),
                "status": data.get("status")
            })

    # PASS all data to template
    return render_template(
    "dashboard.html",
    user=session.get("user"),
    office_name=office_name,
    open_time=open_time,
    close_time=close_time,
    office_id=office_id,
    current_time=now.strftime("%Y-%m-%d %H:%M:%S"),
    counters_count=counters_count,
    waiting_count=waiting_count,
    served_count=served_count,
    tokens_today=tokens_today, 
    queues=queues_list
)
    