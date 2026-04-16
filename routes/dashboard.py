from flask import Blueprint, render_template, session, redirect, request, jsonify
from firebase_config import db
from datetime import datetime
import pytz

dashboard = Blueprint("dashboard", __name__)

@dashboard.route("/dashboard")
def dashboard_home():
    if "user" not in session:
        return redirect("/")

    office_id = session.get("office_id")
    if not office_id:
        return redirect("/")

    office_name = None
    open_time = None
    close_time = None
    colombo = pytz.timezone("Asia/Colombo")
    now = datetime.now(colombo)

    # Fetch office data
    try:
        doc = db.collection("OFFICES").document(office_id).get()
        if doc.exists:
            data = doc.to_dict()
            office_name = data.get("name")
            open_time = data.get("openTime")
            close_time = data.get("closeTime")
    except Exception as e:
        print(f"Error fetching office: {e}")

    # Counters count (active)
    counters_count = 0
    counters = db.collection("COUNTERS").where("officeId", "==", db.collection("OFFICES").document(office_id)).stream()
    for c in counters:
        if c.to_dict().get("status") == "active":
            counters_count += 1

    # Tokens for this office
    tokens = db.collection("TOKENS").where("officeId", "==", db.collection("OFFICES").document(office_id)).stream()
    tokens_list = list(tokens)
    waiting_count = sum(1 for t in tokens_list if t.to_dict().get("status") == "waiting")
    served_count = sum(1 for t in tokens_list if t.to_dict().get("status") == "served")

    # Tokens today
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
            booked_dt = booked_dt.astimezone(colombo)
            if booked_dt.date() == today:
                tokens_today += 1

    # Queues with names resolved
    queues_list = []
    queues = db.collection("QUEUES").where("officeId", "==", db.collection("OFFICES").document(office_id)).stream()
    for q in queues:
        data = q.to_dict()
        
        # Get service name
        service_ref = data.get("serviceId")
        service_name = "N/A"
        if service_ref:
            try:
                service_doc = service_ref.get()
                if service_doc.exists:
                    service_name = service_doc.to_dict().get("name", service_ref.id)
                else:
                    service_name = service_ref.id
            except:
                service_name = str(service_ref.id) if hasattr(service_ref, 'id') else "N/A"
        
        # Get counter name
        counter_ref = data.get("counterId")
        counter_name = "N/A"
        if counter_ref:
            try:
                counter_doc = counter_ref.get()
                if counter_doc.exists:
                    counter_name = counter_doc.to_dict().get("name", counter_ref.id)
                else:
                    counter_name = counter_ref.id
            except:
                counter_name = str(counter_ref.id) if hasattr(counter_ref, 'id') else "N/A"
        
        queues_list.append({
            "name": data.get("name"),
            "service": service_name,
            "counters": counter_name,
            "limit": data.get("maxCapacity"),
            "status": data.get("status")
        })

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

@dashboard.route("/dashboard/api/data")
def api_dashboard_data():
    if "user" not in session or "office_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    office_id = session["office_id"]
    colombo = pytz.timezone("Asia/Colombo")
    now = datetime.now(colombo)

    # Office details
    office_doc = db.collection("OFFICES").document(office_id).get()
    office_data = office_doc.to_dict() if office_doc.exists else {}
    open_time = office_data.get("openTime")
    close_time = office_data.get("closeTime")
    office_name = office_data.get("name")

    # Counters count (active)
    counters_count = 0
    counters = db.collection("COUNTERS").where("officeId", "==", db.collection("OFFICES").document(office_id)).stream()
    for c in counters:
        if c.to_dict().get("status") == "active":
            counters_count += 1

    # Tokens
    tokens = db.collection("TOKENS").where("officeId", "==", db.collection("OFFICES").document(office_id)).stream()
    tokens_list = list(tokens)
    waiting_count = sum(1 for t in tokens_list if t.to_dict().get("status") == "waiting")
    served_count = sum(1 for t in tokens_list if t.to_dict().get("status") == "served")

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
            booked_dt = booked_dt.astimezone(colombo)
            if booked_dt.date() == today:
                tokens_today += 1

    # Queues with names resolved
    queues_list = []
    queues = db.collection("QUEUES").where("officeId", "==", db.collection("OFFICES").document(office_id)).stream()
    for q in queues:
        data = q.to_dict()
        
        # Get service name
        service_ref = data.get("serviceId")
        service_name = "N/A"
        if service_ref:
            try:
                service_doc = service_ref.get()
                if service_doc.exists:
                    service_name = service_doc.to_dict().get("name", service_ref.id)
                else:
                    service_name = service_ref.id
            except:
                service_name = str(service_ref.id) if hasattr(service_ref, 'id') else "N/A"
        
        # Get counter name
        counter_ref = data.get("counterId")
        counter_name = "N/A"
        if counter_ref:
            try:
                counter_doc = counter_ref.get()
                if counter_doc.exists:
                    counter_name = counter_doc.to_dict().get("name", counter_ref.id)
                else:
                    counter_name = counter_ref.id
            except:
                counter_name = str(counter_ref.id) if hasattr(counter_ref, 'id') else "N/A"
        
        queues_list.append({
            "name": data.get("name"),
            "service": service_name,
            "counters": counter_name,
            "limit": data.get("maxCapacity"),
            "status": data.get("status")
        })

    return jsonify({
        "office_name": office_name,
        "open_time": open_time,
        "close_time": close_time,
        "counters_count": counters_count,
        "waiting_count": waiting_count,
        "served_count": served_count,
        "tokens_today": tokens_today,
        "queues": queues_list
    })

@dashboard.route("/dashboard/update_hours", methods=["POST"])
def update_office_hours():
    if "user" not in session or "office_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    open_time = data.get("openTime")
    close_time = data.get("closeTime")
    office_id = session["office_id"]

    if not open_time or not close_time:
        return jsonify({"error": "Missing openTime or closeTime"}), 400

    try:
        db.collection("OFFICES").document(office_id).update({
            "openTime": open_time,
            "closeTime": close_time
        })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500