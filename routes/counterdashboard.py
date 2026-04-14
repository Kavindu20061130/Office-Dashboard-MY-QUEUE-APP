from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from firebase_config import db
from google.cloud.firestore import DocumentReference, SERVER_TIMESTAMP
from datetime import datetime, timezone
import pytz

counterdashboard = Blueprint("counterdashboard", __name__)



def get_document_id_from_ref(ref):
    if isinstance(ref, DocumentReference):
        return ref.id
    if hasattr(ref, 'id'):
        return ref.id
    return str(ref).split('/')[-1]

def get_ref_path(ref):
    if isinstance(ref, DocumentReference):
        return ref.path
    return str(ref).lstrip('/')

@counterdashboard.route("/counterdashboard")
def counter_dashboard_home():
    if not session.get("user_id") or session.get("role") != "counter":
        return redirect(url_for("login.index"))
    return render_template("counterdashboard.html")

# ---------------------------
# API: current counter
# ---------------------------
@counterdashboard.route("/counterdashboard/api/current-counter")
def api_current_counter():
    if not session.get("user_id") or session.get("role") != "counter":
        return jsonify({"error": "Unauthorized"}), 401
    try:
        session_id = session["user_id"]
        session_doc = db.collection("COUNTER_SESSIONS").document(session_id).get()
        if not session_doc.exists:
            return jsonify({"error": "Session not found"}), 404
        data = session_doc.to_dict()
        counter_ref = data.get("counterId")
        office_ref = data.get("officeId")
        counter_id = get_document_id_from_ref(counter_ref)
        office_id = get_document_id_from_ref(office_ref)
        counter_doc = db.collection("COUNTERS").document(counter_id).get()
        office_doc = db.collection("OFFICES").document(office_id).get()
        queue_query = db.collection("QUEUES").where("counterId", "==", counter_ref).limit(1).stream()
        queue_doc = next(queue_query, None)
        return jsonify({
            "counterId": counter_id,
            "counterName": counter_doc.to_dict().get("name", ""),
            "queueId": queue_doc.id if queue_doc else "",
            "queueName": queue_doc.to_dict().get("name", "") if queue_doc else "",
            "officeId": office_id,
            "officeName": office_doc.to_dict().get("name", "")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------
# API: get token list (today only, sorted by position)
# ---------------------------
@counterdashboard.route("/counterdashboard/api/data")
def get_data():
    if not session.get("user_id") or session.get("role") != "counter":
        return jsonify({"error": "Unauthorized"}), 401
    
    # Disable caching
    response_headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    try:
        session_id = session["user_id"]
        session_doc = db.collection("COUNTER_SESSIONS").document(session_id).get()
        if not session_doc.exists:
            return jsonify({"error": "Session not found"}), 404
        session_data = session_doc.to_dict()
        counter_ref = session_data.get("counterId")
        office_ref = session_data.get("officeId")
        counter_id = get_document_id_from_ref(counter_ref)
        office_id = get_document_id_from_ref(office_ref)
        counter_doc = db.collection("COUNTERS").document(counter_id).get()
        office_doc = db.collection("OFFICES").document(office_id).get()
        
        # Check if queue exists for this counter
        queue_doc = next(db.collection("QUEUES").where("counterId", "==", counter_ref).limit(1).stream(), None)
        
        # If no queue assigned, return special status with message
        if not queue_doc:
            return jsonify({
                "hasQueue": False,
                "queueInactive": True,
                "officeName": office_doc.to_dict().get("name", ""),
                "counterName": counter_doc.to_dict().get("name", ""),
                "queueName": None,
                "tokens": [],
                "message": "No queue has been assigned to this counter yet. Please contact your administrator.",
                "lastUpdate": datetime.now().timestamp()
            }), 200, response_headers
        
        # Check if queue is active/inactive
        queue_data = queue_doc.to_dict()
        queue_status = queue_data.get("status", "inactive")  # Default to inactive if status not set
        queue_name = queue_data.get("name", "")
        
        # If queue status is inactive, don't display any data
        if queue_status.lower() == "inactive":
            return jsonify({
                "hasQueue": True,
                "queueInactive": True,
                "officeName": office_doc.to_dict().get("name", ""),
                "counterName": counter_doc.to_dict().get("name", ""),
                "queueName": queue_name,
                "tokens": [],
                "message": "This queue is currently inactive. Tokens cannot be served at this time.",
                "lastUpdate": datetime.now().timestamp()
            }), 200, response_headers
        
        # Queue exists and is active - proceed normally
        queue_ref = queue_doc.reference
        queue_path = get_ref_path(queue_ref)

        # Fetch tokens by queueId (both reference and string for compatibility)
        tokens_ref = []
        tokens_str = []
        try:
            tokens_ref = list(db.collection("TOKENS").where("queueId", "==", queue_ref).stream())
        except:
            pass
        for path_variant in [queue_path, '/' + queue_path]:
            try:
                tokens_str += list(db.collection("TOKENS").where("queueId", "==", path_variant).stream())
            except:
                pass
        all_docs = {}
        for doc in tokens_ref + tokens_str:
            all_docs[doc.id] = doc

        # Date filtering: today only (UTC+5:30)
        tz = pytz.timezone('Asia/Colombo')
        now = datetime.now(tz)
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=tz)
        today_end   = datetime(now.year, now.month, now.day, 23, 59, 59, 999999, tzinfo=tz)
        today_start_utc = today_start.astimezone(timezone.utc)
        today_end_utc   = today_end.astimezone(timezone.utc)

        tokens = []
        for doc in all_docs.values():
            data = doc.to_dict()
            booked = data.get("bookedtime")
            if not booked:
                continue
            if hasattr(booked, 'timestamp'):
                booked_dt = datetime.fromtimestamp(booked.timestamp(), tz=timezone.utc)
            else:
                booked_dt = booked
            if not (today_start_utc <= booked_dt <= today_end_utc):
                continue
            if data.get("status") == "served":
                continue

            # Service name
            service_ref = data.get("serviceId") or data.get("serviceid")
            service_name = ""
            if service_ref:
                service_id = get_document_id_from_ref(service_ref)
                service_doc = db.collection("SERVICES").document(service_id).get()
                if service_doc.exists:
                    service_name = service_doc.to_dict().get("name", "")

            position = data.get("position")
            if position is None:
                position = 9999

            # Convert bookedtime to seconds
            booked_ts = None
            if booked:
                if hasattr(booked, 'timestamp'):
                    booked_ts = booked.timestamp()
                else:
                    booked_ts = booked.timestamp() if hasattr(booked, 'timestamp') else None

            # Convert arrivedtime to seconds
            arrived = data.get("arrivedtime")
            arrived_ts = None
            if arrived:
                if hasattr(arrived, 'timestamp'):
                    arrived_ts = arrived.timestamp()
                else:
                    arrived_ts = arrived.timestamp() if hasattr(arrived, 'timestamp') else None

            tokens.append({
                "id": doc.id,
                "tokenNumber": data.get("tokenNumber", ""),
                "bookedtime": booked_ts,
                "arrivedtime": arrived_ts,
                "position": position,
                "serviceName": service_name,
                "status": data.get("status", "waiting")
            })

        tokens.sort(key=lambda x: x["position"])
        
        return jsonify({
            "hasQueue": True,
            "queueInactive": False,
            "officeName": office_doc.to_dict().get("name", ""),
            "counterName": counter_doc.to_dict().get("name", ""),
            "queueName": queue_name,
            "tokens": tokens,
            "lastUpdate": datetime.now().timestamp()
        }), 200, response_headers
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500, response_headers

# ---------------------------
# Actions
# ---------------------------
@counterdashboard.route("/counterdashboard/api/serve/<token_id>", methods=["POST"])
def serve_token(token_id):
    # Check if queue is active before allowing serve action
    try:
        # Get the token's queue info
        token_doc = db.collection("TOKENS").document(token_id).get()
        if not token_doc.exists:
            return jsonify({"error": "Token not found"}), 404
        
        token_data = token_doc.to_dict()
        queue_ref = token_data.get("queueId")
        
        if queue_ref:
            # Get queue document to check status
            queue_id = get_document_id_from_ref(queue_ref)
            queue_doc = db.collection("QUEUES").document(queue_id).get()
            if queue_doc.exists:
                queue_status = queue_doc.to_dict().get("status", "inactive")
                if queue_status.lower() == "inactive":
                    return jsonify({"error": "Cannot serve token: Queue is inactive"}), 403
        
        db.collection("TOKENS").document(token_id).update({
            "status": "served",
            "servedtime": SERVER_TIMESTAMP
        })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@counterdashboard.route("/counterdashboard/api/skip/<token_id>", methods=["POST"])
def skip_token(token_id):
    # Check if queue is active before allowing skip action
    try:
        # Get the token's queue info
        token_doc = db.collection("TOKENS").document(token_id).get()
        if not token_doc.exists:
            return jsonify({"error": "Token not found"}), 404
        
        token_data = token_doc.to_dict()
        queue_ref = token_data.get("queueId")
        
        if queue_ref:
            # Get queue document to check status
            queue_id = get_document_id_from_ref(queue_ref)
            queue_doc = db.collection("QUEUES").document(queue_id).get()
            if queue_doc.exists:
                queue_status = queue_doc.to_dict().get("status", "inactive")
                if queue_status.lower() == "inactive":
                    return jsonify({"error": "Cannot skip token: Queue is inactive"}), 403
        
        db.collection("TOKENS").document(token_id).update({"status": "skipped"})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@counterdashboard.route("/counterdashboard/api/arrive/<token_id>", methods=["POST"])
def set_arrived_time(token_id):
    """Set a custom arrival time (Unix timestamp in seconds)"""
    # Check if queue is active before allowing arrive action
    try:
        # Get the token's queue info
        token_doc = db.collection("TOKENS").document(token_id).get()
        if not token_doc.exists:
            return jsonify({"error": "Token not found"}), 404
        
        token_data = token_doc.to_dict()
        queue_ref = token_data.get("queueId")
        
        if queue_ref:
            # Get queue document to check status
            queue_id = get_document_id_from_ref(queue_ref)
            queue_doc = db.collection("QUEUES").document(queue_id).get()
            if queue_doc.exists:
                queue_status = queue_doc.to_dict().get("status", "inactive")
                if queue_status.lower() == "inactive":
                    return jsonify({"error": "Cannot set arrival time: Queue is inactive"}), 403
        
        data = request.get_json()
        if not data or "arrivedtime" not in data:
            return jsonify({"error": "Missing arrivedtime"}), 400
        timestamp_seconds = data["arrivedtime"]
        dt = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        db.collection("TOKENS").document(token_id).update({"arrivedtime": dt})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500