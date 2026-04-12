from flask import Blueprint, render_template, request, jsonify, session, redirect
from firebase_config import db
from datetime import datetime
import re
from google.cloud import firestore

createcounterstaff = Blueprint("createcounterstaff", __name__)

# ----- ID generators (counter_X, session_X) -----
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

# ----- Helper to get current queue for a counter -----
def get_queue_for_counter(counter_ref):
    queues = db.collection("QUEUES").where("counterId", "==", counter_ref).limit(1).stream()
    for q in queues:
        return q.id
    return None

# ----- Page: render admin form -----
@createcounterstaff.route("/create-staff")
def create_staff_page():
    if "user" not in session or session.get("role") != "admin":
        return redirect("/")

    office_id = session.get("office_id")
    office_ref = db.collection("OFFICES").document(office_id)

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

    return render_template("createcounterstaff.html",
                           counters=counters,
                           staff=staff,
                           queues=queues)

# ----- Check username uniqueness (global) -----
@createcounterstaff.route("/check-username", methods=["GET"])
def check_username():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"available": True})
    existing = db.collection("COUNTER_SESSIONS").where("Username", "==", username).limit(1).stream()
    return jsonify({"available": not any(existing), "username": username})

# ----- CREATE staff (with optional queue assignment) -----
@createcounterstaff.route("/create-staff", methods=["POST"])
def create_staff():
    office_id = session.get("office_id")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")
    queue_id = request.form.get("queue_id")  # may be empty string

    # validations
    if not username or len(username) < 8:
        return jsonify({"error": "Username must be at least 8 characters"}), 400
    if not password or not confirm:
        return jsonify({"error": "Password required"}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400
    if len(password) < 8 or len(password) > 18 or not re.search(r"\d", password):
        return jsonify({"error": "Password must be 8-18 characters and contain at least one digit"}), 400

    # unique username globally
    existing_user = db.collection("COUNTER_SESSIONS").where("Username", "==", username).limit(1).stream()
    if any(existing_user):
        return jsonify({"error": "Username already taken (global unique)"}), 400

    office_ref = db.collection("OFFICES").document(office_id)

    # Determine counter: either existing_counter_id or create new
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

    # create staff session
    session_id = get_next_session_id()
    db.collection("COUNTER_SESSIONS").document(session_id).set({
        "Username": username,
        "password": password,
        "status": "active",
        "counterId": counter_ref,
        "officeId": office_ref,
        "createdAt": datetime.now()
    })

    # assign to queue ONLY if a valid queue_id is provided (not empty)
    if queue_id and queue_id.strip():
        queue_ref = db.collection("QUEUES").document(queue_id)
        queue_snapshot = queue_ref.get()
        if queue_snapshot.exists and queue_snapshot.to_dict().get("officeId") == office_ref:
            # Remove counter from any previous queue (safety, though new staff has no previous)
            old_queues = db.collection("QUEUES").where("counterId", "==", counter_ref).stream()
            for q in old_queues:
                q.reference.update({"counterId": None})
            # Assign to new queue
            queue_ref.update({"counterId": counter_ref})
        else:
            return jsonify({"error": "Invalid queue selected"}), 400

    return jsonify({"success": f"Staff '{username}' created with counter {counter_ref.id}"})

# ----- UPDATE staff (status, password, counter assignment, optional queue assignment/unassignment) -----
@createcounterstaff.route("/update-staff/<doc_id>", methods=["POST"])
def update_staff(doc_id):
    password = request.form.get("password")
    confirm = request.form.get("confirm_password")
    status = request.form.get("status")
    queue_id = request.form.get("queue_id")  # may be empty string
    existing_counter_id = request.form.get("existing_counter_id")
    new_counter_name = request.form.get("new_counter_name", "").strip()

    update_data = {}
    if password:
        if password != confirm:
            return jsonify({"error": "Passwords do not match"}), 400
        if len(password) < 8 or len(password) > 18 or not re.search(r"\d", password):
            return jsonify({"error": "Password must be 8-18 chars and contain a digit"}), 400
        update_data["password"] = password
    if status:
        update_data["status"] = status

    office_ref = db.collection("OFFICES").document(session.get("office_id"))
    staff_doc = db.collection("COUNTER_SESSIONS").document(doc_id).get()
    if not staff_doc.exists:
        return jsonify({"error": "Staff not found"}), 404
    old_counter_ref = staff_doc.to_dict().get("counterId")

    # handle counter assignment (either existing or new)
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
        new_counter_ref = old_counter_ref   # keep old

    # --- Handle queue assignment / unassignment ---
    # First, remove counter from any queue it is currently assigned to (old assignment)
    if old_counter_ref:
        old_queues = db.collection("QUEUES").where("counterId", "==", old_counter_ref).stream()
        for q in old_queues:
            q.reference.update({"counterId": None})

    # Now, if a queue_id is provided (non-empty), assign the (possibly new) counter to that queue
    if queue_id and queue_id.strip():
        queue_ref = db.collection("QUEUES").document(queue_id)
        queue_snapshot = queue_ref.get()
        if queue_snapshot.exists and queue_snapshot.to_dict().get("officeId") == office_ref:
            queue_ref.update({"counterId": new_counter_ref})
        else:
            return jsonify({"error": "Invalid queue selected"}), 400
    # If queue_id is empty, the counter remains unassigned (already cleared above)

    if update_data:
        db.collection("COUNTER_SESSIONS").document(doc_id).update(update_data)
    return jsonify({"success": "Staff updated successfully"})

# ----- DELETE staff (also unassigns from any queue) -----
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

# ----- Rename counter (separate utility) -----
@createcounterstaff.route("/update-counter/<counter_id>", methods=["POST"])
def update_counter(counter_id):
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "Counter name required"}), 400
    db.collection("COUNTERS").document(counter_id).update({"name": name})
    return jsonify({"success": "Counter name updated"})