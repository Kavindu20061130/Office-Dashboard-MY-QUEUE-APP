from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from firebase_config import db
from google.cloud.firestore import DocumentReference

counterdashboard = Blueprint("counterdashboard", __name__)

def get_document_id_from_ref(ref):
    """Extract document ID from a Firestore Reference object or string path."""
    if isinstance(ref, DocumentReference):
        return ref.id
    if hasattr(ref, 'id'):
        return ref.id
    ref_str = str(ref)
    return ref_str.split('/')[-1]

@counterdashboard.route("/counterdashboard")
def counter_dashboard_home():
    """Render the counter dashboard page with data pre-loaded."""
    if not session.get("user_id") or session.get("role") != "counter":
        return redirect(url_for("login.index"))

    counter_session_id = session["user_id"]
    
    # Default values
    office_name = "Unknown Office"
    queue_name = "Unknown Queue"
    counter_name = "Unknown Counter"
    
    try:
        counter_session_doc = db.collection("COUNTER_SESSIONS").document(counter_session_id).get()
        if counter_session_doc.exists:
            counter_session_data = counter_session_doc.to_dict()
            counter_ref = counter_session_data.get("counterId")
            office_ref = counter_session_data.get("officeId")
            
            if counter_ref:
                counter_id = get_document_id_from_ref(counter_ref)
                counter_doc = db.collection("COUNTERS").document(counter_id).get()
                counter_name = counter_doc.to_dict().get("name", "Unknown Counter") if counter_doc.exists else "Unknown Counter"
            
            if office_ref:
                office_id = get_document_id_from_ref(office_ref)
                office_doc = db.collection("OFFICES").document(office_id).get()
                office_name = office_doc.to_dict().get("name", "Unknown Office") if office_doc.exists else "Unknown Office"
            
            if counter_ref:
                queues_ref = db.collection("QUEUES")
                query = queues_ref.where("counterId", "==", counter_ref).limit(1).stream()
                queue_doc = next(query, None)
                if queue_doc:
                    queue_name = queue_doc.to_dict().get("name", "Unknown Queue")
    except Exception as e:
        print(f"Error loading dashboard data: {e}")
    
    return render_template("counterdashboard.html", 
                         office_name=office_name,
                         queue_name=queue_name,
                         counter_name=counter_name)

@counterdashboard.route("/counterdashboard/api/current-counter")
def api_current_counter():
    """API endpoint for frontend to get current counter's details."""
    if not session.get("user_id") or session.get("role") != "counter":
        return jsonify({"error": "Unauthorized"}), 401

    counter_session_id = session["user_id"]

    try:
        counter_session_doc = db.collection("COUNTER_SESSIONS").document(counter_session_id).get()
        if not counter_session_doc.exists:
            return jsonify({"error": "Counter session not found"}), 404

        counter_session_data = counter_session_doc.to_dict()
        counter_ref = counter_session_data.get("counterId")
        office_ref = counter_session_data.get("officeId")

        if not counter_ref or not office_ref:
            return jsonify({"error": "Invalid counter session data"}), 500

        counter_id = get_document_id_from_ref(counter_ref)
        counter_doc = db.collection("COUNTERS").document(counter_id).get()
        counter_name = counter_doc.to_dict().get("name", "Unknown Counter") if counter_doc.exists else "Unknown Counter"

        office_id = get_document_id_from_ref(office_ref)
        office_doc = db.collection("OFFICES").document(office_id).get()
        office_name = office_doc.to_dict().get("name", "Unknown Office") if office_doc.exists else "Unknown Office"

        queues_ref = db.collection("QUEUES")
        query = queues_ref.where("counterId", "==", counter_ref).limit(1).stream()
        queue_doc = next(query, None)

        if not queue_doc:
            return jsonify({"error": f"No queue found for counter {counter_id}"}), 404

        queue_id = queue_doc.id
        queue_name = queue_doc.to_dict().get("name", "Unknown Queue")

        return jsonify({
            "counterId": counter_id,
            "counterName": counter_name,
            "queueId": queue_id,
            "queueName": queue_name,
            "officeId": office_id,
            "officeName": office_name
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500