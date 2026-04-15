from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from firebase_config import db
from google.cloud.firestore import SERVER_TIMESTAMP, DocumentReference
from datetime import datetime, timezone

counter_qr_scanner = Blueprint("counter_qr_scanner", __name__)

# ---------- Helper functions (reused from counterdashboard) ----------
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

def get_counter_queue_ref():
    """Returns (queue_ref, queue_doc) for the currently logged-in counter staff."""
    session_id = session.get("user_id")
    if not session_id:
        return None, None
    session_doc = db.collection("COUNTER_SESSIONS").document(session_id).get()
    if not session_doc.exists:
        return None, None
    data = session_doc.to_dict()
    counter_ref = data.get("counterId")
    if not counter_ref:
        return None, None
    queue_docs = list(db.collection("QUEUES").where("counterId", "==", counter_ref).limit(1).stream())
    if not queue_docs:
        return None, None
    queue_doc = queue_docs[0]
    return queue_doc.reference, queue_doc

# ---------- Page route ----------
@counter_qr_scanner.route("/counterdashboard/scanner")
def scanner_page():
    if not session.get("user_id") or session.get("role") != "counter":
        return redirect(url_for("login.index"))
    return render_template("counterscanner.html")

# ---------- API: Get token info (validates token belongs to counter's queue) ----------
@counter_qr_scanner.route("/counterdashboard/scanner/api/token-info/<token_id>")
def token_info(token_id):
    if not session.get("user_id") or session.get("role") != "counter":
        return jsonify({"error": "Unauthorized"}), 401

    token_doc = db.collection("TOKENS").document(token_id).get()
    if not token_doc.exists:
        return jsonify({"error": f"Token '{token_id}' not found."}), 404

    token_data = token_doc.to_dict()
    token_queue_ref = token_data.get("queueId")
    if not token_queue_ref:
        return jsonify({"error": "Token has no associated queue."}), 400

    counter_queue_ref, queue_doc = get_counter_queue_ref()
    if not counter_queue_ref:
        return jsonify({"error": "No queue assigned to this counter."}), 400

    if get_ref_path(token_queue_ref) != get_ref_path(counter_queue_ref):
        return jsonify({"error": "This token does not belong to your counter's queue."}), 403

    # Check counter and queue active status
    counter_id = get_document_id_from_ref(queue_doc.to_dict().get("counterId"))
    counter_doc = db.collection("COUNTERS").document(counter_id).get()
    if counter_doc.exists and counter_doc.to_dict().get("status", "").lower() != "active":
        return jsonify({"error": "Counter is inactive. Cannot process tokens."}), 403

    if queue_doc.to_dict().get("status", "").lower() != "active":
        return jsonify({"error": "Queue is inactive. Cannot process tokens."}), 403

    service_name = ""
    service_ref = token_data.get("serviceId")
    if service_ref:
        s_doc = db.collection("SERVICES").document(get_document_id_from_ref(service_ref)).get()
        if s_doc.exists:
            service_name = s_doc.to_dict().get("name", "")

    arrival = token_data.get("arrivedtime")
    arrival_ts = arrival.timestamp() if hasattr(arrival, 'timestamp') else None

    return jsonify({
        "tokenId": token_id,
        "tokenNumber": token_data.get("tokenNumber", ""),
        "status": token_data.get("status", ""),
        "arrivedtime": arrival_ts,
        "serviceName": service_name,
        "queueName": queue_doc.to_dict().get("name", "")
    })

# ---------- API: Mark token as arrived ----------
@counter_qr_scanner.route("/counterdashboard/scanner/api/arrive", methods=["POST"])
def arrive_token():
    if not session.get("user_id") or session.get("role") != "counter":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    token_id = data.get("tokenId")
    if not token_id:
        return jsonify({"error": "Missing tokenId"}), 400

    token_ref = db.collection("TOKENS").document(token_id)
    token_doc = token_ref.get()
    if not token_doc.exists:
        return jsonify({"error": f"Token '{token_id}' not found."}), 404

    token_data = token_doc.to_dict()
    token_queue_ref = token_data.get("queueId")
    if not token_queue_ref:
        return jsonify({"error": "Token has no associated queue."}), 400

    counter_queue_ref, queue_doc = get_counter_queue_ref()
    if not counter_queue_ref:
        return jsonify({"error": "No queue assigned to this counter."}), 400

    if get_ref_path(token_queue_ref) != get_ref_path(counter_queue_ref):
        return jsonify({"error": "This token does not belong to your counter's queue."}), 403

    counter_id = get_document_id_from_ref(queue_doc.to_dict().get("counterId"))
    counter_doc = db.collection("COUNTERS").document(counter_id).get()
    if counter_doc.exists and counter_doc.to_dict().get("status", "").lower() != "active":
        return jsonify({"error": "Counter is inactive."}), 403
    if queue_doc.to_dict().get("status", "").lower() != "active":
        return jsonify({"error": "Queue is inactive."}), 403

    if token_data.get("status") == "served":
        return jsonify({"error": "Token already served."}), 400

    if token_data.get("arrivedtime"):
        return jsonify({"error": "Token already has arrival time. Scan again to serve."}), 400

    now_utc = datetime.now(timezone.utc)
    token_ref.update({
        "arrivedtime": now_utc,
        "arrivedTime": now_utc
    })

    service_name = ""
    service_ref = token_data.get("serviceId")
    if service_ref:
        s_doc = db.collection("SERVICES").document(get_document_id_from_ref(service_ref)).get()
        if s_doc.exists:
            service_name = s_doc.to_dict().get("name", "")

    return jsonify({
        "success": True,
        "message": "Arrival time recorded",
        "token": {
            "id": token_id,
            "tokenNumber": token_data.get("tokenNumber", ""),
            "serviceName": service_name,
            "queueName": queue_doc.to_dict().get("name", ""),
            "arrivedtime": now_utc.timestamp()
        }
    })

