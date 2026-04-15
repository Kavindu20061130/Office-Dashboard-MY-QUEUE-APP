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

def is_counter_active(counter_ref):
    """Check if counter is active"""
    try:
        counter_id = get_document_id_from_ref(counter_ref)
        counter_doc = db.collection("COUNTERS").document(counter_id).get()
        if counter_doc.exists:
            status = counter_doc.to_dict().get("status", "inactive")
            return status.lower() == "active"
        return False
    except Exception:
        return False

def is_queue_active(queue_ref):
    """Check if queue is active"""
    try:
        queue_id = get_document_id_from_ref(queue_ref)
        queue_doc = db.collection("QUEUES").document(queue_id).get()
        if queue_doc.exists:
            status = queue_doc.to_dict().get("status", "inactive")
            return status.lower() == "active"
        return False
    except Exception:
        return False

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
        
        # Get counter status
        counter_status = counter_doc.to_dict().get("status", "inactive")
        
        queue_query = db.collection("QUEUES").where("counterId", "==", counter_ref).limit(1).stream()
        queue_doc = next(queue_query, None)
        
        return jsonify({
            "counterId": counter_id,
            "counterName": counter_doc.to_dict().get("name", ""),
            "counterStatus": counter_status,
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
        
        # Check counter status first (priority over queue)
        counter_status = counter_doc.to_dict().get("status", "inactive")
        
        # If counter is inactive, return immediately
        if counter_status.lower() == "inactive":
            return jsonify({
                "hasCounter": True,
                "counterInactive": True,
                "officeName": office_doc.to_dict().get("name", ""),
                "counterName": counter_doc.to_dict().get("name", ""),
                "counterStatus": "inactive",
                "queueName": None,
                "tokens": [],
                "message": "Counter is currently inactive. Please contact your administrator.",
                "lastUpdate": datetime.now().timestamp()
            }), 200, response_headers
        
        # Check if queue exists for this counter
        queue_doc = next(db.collection("QUEUES").where("counterId", "==", counter_ref).limit(1).stream(), None)
        
        if not queue_doc:
            return jsonify({
                "hasCounter": True,
                "counterInactive": False,
                "hasQueue": False,
                "queueInactive": True,
                "officeName": office_doc.to_dict().get("name", ""),
                "counterName": counter_doc.to_dict().get("name", ""),
                "counterStatus": "active",
                "queueName": None,
                "tokens": [],
                "message": "No queue has been assigned to this counter yet. Please contact your administrator.",
                "lastUpdate": datetime.now().timestamp()
            }), 200, response_headers
        
        # Check queue status
        queue_data = queue_doc.to_dict()
        queue_status = queue_data.get("status", "inactive")
        queue_name = queue_data.get("name", "")
        
        if queue_status.lower() == "inactive":
            return jsonify({
                "hasCounter": True,
                "counterInactive": False,
                "hasQueue": True,
                "queueInactive": True,
                "officeName": office_doc.to_dict().get("name", ""),
                "counterName": counter_doc.to_dict().get("name", ""),
                "counterStatus": "active",
                "queueName": queue_name,
                "tokens": [],
                "message": "This queue is currently inactive. Tokens cannot be served at this time.",
                "lastUpdate": datetime.now().timestamp()
            }), 200, response_headers
        
        # Both counter and queue are active - proceed normally
        queue_ref = queue_doc.reference
        queue_path = get_ref_path(queue_ref)

        # Fetch tokens
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

            booked_ts = None
            if booked:
                if hasattr(booked, 'timestamp'):
                    booked_ts = booked.timestamp()
                else:
                    booked_ts = booked.timestamp() if hasattr(booked, 'timestamp') else None

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
            "hasCounter": True,
            "counterInactive": False,
            "hasQueue": True,
            "queueInactive": False,
            "officeName": office_doc.to_dict().get("name", ""),
            "counterName": counter_doc.to_dict().get("name", ""),
            "counterStatus": "active",
            "queueName": queue_name,
            "tokens": tokens,
            "lastUpdate": datetime.now().timestamp()
        }), 200, response_headers
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500, response_headers

# ---------------------------
# Helper function to check operation permissions
# ---------------------------
def check_operation_permission(token_id):
    """Check if operation is allowed (counter and queue must be active)"""
    # Get token's queue
    token_doc = db.collection("TOKENS").document(token_id).get()
    if not token_doc.exists:
        return False, "Token not found"
    
    token_data = token_doc.to_dict()
    queue_ref = token_data.get("queueId")
    
    if not queue_ref:
        return False, "No queue associated with token"
    
    # Get queue's counter
    queue_id = get_document_id_from_ref(queue_ref)
    queue_doc = db.collection("QUEUES").document(queue_id).get()
    if not queue_doc.exists:
        return False, "Queue not found"
    
    queue_data = queue_doc.to_dict()
    counter_ref = queue_data.get("counterId")
    
    if not counter_ref:
        return False, "No counter associated with queue"
    
    # Check if counter is active
    if not is_counter_active(counter_ref):
        return False, "Counter is currently inactive. Operation not allowed."
    
    # Check if queue is active
    if not is_queue_active(queue_ref):
        return False, "Queue is currently inactive. Operation not allowed."
    
    return True, "OK"

# ---------------------------
# Actions with counter status check
# ---------------------------
@counterdashboard.route("/counterdashboard/api/serve/<token_id>", methods=["POST"])
def serve_token(token_id):
    try:
        allowed, message = check_operation_permission(token_id)
        if not allowed:
            return jsonify({"error": message}), 403
        
        db.collection("TOKENS").document(token_id).update({
            "status": "served",
            "servedtime": SERVER_TIMESTAMP
        })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@counterdashboard.route("/counterdashboard/api/skip/<token_id>", methods=["POST"])
def skip_token(token_id):
    try:
        allowed, message = check_operation_permission(token_id)
        if not allowed:
            return jsonify({"error": message}), 403
        
        db.collection("TOKENS").document(token_id).update({"status": "skipped"})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@counterdashboard.route("/counterdashboard/api/arrive/<token_id>", methods=["POST"])
def set_arrived_time(token_id):
    try:
        allowed, message = check_operation_permission(token_id)
        if not allowed:
            return jsonify({"error": message}), 403
        
        data = request.get_json()
        if not data or "arrivedtime" not in data:
            return jsonify({"error": "Missing arrivedtime"}), 400
        timestamp_seconds = data["arrivedtime"]
        dt = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        db.collection("TOKENS").document(token_id).update({"arrivedtime": dt})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500