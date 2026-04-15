from flask import Blueprint, render_template, session, request, jsonify
from firebase_config import db
from google.cloud.firestore import SERVER_TIMESTAMP
from datetime import datetime, timezone
import pytz

qr_scanner = Blueprint("qr_scanner", __name__)

def get_doc_id(ref):
    if hasattr(ref, 'id'):
        return ref.id
    return str(ref).split('/')[-1]

def get_admin_office_id():
    if session.get("office_id"):
        return session["office_id"]
    user_id = session.get("user_id")
    if user_id:
        user_doc = db.collection("USERS").document(user_id).get()
        if user_doc.exists:
            office_ref = user_doc.to_dict().get("officeId")
            return get_doc_id(office_ref)
    return None

def get_next_analytics_id():
    docs = db.collection("QUEUE_ANALYTICS").stream()
    max_num = 0
    for doc in docs:
        doc_id_lower = doc.id.lower()
        if doc_id_lower.startswith("log_"):
            try:
                num = int(doc.id.split("_")[1])
                if num > max_num:
                    max_num = num
            except:
                pass
    return f"log_{max_num + 1}"

def compute_wait_time(arrived_dt, served_dt):
    delta = abs(served_dt - arrived_dt)
    total_minutes = int(delta.total_seconds() // 60)
    if total_minutes < 60:
        return f"{total_minutes} min{'s' if total_minutes != 1 else ''}"
    hours = total_minutes // 60
    mins = total_minutes % 60
    if mins == 0:
        return f"{hours} hr{'s' if hours != 1 else ''}"
    return f"{hours} hr{'s' if hours != 1 else ''} {mins} min{'s' if mins != 1 else ''}"

def get_arrival_time(token_data):
    if token_data.get("arrivedtime"):
        return token_data["arrivedtime"]
    if token_data.get("arrivedTime"):
        return token_data["arrivedTime"]
    return None

def set_arrival_time(token_ref, now_utc):
    token_ref.update({
        "arrivedtime": now_utc,
        "arrivedTime": now_utc
    })

# ---------------------------
# Page route
# ---------------------------
@qr_scanner.route("/admin/scanner")
def scanner_page():
    if not session.get("user_id") or session.get("role") not in ["admin", "operator"]:
        return "Unauthorized", 401
    return render_template("scanner.html")

# ---------------------------
# Get token info (no modification)
# ---------------------------
@qr_scanner.route("/api/qr/token-info/<token_id>", methods=["GET"])
def token_info(token_id):
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    token_ref = db.collection("TOKENS").document(token_id)
    token_doc = token_ref.get()
    if not token_doc.exists:
        return jsonify({"error": f"Token '{token_id}' does not exist in TOKENS collection."}), 404

    token_data = token_doc.to_dict()
    office_ref = token_data.get("officeId")
    token_office_id = office_ref.id if hasattr(office_ref, 'id') else get_doc_id(office_ref)
    admin_office_id = get_admin_office_id()
    if token_office_id != admin_office_id:
        # CHANGED ERROR MESSAGE
        return jsonify({"error": "failed due to QR is Wrong"}), 403

    arrival_ts = get_arrival_time(token_data)
    service_name = ""
    service_ref = token_data.get("serviceId")
    if service_ref:
        service_doc = db.collection("SERVICES").document(get_doc_id(service_ref)).get()
        if service_doc.exists:
            service_name = service_doc.to_dict().get("name", "")

    queue_name = ""
    queue_type = ""
    queue_ref = token_data.get("queueId")
    if queue_ref:
        queue_doc = db.collection("QUEUES").document(get_doc_id(queue_ref)).get()
        if queue_doc.exists:
            qdata = queue_doc.to_dict()
            queue_name = qdata.get("name", "")
            queue_type = qdata.get("queueType", "")

    return jsonify({
        "tokenId": token_id,
        "tokenNumber": token_data.get("tokenNumber", ""),
        "status": token_data.get("status", ""),
        "arrivedtime": arrival_ts.timestamp() if arrival_ts else None,
        "serviceName": service_name,
        "queueName": queue_name,
        "queueType": queue_type
    })

# ---------------------------
# Mark arrived (sets both field names)
# ---------------------------
@qr_scanner.route("/api/qr/arrive", methods=["POST"])
def qr_arrive():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    token_id = data.get("tokenId")
    if not token_id:
        return jsonify({"error": "Missing tokenId"}), 400

    token_ref = db.collection("TOKENS").document(token_id)
    token_doc = token_ref.get()
    if not token_doc.exists:
        return jsonify({"error": f"Token '{token_id}' not found in TOKENS collection."}), 404

    token_data = token_doc.to_dict()
    office_ref = token_data.get("officeId")
    token_office_id = office_ref.id if hasattr(office_ref, 'id') else get_doc_id(office_ref)
    admin_office_id = get_admin_office_id()
    if token_office_id != admin_office_id:
        # CHANGED ERROR MESSAGE
        return jsonify({"error": "failed due to QR is Wrong"}), 403

    if token_data.get("status") == "served":
        return jsonify({"error": f"Token '{token_id}' was already served."}), 400

    if get_arrival_time(token_data) is not None:
        return jsonify({"error": f"Token '{token_id}' already has arrival time. Please scan again to complete service."}), 400

    now_utc = datetime.now(timezone.utc)
    set_arrival_time(token_ref, now_utc)
    token_data["arrivedtime"] = now_utc
    token_data["arrivedTime"] = now_utc

    service_name = ""
    service_ref = token_data.get("serviceId")
    if service_ref:
        service_doc = db.collection("SERVICES").document(get_doc_id(service_ref)).get()
        if service_doc.exists:
            service_name = service_doc.to_dict().get("name", "")

    queue_name = ""
    queue_type = ""
    queue_ref = token_data.get("queueId")
    if queue_ref:
        queue_doc = db.collection("QUEUES").document(get_doc_id(queue_ref)).get()
        if queue_doc.exists:
            qdata = queue_doc.to_dict()
            queue_name = qdata.get("name", "")
            queue_type = qdata.get("queueType", "")

    return jsonify({
        "success": True,
        "message": "Arrival time recorded",
        "token": {
            "id": token_id,
            "tokenNumber": token_data.get("tokenNumber", ""),
            "serviceName": service_name,
            "queueName": queue_name,
            "queueType": queue_type,
            "status": token_data.get("status", "waiting"),
            "arrivedtime": now_utc.timestamp()
        }
    })

# ---------------------------
# Mark served + calculate wait time
# ---------------------------
@qr_scanner.route("/api/qr/serve", methods=["POST"])
def qr_serve():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    token_id = data.get("tokenId")
    if not token_id:
        return jsonify({"error": "Missing tokenId"}), 400

    token_ref = db.collection("TOKENS").document(token_id)
    token_doc = token_ref.get()
    if not token_doc.exists:
        return jsonify({"error": f"Token '{token_id}' not found in TOKENS collection."}), 404

    token_data = token_doc.to_dict()
    office_ref = token_data.get("officeId")
    token_office_id = office_ref.id if hasattr(office_ref, 'id') else get_doc_id(office_ref)
    admin_office_id = get_admin_office_id()
    if token_office_id != admin_office_id:
        # CHANGED ERROR MESSAGE
        return jsonify({"error": "failed due to QR is Wrong"}), 403

    if token_data.get("status") == "served":
        return jsonify({"error": f"Token '{token_id}' was already served."}), 400

    arrived_time = get_arrival_time(token_data)
    if not arrived_time:
        return jsonify({"error": f"Token '{token_id}' has no arrival time. Please scan once to set arrival first."}), 400

    served_time = datetime.now(timezone.utc)
    token_ref.update({
        "status": "served",
        "servedtime": SERVER_TIMESTAMP
    })

    if hasattr(arrived_time, 'timestamp'):
        arrived_dt = arrived_time
    else:
        arrived_dt = arrived_time
    wait_str = compute_wait_time(arrived_dt, served_time)

    analytics_id = get_next_analytics_id()
    queue_ref = token_data.get("queueId")
    service_ref = token_data.get("serviceId")
    service_name = ""
    if service_ref:
        service_doc = db.collection("SERVICES").document(get_doc_id(service_ref)).get()
        if service_doc.exists:
            service_name = service_doc.to_dict().get("name", "")

    analytics_data = {
        "avgWaitTime": wait_str,
        "queueId": queue_ref,
        "serviceId": service_ref,
        "serviceName": service_name,
        "tokenId": token_ref,
        "timestamp": SERVER_TIMESTAMP
    }
    db.collection("QUEUE_ANALYTICS").document(analytics_id).set(analytics_data)

    return jsonify({
        "success": True,
        "message": f"Token served. Waiting time: {wait_str}",
        "waitTime": wait_str
    })

# ---------------------------
# Waiting tokens – using DocumentReference
# ---------------------------
@qr_scanner.route("/api/qr/waiting-tokens", methods=["GET"])
def waiting_tokens():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    admin_office_id = get_admin_office_id()
    if not admin_office_id:
        return jsonify({"error": "No office assigned"}), 400

    office_ref = db.collection("OFFICES").document(admin_office_id)
    tokens_ref = db.collection("TOKENS").where("officeId", "==", office_ref).stream()

    waiting = []
    for doc in tokens_ref:
        data = doc.to_dict()
        if data.get("status") == "served":
            continue
        service_name = ""
        service_ref = data.get("serviceId")
        if service_ref:
            if hasattr(service_ref, 'id'):
                s_doc = service_ref.get()
            else:
                s_doc = db.collection("SERVICES").document(get_doc_id(service_ref)).get()
            if s_doc.exists:
                service_name = s_doc.to_dict().get("name", "")
        arrival_ts = get_arrival_time(data)
        waiting.append({
            "id": doc.id,
            "tokenNumber": data.get("tokenNumber", ""),
            "serviceName": service_name,
            "status": data.get("status", "waiting"),
            "position": data.get("position", 0),
            "arrivedtime": arrival_ts.timestamp() if arrival_ts else None
        })
    waiting.sort(key=lambda x: x["position"])
    return jsonify({"waiting": waiting})

# ---------------------------
# Recent scans – using DocumentReference
# ---------------------------
@qr_scanner.route("/api/qr/recent-scans", methods=["GET"])
def recent_scans():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

    admin_office_id = get_admin_office_id()
    if not admin_office_id:
        return jsonify({"error": "No office assigned"}), 400

    office_ref = db.collection("OFFICES").document(admin_office_id)
    tokens_ref = db.collection("TOKENS").where("officeId", "==", office_ref).stream()

    served = []
    for doc in tokens_ref:
        data = doc.to_dict()
        if data.get("status") != "served":
            continue
        served_time = data.get("servedtime")
        if served_time is None:
            continue
        service_name = ""
        service_ref = data.get("serviceId")
        if service_ref:
            if hasattr(service_ref, 'id'):
                s_doc = service_ref.get()
            else:
                s_doc = db.collection("SERVICES").document(get_doc_id(service_ref)).get()
            if s_doc.exists:
                service_name = s_doc.to_dict().get("name", "")
        served.append({
            "id": doc.id,
            "tokenNumber": data.get("tokenNumber", ""),
            "serviceName": service_name,
            "servedtime": served_time.timestamp(),
            "_raw_dt": served_time
        })

    served.sort(key=lambda x: x["_raw_dt"], reverse=True)
    recent = served[:10]
    for r in recent:
        del r["_raw_dt"]
    return jsonify({"recent": recent})