# ---------- API: Mark token as served ----------
@counter_qr_scanner.route("/counterdashboard/scanner/api/serve", methods=["POST"])
def serve_token():
    if not session.get("user_id") or session.get("role") != "counter":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    token_id = data.get("tokenId")
    if not token_id:
        return jsonify({"error": "Missing tokenId"}), 400

    token_ref = db.collection("TOKENS").document(token_id)
    token_doc = token_ref.get()
    if not token_doc.exists:
        return jsonify({"error": f"Token '{token_id}' not found."}), 404

    token_data = token_doc.to_dict()
    token_queue_ref = token_data.get("queueId")
    if not token_queue_ref:
        return jsonify({"error": "Token has no associated queue."}), 400

    counter_queue_ref, queue_doc = get_counter_queue_ref()
    if not counter_queue_ref:
        return jsonify({"error": "No queue assigned to this counter."}), 400

    if get_ref_path(token_queue_ref) != get_ref_path(counter_queue_ref):
        return jsonify({"error": "This token does not belong to your counter's queue."}), 403

    counter_id = get_document_id_from_ref(queue_doc.to_dict().get("counterId"))
    counter_doc = db.collection("COUNTERS").document(counter_id).get()
    if counter_doc.exists and counter_doc.to_dict().get("status", "").lower() != "active":
        return jsonify({"error": "Counter is inactive."}), 403
    if queue_doc.to_dict().get("status", "").lower() != "active":
        return jsonify({"error": "Queue is inactive."}), 403

    if token_data.get("status") == "served":
        return jsonify({"error": "Token already served."}), 400

    arrived_time = token_data.get("arrivedtime")
    if not arrived_time:
        return jsonify({"error": "Token has no arrival time. Scan once to set arrival first."}), 400

    served_time = datetime.now(timezone.utc)
    token_ref.update({
        "status": "served",
        "servedtime": SERVER_TIMESTAMP
    })

    # Compute wait time
    if hasattr(arrived_time, 'timestamp'):
        arrived_dt = arrived_time
    else:
        arrived_dt = arrived_time
    delta = abs(served_time - arrived_dt)
    total_minutes = int(delta.total_seconds() // 60)
    if total_minutes < 60:
        wait_str = f"{total_minutes} min{'s' if total_minutes != 1 else ''}"
    else:
        hours = total_minutes // 60
        mins = total_minutes % 60
        wait_str = f"{hours} hr{'s' if hours != 1 else ''} {mins} min{'s' if mins != 1 else ''}" if mins else f"{hours} hr{'s' if hours != 1 else ''}"

    # (Optional) Save to analytics – you can add that logic if needed

    return jsonify({
        "success": True,
        "message": f"Token served. Waiting time: {wait_str}",
        "waitTime": wait_str
    })

# ---------- API: Get waiting tokens for counter's queue ----------
@counter_qr_scanner.route("/counterdashboard/scanner/api/waiting-tokens")
def waiting_tokens():
    if not session.get("user_id") or session.get("role") != "counter":
        return jsonify({"error": "Unauthorized"}), 401

    counter_queue_ref, queue_doc = get_counter_queue_ref()
    if not counter_queue_ref:
        return jsonify({"waiting": []})

    tokens_ref = db.collection("TOKENS").where("queueId", "==", counter_queue_ref).stream()
    waiting = []
    for doc in tokens_ref:
        data = doc.to_dict()
        if data.get("status") == "served":
            continue
        service_name = ""
        service_ref = data.get("serviceId")
        if service_ref:
            s_doc = db.collection("SERVICES").document(get_document_id_from_ref(service_ref)).get()
            if s_doc.exists:
                service_name = s_doc.to_dict().get("name", "")
        arrival = data.get("arrivedtime")
        arrival_ts = arrival.timestamp() if hasattr(arrival, 'timestamp') else None
        waiting.append({
            "id": doc.id,
            "tokenNumber": data.get("tokenNumber", ""),
            "serviceName": service_name,
            "position": data.get("position", 9999),
            "arrivedtime": arrival_ts
        })
    waiting.sort(key=lambda x: x["position"])
    return jsonify({"waiting": waiting})