from flask import Blueprint, render_template, session, redirect, request, flash, url_for
from firebase_config import db
from google.cloud.firestore import SERVER_TIMESTAMP
import re

createqueue = Blueprint("createqueue", __name__)

# ---------- Helper: generate next service ID (sequential) ----------
def get_next_service_id():
    services_ref = db.collection("SERVICES")
    docs = services_ref.stream()
    max_num = 0
    for doc in docs:
        match = re.match(r'service_(\d+)', doc.id)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return f"service_{max_num + 1}"

# ---------- Helper: generate next queue base number (sequential) ----------
def get_next_queue_base():
    queues_ref = db.collection("QUEUES")
    docs = queues_ref.stream()
    max_num = 0
    for doc in docs:
        match = re.match(r'queue_(\d+)', doc.id)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return max_num + 1

# ---------- Helper: capacity‑based deactivation (call when token issued) ----------
def check_and_update_queue_status(queue_id):
    queue_ref = db.collection("QUEUES").document(queue_id)
    queue = queue_ref.get().to_dict()
    if queue and queue.get("bookedCount", 0) >= queue.get("maxCapacity", 999999):
        queue_ref.update({"status": "inactive"})
        return True
    return False

# ---------- Route: Create Queue ----------
@createqueue.route("/create-queue", methods=["GET", "POST"])
def create_queue_page():
    if "user" not in session or session.get("role") != "admin":
        flash("Please log in as admin", "error")
        return redirect("/")

    office_id = session.get("office_id")
    if not office_id:
        flash("Office not found in session", "error")
        return redirect(url_for("dashboard.dashboard_home"))

    office_ref = db.collection("OFFICES").document(office_id)
    
    # ===== FIX: Get office details for sidebar =====
    office_doc = office_ref.get()
    office_name = None
    if office_doc.exists:
        office_name = office_doc.to_dict().get("name")
    # =============================================

    if request.method == "GET":
        # Get success data from session if exists
        success_data = session.pop('queue_success_data', None)
        
        # Fetch only services belonging to this office
        services = []
        for doc in db.collection("SERVICES").where("officeId", "==", office_ref).stream():
            data = doc.to_dict()
            services.append({
                "id": doc.id,
                "name": data.get("name", "Unnamed"),
                "charge": data.get("charge", 0)
            })
        services.sort(key=lambda x: int(x['id'].split('_')[1]) if x['id'].startswith('service_') else 0)

        # Fetch counters for this office
        counters = []
        counters_query = db.collection("COUNTERS").where("officeId", "==", office_ref).stream()
        for doc in counters_query:
            data = doc.to_dict()
            counters.append({
                "id": doc.id,
                "name": data.get("name", doc.id)
            })

        letters = [chr(i) for i in range(ord('A'), ord('Z')+1)]
        
        # ===== FIX: Pass office_name and office_id to template =====
        return render_template("create_queue.html",
                               services=services,
                               counters=counters,
                               letters=letters,
                               success_data=success_data,
                               office_name=office_name,
                               office_id=office_id)

    # ---------- POST: create queue(s) ----------
    try:
        # 1. Service
        service_option = request.form.get("service_option")
        if service_option == "existing":
            service_id = request.form.get("existing_service_id")
            if not service_id:
                flash("Please select a service", "error")
                return redirect(url_for("createqueue.create_queue_page"))
            service_ref = db.collection("SERVICES").document(service_id)
        else:
            custom_name = request.form.get("custom_service_name", "").strip()
            custom_charge = request.form.get("custom_service_charge", "").strip()
            if not custom_name or not custom_charge:
                flash("Custom service requires both name and charge", "error")
                return redirect(url_for("createqueue.create_queue_page"))
            new_service_id = get_next_service_id()
            new_service_data = {
                "name": custom_name,
                "charge": int(custom_charge),
                "officeId": office_ref,
                "createdAt": SERVER_TIMESTAMP
            }
            service_ref = db.collection("SERVICES").document(new_service_id)
            service_ref.set(new_service_data)

        # 2. Queue name
        queue_name = request.form.get("queue_name", "").strip()
        if not queue_name:
            flash("Queue name is required", "error")
            return redirect(url_for("createqueue.create_queue_page"))

        # 3. Token prefix
        token_letter = request.form.get("token_letter", "A")
        token_start_num = request.form.get("token_start_number", "1")
        token_start_number = int(token_start_num) if token_start_num.isdigit() else 1
        token_prefix = f"{token_letter}-{token_start_number:03d}"

        # 4. Max capacity & queue type
        max_capacity = int(request.form.get("max_capacity", "50"))
        queue_type = request.form.get("queue_type", "Medium")

        # 5. Auto‑close times (stored, but not acted upon here)
        auto_inactive_time = request.form.get("auto_inactive_time") or None
        auto_active_time = request.form.get("auto_active_time") or None

        # 6. Selected counters (multi‑select)
        selected_counter_ids = request.form.getlist("counters")
        if not selected_counter_ids:
            flash("Please select at least one counter", "error")
            return redirect(url_for("createqueue.create_queue_page"))

        # ----- VALIDATION: Check if any selected counter already has an active queue -----
        conflicting_counters = []
        for counter_id in selected_counter_ids:
            counter_ref = db.collection("COUNTERS").document(counter_id)
            # Query for any active queue linked to this counter
            active_queue_query = db.collection("QUEUES") \
                .where("counterId", "==", counter_ref) \
                .where("status", "==", "active") \
                .limit(1).stream()
            if any(active_queue_query):  # at least one active queue exists
                # Get counter name for better error message
                counter_doc = counter_ref.get()
                counter_name = counter_doc.to_dict().get("name", counter_id) if counter_doc.exists else counter_id
                conflicting_counters.append(counter_name)

        if conflicting_counters:
            flash(f"Cannot create queue(s). The following counters already have an active queue: {', '.join(conflicting_counters)}. "
                  "Please close or deactivate the existing queue first.", "error")
            return redirect(url_for("createqueue.create_queue_page"))
        # -----------------------------------------------------------------------------------

        # 7. Generate sequential queue IDs
        next_base = get_next_queue_base()
        created_ids = []

        # 8. Create one queue document per counter
        for idx, counter_id in enumerate(selected_counter_ids):
            queue_doc_id = f"queue_{next_base + idx}"
            counter_ref = db.collection("COUNTERS").document(counter_id)

            queue_data = {
                "bookedCount": 0,
                "counterId": counter_ref,
                "maxCapacity": max_capacity,
                "name": queue_name,
                "officeId": office_ref,
                "queueType": queue_type,
                "serviceId": service_ref,
                "status": "active",
                "tokenPrefix": token_prefix,
                "tokenStartNumber": token_start_number,
                "tokenLetter": token_letter,
                "autoInactiveTime": auto_inactive_time,
                "autoActiveTime": auto_active_time,
                "createdAt": SERVER_TIMESTAMP
            }

            db.collection("QUEUES").document(queue_doc_id).set(queue_data)
            created_ids.append(queue_doc_id)

        # Store success data in session for the GET request to display popup
        session['queue_success_data'] = {
            'queue_name': queue_name,
            'queue_ids': ', '.join(created_ids),
            'counter_count': len(selected_counter_ids)
        }
        
        return redirect(url_for("createqueue.create_queue_page"))

    except Exception as e:
        print("❌ Error:", e)
        flash(f"An error occurred while creating the queue(s): {str(e)}", "error")
        return redirect(url_for("createqueue.create_queue_page"))