from flask import Blueprint, render_template, request, jsonify, session, redirect
from firebase_config import db
from datetime import datetime
import re
from google.cloud import firestore
import bcrypt   # <-- added for hashing

createcounterstaff = Blueprint("createcounterstaff", __name__)

# ---------- ID generators (unchanged) ----------
def get_next_counter_id():
    counter_ref = db.collection("METADATA").document("counter_counter")
    transaction = db.transaction()
    try:
        @firestore.transactional
        def increment(transaction):
            snapshot = counter_ref.get(transaction=transaction)
            if not snapshot.exists:
                transaction.set(counter_ref, {"value": 1})
                return "counter_1"
            current = snapshot.get("value")
            next_val = current + 1
            transaction.update(counter_ref, {"value": next_val})
            return f"counter_{next_val}"
        return increment(transaction)
    except Exception as e:
        print(f"Counter ID generation failed: {e}")
        return db.collection("COUNTERS").document().id

def get_next_session_id():
    counter_ref = db.collection("METADATA").document("session_counter")
    transaction = db.transaction()
    try:
        @firestore.transactional
        def increment(transaction):
            snapshot = counter_ref.get(transaction=transaction)
            if not snapshot.exists:
                transaction.set(counter_ref, {"value": 1})
                return "session_1"
            current = snapshot.get("value")
            next_val = current + 1
            transaction.update(counter_ref, {"value": next_val})
            return f"session_{next_val}"
        return increment(transaction)
    except Exception as e:
        print(f"Session ID generation failed: {e}")
        return db.collection("COUNTER_SESSIONS").document().id

# ---------- Helper ----------
def get_queue_for_counter(counter_ref):
    queues = db.collection("QUEUES").where("counterId", "==", counter_ref).limit(1).stream()
    for q in queues:
        return q.id
    return None

# ---------- RENDER PAGE ----------
@createcounterstaff.route("/create-staff")
def create_staff_page():
    if "user" not in session or session.get("role") != "admin":
        return redirect("/")

    office_id = session.get("office_id")
    office_ref = db.collection("OFFICES").document(office_id)

    office_doc = office_ref.get()
    office_name = office_doc.to_dict().get("name") if office_doc.exists else None

    counters = []
    for doc in db.collection("COUNTERS").where("officeId", "==", office_ref).stream():
        data = doc.to_dict()
        counters.append({"id": doc.id, "name": data.get("name"), "status": data.get("status")})

    staff = []
    for doc in db.collection("COUNTER_SESSIONS").where("officeId", "==", office_ref).stream():
        data = doc.to_dict()
        counter_ref = data.get("counterId")
        queue_id = get_queue_for_counter(counter_ref) if counter_ref else None
        staff.append({
            "id": doc.id,
            "username": data.get("Username"),
            "status": data.get("status"),
            "counterId": counter_ref.id if counter_ref else "",
            "queueId": queue_id
        })

    queues = []
    for doc in db.collection("QUEUES").where("officeId", "==", office_ref).stream():
        data = doc.to_dict()
        queues.append({"id": doc.id, "name": data.get("name"), "status": data.get("status")})

    return render_template("createcounter.html",
                           counters=counters,
                           staff=staff,
                           queues=queues,
                           office_name=office_name,
                           office_id=office_id)

# ---------- CHECK USERNAME UNIQUENESS ----------
@createcounterstaff.route("/check-username", methods=["GET"])
def check_username():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"available": True})
    existing = db.collection("COUNTER_SESSIONS").where("Username", "==", username).limit(1).stream()
    return jsonify({"available": not any(existing), "username": username})

