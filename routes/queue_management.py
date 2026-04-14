# routes/queue_management.py
from flask import Blueprint, render_template, request, jsonify, session, redirect
from firebase_config import db

queue_management = Blueprint("queue_management", __name__)

# ---------------------------
# LOAD PAGE
# ---------------------------
@queue_management.route("/queue-management")
def queue_management_page():
    if "user" not in session:
        return redirect("/")

    office_id = session.get("office_id")
    
    # Get office name from database
    office_name = "No Office Assigned"
    if office_id:
        office_ref = db.collection("OFFICES").document(office_id)
        office_doc = office_ref.get()
        if office_doc.exists:
            office_data = office_doc.to_dict()
            office_name = office_data.get("name", "Unknown Office")

    queues = get_queues_data(office_id) if office_id else []
    
    # Get counters for this office
    counters = []
    if office_id:
        office_ref = db.collection("OFFICES").document(office_id)
        counters_ref = db.collection("COUNTERS") \
            .where("officeId", "==", office_ref).stream()
        
        for c in counters_ref:
            counters.append({
                "id": c.id,
                "name": c.to_dict().get("name", c.id)
            })

    return render_template(
        "queue_management.html", 
        queues=queues, 
        counters=counters,
        office_name=office_name,
        office_id=office_id
    )


# ---------------------------
# API ENDPOINT FOR REAL-TIME DATA
# ---------------------------
@queue_management.route("/api/get-queues-data", methods=["GET"])
def get_queues_data_api():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    office_id = session.get("office_id")
    queues = get_queues_data(office_id)
    
    return jsonify({"success": True, "queues": queues})


def get_queues_data(office_id):
    """Helper function to fetch queues data"""
    queues = []
    
    if not office_id:
        return queues
    
    office_ref = db.collection("OFFICES").document(office_id)
    
    for q in db.collection("QUEUES").where("officeId", "==", office_ref).stream():
        data = q.to_dict()
        
        # Get counter name
        counter_name = ""
        counter_id = ""
        if data.get("counterId"):
            counter_id = data["counterId"].id
            counter_doc = db.collection("COUNTERS").document(counter_id).get()
            if counter_doc.exists:
                counter_name = counter_doc.to_dict().get("name", "")
        
        # Get tokens
        tokens = []
        tokens_ref = db.collection("TOKENS") \
            .where("queueId", "==", q.reference).stream()
        
        for t in tokens_ref:
            t_data = t.to_dict()
            status = str(t_data.get("status", "")).strip().lower()
            
            if status == "waiting":
                # Get service name
                service_name = ""
                service_ref = t_data.get("serviceid") or t_data.get("serviceId")
                if service_ref:
                    s_doc = service_ref.get()
                    if s_doc.exists:
                        service_name = s_doc.to_dict().get("name", "")
                
                # Format time
                booked_time = ""
                if t_data.get("bookedtime"):
                    if hasattr(t_data["bookedtime"], 'strftime'):
                        booked_time = t_data["bookedtime"].strftime("%I:%M %p")
                    else:
                        booked_time = str(t_data["bookedtime"])
                
                tokens.append({
                    "id": t.id,
                    "number": t_data.get("tokenNumber", f"T{t.id}"),
                    "service": service_name if service_name else "General Service",
                    "time": booked_time
                })
        
        queues.append({
            "id": q.id,
            "name": data.get("name", ""),
            "type": data.get("queueType", "short"),
            "max": data.get("maxCapacity", 50),
            "status": data.get("status", "inactive"),
            "booked": data.get("bookedCount", 0),
            "counter": counter_id,
            "counter_name": counter_name,
            "tokens": tokens
        })
    
    return queues


# ---------------------------
# UPDATE QUEUE
# ---------------------------
@queue_management.route("/update-queue", methods=["POST"])
def update_queue():
    try:
        data = request.json
        
        queue_id = data.get("id")
        queue_ref = db.collection("QUEUES").document(queue_id)
        
        # Handle counter reference
        counter_ref = None
        counter_id = data.get("counter")
        if counter_id and counter_id != "":
            counter_ref = db.collection("COUNTERS").document(counter_id)
        
        # Prepare update data
        update_data = {
            "name": data.get("name"),
            "queueType": data.get("type"),
            "maxCapacity": int(data.get("max")),
            "status": data.get("status")
        }
        
        if counter_ref:
            update_data["counterId"] = counter_ref
        else:
            update_data["counterId"] = None
        
        queue_ref.update(update_data)
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error updating queue: {e}")
        return jsonify({"success": False, "error": str(e)})


# ---------------------------
# DELETE TOKEN
# ---------------------------
@queue_management.route("/delete-token", methods=["POST"])
def delete_token():
    try:
        data = request.json
        token_id = data.get("id")
        
        token_ref = db.collection("TOKENS").document(token_id)
        token_doc = token_ref.get()
        
        if not token_doc.exists:
            return jsonify({"success": False, "error": "Token not found"})
        
        token_data = token_doc.to_dict()
        queue_ref = token_data.get("queueId")
        
        token_ref.delete()
        
        if queue_ref:
            q_doc = queue_ref.get()
            if q_doc.exists:
                current = q_doc.to_dict().get("bookedCount", 0)
                queue_ref.update({"bookedCount": max(0, current - 1)})
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error deleting token: {e}")
        return jsonify({"success": False, "error": str(e)})


# ---------------------------
# DELETE QUEUE
# ---------------------------
@queue_management.route("/delete-queue", methods=["POST"])
def delete_queue():
    try:
        data = request.json
        queue_id = data.get("id")
        force = data.get("force", False)
        
        q_ref = db.collection("QUEUES").document(queue_id)
        q_doc = q_ref.get()
        
        if not q_doc.exists:
            return jsonify({"success": False, "error": "Queue not found"})
        
        booked = q_doc.to_dict().get("bookedCount", 0)
        
        if booked > 0 and not force:
            return jsonify({"error": "HAS_BOOKINGS"})
        
        # Delete all tokens for this queue
        tokens = db.collection("TOKENS").where("queueId", "==", q_ref).stream()
        for t in tokens:
            t.reference.delete()
        
        # Delete the queue
        q_ref.delete()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error deleting queue: {e}")
        return jsonify({"success": False, "error": str(e)})