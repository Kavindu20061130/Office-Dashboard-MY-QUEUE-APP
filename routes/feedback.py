from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from firebase_config import db
from datetime import datetime, timedelta
from functools import wraps
import pytz
from collections import Counter, defaultdict
import time
from google.cloud.firestore import DocumentReference

feedback_bp = Blueprint("feedback", __name__, url_prefix="/feedback")

def rating_to_score(rating_str):
    mapping = {
        "Very Poor": 1,
        "Poor": 2,
        "Average": 3,
        "Good": 4,
        "Excellent": 5
    }
    # Map any legacy "Very Good" or "Satisfied" to "Good"
    if rating_str == "Very Good" or rating_str == "Satisfied":
        rating_str = "Good"
    elif rating_str == "Neutral":
        rating_str = "Average"
    return mapping.get(rating_str, 3)

def get_office_name(office_id):
    try:
        doc = db.collection("OFFICES").document(office_id).get()
        return doc.to_dict().get("name", office_id) if doc.exists else office_id
    except:
        return office_id

def resolve_reference(ref):
    if not ref:
        return {"id": None, "name": "N/A"}
    try:
        if isinstance(ref, DocumentReference):
            doc = ref.get()
            doc_id = ref.id
        else:
            doc_ref = db.document(ref)
            doc = doc_ref.get()
            doc_id = doc_ref.id
        if doc.exists:
            data = doc.to_dict()
            name = data.get("name") or data.get("title") or doc_id
            return {"id": doc_id, "name": name}
    except Exception as e:
        print(f"Resolve error: {e}")
    return {"id": str(ref), "name": "Unknown"}

@feedback_bp.route("/")
def feedback_page():
    if session.get('role') not in ['admin', 'counter']:
        return redirect(url_for('login.index'))
    office_id = session.get('office_id')
    office_name = get_office_name(office_id)
    return render_template("feedback.html",
                           office_id=office_id,
                           office_name=office_name)