# ---------- CREATE STAFF (with bcrypt & @counter.com) ----------
@createcounterstaff.route("/create-staff", methods=["POST"])
def create_staff():
    office_id = session.get("office_id")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")
    queue_id = request.form.get("queue_id")

    # --- Username domain validation ---
    if not username.endswith("@counter.com"):
        return jsonify({"error": "Username must end with '@counter.com'"}), 400
    local_part = username.split("@")[0]
    if len(local_part) < 8:
        return jsonify({"error": "Local part of username must be at least 8 characters"}), 400

    # --- Password validation ---
    if not password or not confirm:
        return jsonify({"error": "Password required"}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400
    if len(password) < 8 or len(password) > 18 or not re.search(r"\d", password):
        return jsonify({"error": "Password must be 8-18 characters and contain at least one digit"}), 400

    # --- Uniqueness check ---
    existing_user = db.collection("COUNTER_SESSIONS").where("Username", "==", username).limit(1).stream()
    if any(existing_user):
        return jsonify({"error": "Username already taken (global unique)"}), 400

    office_ref = db.collection("OFFICES").document(office_id)

    # --- Counter assignment ---
    existing_counter_id = request.form.get("existing_counter_id")
    new_counter_name = request.form.get("counter_name", "").strip()

    if existing_counter_id:
        counter_ref = db.collection("COUNTERS").document(existing_counter_id)
        counter_doc = counter_ref.get()
        if not counter_doc.exists or counter_doc.to_dict().get("officeId") != office_ref:
            return jsonify({"error": "Invalid counter selected"}), 400
    elif new_counter_name:
        counter_id = get_next_counter_id()
        counter_ref = db.collection("COUNTERS").document(counter_id)
        counter_ref.set({
            "name": new_counter_name,
            "officeId": office_ref,
            "status": "active"
        })
    else:
        return jsonify({"error": "Either select existing counter or provide new counter name"}), 400

    # --- Hash password ---
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    session_id = get_next_session_id()
    db.collection("COUNTER_SESSIONS").document(session_id).set({
        "Username": username,
        "password": hashed_pw,          # bcrypt hash stored here (login.py expects 'password')
        "status": "active",
        "counterId": counter_ref,
        "officeId": office_ref,
        "createdAt": datetime.now()
    })

    # --- Queue linking ---
    if queue_id and queue_id.strip():
        queue_ref = db.collection("QUEUES").document(queue_id)
        queue_snapshot = queue_ref.get()
        if queue_snapshot.exists and queue_snapshot.to_dict().get("officeId") == office_ref:
            old_queues = db.collection("QUEUES").where("counterId", "==", counter_ref).stream()
            for q in old_queues:
                q.reference.update({"counterId": None})
            queue_ref.update({"counterId": counter_ref})
        else:
            return jsonify({"error": "Invalid queue selected"}), 400

    return jsonify({"success": f"Staff '{username}' created with counter {counter_ref.id}"})

# ---------- UPDATE STAFF (with bcrypt) ----------
@createcounterstaff.route("/update-staff/<doc_id>", methods=["POST"])
def update_staff(doc_id):
    password = request.form.get("password")
    confirm = request.form.get("confirm_password")
    status = request.form.get("status")
    queue_id = request.form.get("queue_id")
    existing_counter_id = request.form.get("existing_counter_id")
    new_counter_name = request.form.get("new_counter_name", "").strip()

    update_data = {}

    # --- Password update (if provided) ---
    if password:
        if password != confirm:
            return jsonify({"error": "Passwords do not match"}), 400
        if len(password) < 8 or len(password) > 18 or not re.search(r"\d", password):
            return jsonify({"error": "Password must be 8-18 chars and contain a digit"}), 400
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        update_data["password"] = hashed_pw

    if status:
        update_data["status"] = status

    office_ref = db.collection("OFFICES").document(session.get("office_id"))
    staff_doc = db.collection("COUNTER_SESSIONS").document(doc_id).get()
    if not staff_doc.exists:
        return jsonify({"error": "Staff not found"}), 404
    old_counter_ref = staff_doc.to_dict().get("counterId")

    # --- Counter assignment ---
    if existing_counter_id:
        counter_ref = db.collection("COUNTERS").document(existing_counter_id)
        counter_doc = counter_ref.get()
        if not counter_doc.exists or counter_doc.to_dict().get("officeId") != office_ref:
            return jsonify({"error": "Invalid counter"}), 400
        update_data["counterId"] = counter_ref
        new_counter_ref = counter_ref
    elif new_counter_name:
        new_counter_id = get_next_counter_id()
        new_counter_ref = db.collection("COUNTERS").document(new_counter_id)
        new_counter_ref.set({
            "name": new_counter_name,
            "officeId": office_ref,
            "status": "active"
        })
        update_data["counterId"] = new_counter_ref
    else:
        new_counter_ref = old_counter_ref

    # --- Detach old counter from queues ---
    if old_counter_ref:
        old_queues = db.collection("QUEUES").where("counterId", "==", old_counter_ref).stream()
        for q in old_queues:
            q.reference.update({"counterId": None})

    # --- Attach new counter to selected queue ---
    if queue_id and queue_id.strip():
        queue_ref = db.collection("QUEUES").document(queue_id)
        queue_snapshot = queue_ref.get()
        if queue_snapshot.exists and queue_snapshot.to_dict().get("officeId") == office_ref:
            queue_ref.update({"counterId": new_counter_ref})
        else:
            return jsonify({"error": "Invalid queue selected"}), 400

    if update_data:
        db.collection("COUNTER_SESSIONS").document(doc_id).update(update_data)
    return jsonify({"success": "Staff updated successfully"})

# ---------- DELETE STAFF ----------
@createcounterstaff.route("/delete-staff/<doc_id>", methods=["POST"])
def delete_staff(doc_id):
    staff_doc = db.collection("COUNTER_SESSIONS").document(doc_id).get()
    if staff_doc.exists:
        counter_ref = staff_doc.to_dict().get("counterId")
        if counter_ref:
            queues = db.collection("QUEUES").where("counterId", "==", counter_ref).stream()
            for q in queues:
                q.reference.update({"counterId": None})
    db.collection("COUNTER_SESSIONS").document(doc_id).delete()
    return jsonify({"success": "Staff deleted successfully"})

# ---------- RENAME COUNTER ----------
@createcounterstaff.route("/update-counter/<counter_id>", methods=["POST"])
def update_counter(counter_id):
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "Counter name required"}), 400
    db.collection("COUNTERS").document(counter_id).update({"name": name})
    return jsonify({"success": "Counter name updated"})