@feedback_bp.route("/api/data")
def get_feedback_data():
    start_time = time.time()
    if session.get('role') not in ['admin', 'counter']:
        return jsonify({"error": "Unauthorized"}), 403

    office_id = session.get('office_id')
    if not office_id:
        return jsonify({"error": "No office assigned"}), 400

    office_ref = db.collection("OFFICES").document(office_id)

    queue_id = request.args.get("queue_id", "")
    counter_id = request.args.get("counter_id", "")
    service_id = request.args.get("service_id", "")
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")
    keyword = request.args.get("keyword", "").strip()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")

    query = db.collection("FEEDBACK").where("officeId", "==", office_ref)

    if queue_id:
        query = query.where("queue_id", "==", db.collection("QUEUES").document(queue_id))
    if counter_id:
        query = query.where("counter_id", "==", db.collection("COUNTERS").document(counter_id))
    if service_id:
        query = query.where("service_id", "==", db.collection("SERVICES").document(service_id))

    try:
        docs = list(query.stream())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    tz = pytz.timezone('Asia/Colombo')
    feedbacks = []
    user_ids = set()
    daily_ratings = defaultdict(list)

    for doc in docs:
        data = doc.to_dict()
        created_at = data.get("created_at")
        if created_at and created_at.tzinfo is None:
            created_at = tz.localize(created_at)

        if from_date and created_at:
            doc_date = created_at.date().isoformat()
            if doc_date < from_date:
                continue
        if to_date and created_at:
            doc_date = created_at.date().isoformat()
            if doc_date > to_date:
                continue

        comment = data.get("comment", "")
        rating_raw = data.get("rating", "Average")
        # Normalize to 5-level system
        if rating_raw == "Very Good" or rating_raw == "Satisfied":
            rating = "Good"
        elif rating_raw == "Neutral":
            rating = "Average"
        else:
            rating = rating_raw

        if keyword and keyword.lower() not in comment.lower() and keyword.lower() not in rating.lower():
            continue

        user_ref = data.get("user_id")
        user_id = None
        if user_ref:
            if isinstance(user_ref, DocumentReference):
                user_id = user_ref.id
            else:
                user_id = user_ref.split('/')[-1]
            user_ids.add(user_id)

        rating_score = rating_to_score(rating)
        feedbacks.append({
            "id": doc.id,
            "user_id": user_id,
            "rating": rating,
            "rating_score": rating_score,
            "comment": comment,
            "comment_preview": comment[:100] + "..." if len(comment) > 100 else comment,
            "service": resolve_reference(data.get("service_id")),
            "queue": resolve_reference(data.get("queue_id")),
            "counter": resolve_reference(data.get("counter_id")),
            "office": resolve_reference(data.get("officeId")),
            "created_at": created_at,
            "created_at_formatted": created_at.strftime("%b %d, %Y %I:%M %p") if created_at else "N/A"
        })

        if created_at:
            date_str = created_at.date().isoformat()
            daily_ratings[date_str].append(rating_score)

    # Fetch user names
    users_data = {}
    for uid in user_ids:
        try:
            user_doc = db.collection("USERS").document(uid).get()
            if user_doc.exists:
                users_data[uid] = {"name": user_doc.to_dict().get("name", uid)}
            else:
                users_data[uid] = {"name": uid}
        except:
            users_data[uid] = {"name": uid}

    for fb in feedbacks:
        uid = fb["user_id"]
        fb["user_name"] = users_data.get(uid, {}).get("name", "Guest User") if uid else "Guest User"

    # Sorting
    reverse = (sort_order == 'desc')
    if sort_by == 'user_name':
        feedbacks.sort(key=lambda x: x['user_name'].lower(), reverse=reverse)
    elif sort_by == 'rating':
        feedbacks.sort(key=lambda x: x['rating_score'], reverse=reverse)
    elif sort_by == 'comment':
        feedbacks.sort(key=lambda x: x['comment'], reverse=reverse)
    elif sort_by == 'service':
        feedbacks.sort(key=lambda x: x['service']['name'].lower(), reverse=reverse)
    elif sort_by == 'queue':
        feedbacks.sort(key=lambda x: x['queue']['name'].lower(), reverse=reverse)
    elif sort_by == 'counter':
        feedbacks.sort(key=lambda x: x['counter']['name'].lower(), reverse=reverse)
    else:
        feedbacks.sort(key=lambda x: x['created_at'] or datetime.min, reverse=reverse)

    total = len(feedbacks)
    avg_rating = sum(f["rating_score"] for f in feedbacks) / total if total else 0

    rating_dist = {
        "Very Poor": 0,
        "Poor": 0,
        "Average": 0,
        "Good": 0,
        "Excellent": 0
    }
    rating_list = []
    for fb in feedbacks:
        rating_dist[fb["rating"]] = rating_dist.get(fb["rating"], 0) + 1
        rating_list.append(fb["rating"])

    most_common = None
    if rating_list:
        counter = Counter(rating_list)
        most_common = counter.most_common(1)[0][0]

    # Line chart: last 30 days
    today = datetime.now(tz).date()
    line_labels = []
    line_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        line_labels.append(day.strftime("%b %d"))
        scores = daily_ratings.get(day_str, [])
        avg = sum(scores) / len(scores) if scores else 0
        line_data.append(round(avg, 1))

    # Pagination
    start = (page - 1) * per_page
    paginated = feedbacks[start:start + per_page]
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    elapsed = round((time.time() - start_time) * 1000)
    return jsonify({
        "success": True,
        "feedbacks": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "analytics": {
            "total_feedbacks": total,
            "average_rating": round(avg_rating, 1),
            "rating_distribution": rating_dist,
            "most_common_rating": most_common
        },
        "line_chart": {
            "labels": line_labels,
            "data": line_data
        },
        "load_time_ms": elapsed
    })

@feedback_bp.route("/api/queues")
def get_queues():
    office_id = session.get('office_id')
    if not office_id:
        return jsonify({"queues": []})
    office_ref = db.collection("OFFICES").document(office_id)
    queues = []
    for doc in db.collection("QUEUES").where("officeId", "==", office_ref).stream():
        data = doc.to_dict()
        queues.append({"id": doc.id, "name": data.get("name", doc.id)})
    return jsonify({"success": True, "queues": queues})

@feedback_bp.route("/api/counters")
def get_counters():
    office_id = session.get('office_id')
    if not office_id:
        return jsonify({"counters": []})
    office_ref = db.collection("OFFICES").document(office_id)
    counters = []
    for doc in db.collection("COUNTERS").where("officeId", "==", office_ref).stream():
        data = doc.to_dict()
        counters.append({"id": doc.id, "name": data.get("name", doc.id)})
    return jsonify({"success": True, "counters": counters})

@feedback_bp.route("/api/services")
def get_services():
    office_id = session.get('office_id')
    if not office_id:
        return jsonify({"services": []})
    office_ref = db.collection("OFFICES").document(office_id)
    services = []
    for doc in db.collection("SERVICES").where("officeId", "==", office_ref).stream():
        data = doc.to_dict()
        services.append({"id": doc.id, "name": data.get("name", doc.id)})
    return jsonify({"success": True, "services": services})