from flask import Blueprint, render_template, session, jsonify, request, redirect, url_for
from firebase_config import db
from google.cloud.firestore import SERVER_TIMESTAMP, DELETE_FIELD
from datetime import datetime, timezone
import pytz

history_bp = Blueprint('history', __name__, url_prefix='/admin')

def is_admin():
    return session.get('role') == 'admin'

def get_admin_office():
    return session.get('office_id')

def get_document_id_from_ref(ref):
    if hasattr(ref, 'id'):
        return ref.id
    return str(ref).split('/')[-1]

def format_timestamp(ts):
    if not ts:
        return None
    if hasattr(ts, 'timestamp'):
        return ts.timestamp()
    return None

# ------------------- Page Route -------------------
@history_bp.route('/history')
def history_page():
    if not is_admin():
        return redirect(url_for('login.index'))

    office_id = get_admin_office()
    office_name = None
    if office_id:
        office_doc = db.collection('OFFICES').document(office_id).get()
        if office_doc.exists:
            office_name = office_doc.to_dict().get('name')

    office_ref = db.collection('OFFICES').document(office_id)

    counters = []
    for c in db.collection('COUNTERS').where('officeId', '==', office_ref).stream():
        counters.append({'id': c.id, 'name': c.to_dict().get('name', 'Unnamed')})

    queues = []
    for q in db.collection('QUEUES').where('officeId', '==', office_ref).stream():
        queues.append({'id': q.id, 'name': q.to_dict().get('name', 'Unnamed')})

    services = []
    for s in db.collection('SERVICES').where('officeId', '==', office_ref).stream():
        services.append({'id': s.id, 'name': s.to_dict().get('name', 'Unnamed')})

    return render_template('history.html',
                           office_name=office_name,
                           office_id=office_id,
                           counters=counters,
                           queues=queues,
                           services=services)

# ------------------- API: Get filtered tokens (ALL tokens by default) -------------------
@history_bp.route('/api/history/tokens', methods=['GET'])
def get_history_tokens():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401

    office_id = get_admin_office()
    if not office_id:
        return jsonify({'error': 'No office assigned'}), 400

    office_ref = db.collection('OFFICES').document(office_id)

    queue_id     = request.args.get('queueId')
    service_id   = request.args.get('serviceId')
    counter_id   = request.args.get('counterId')
    date_from    = request.args.get('dateFrom')
    date_to      = request.args.get('dateTo')
    search_type  = request.args.get('searchType')
    search_value = request.args.get('searchValue')

    query = db.collection('TOKENS').where('officeId', '==', office_ref)

    if queue_id:
        query = query.where('queueId', '==', db.collection('QUEUES').document(queue_id))
    if service_id:
        query = query.where('serviceId', '==', db.collection('SERVICES').document(service_id))
    if counter_id:
        query = query.where('counterId', '==', db.collection('COUNTERS').document(counter_id))

    tokens_stream = query.stream()

    tz = pytz.timezone('Asia/Colombo')
    if date_from:
        d = datetime.strptime(date_from, '%Y-%m-%d')
        date_from_utc = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz).astimezone(timezone.utc)
    else:
        date_from_utc = None

    if date_to:
        d = datetime.strptime(date_to, '%Y-%m-%d')
        date_to_utc = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=tz).astimezone(timezone.utc)
    else:
        date_to_utc = None

    result = []
    for doc in tokens_stream:
        data = doc.to_dict()
        status = data.get('status', '')
        # Only include served, cancelled, skipped
        if status not in ['served', 'cancelled', 'skipped']:
            continue

        booked = data.get('bookedTime') or data.get('bookedtime')
        # Date filter: only apply if user provided a date range
        if date_from_utc or date_to_utc:
            # If no bookedTime, we cannot compare; skip this token (optional: you could keep it but we skip for safety)
            if not booked:
                continue
            if hasattr(booked, 'timestamp'):
                booked_dt = datetime.fromtimestamp(booked.timestamp(), tz=timezone.utc)
            else:
                booked_dt = booked
            if date_from_utc and booked_dt < date_from_utc:
                continue
            if date_to_utc and booked_dt > date_to_utc:
                continue

        # Search filter
        if search_value:
            if search_type == 'tokenNumber':
                if search_value.lower() not in data.get('tokenNumber', '').lower():
                    continue
            elif search_type == 'tokenId':
                if search_value.lower() != doc.id.lower():
                    continue

        queue_name = ''
        queue_ref = data.get('queueId')
        if queue_ref:
            q_doc = db.collection('QUEUES').document(get_document_id_from_ref(queue_ref)).get()
            if q_doc.exists:
                queue_name = q_doc.to_dict().get('name', '')

        service_name = ''
        service_ref = data.get('serviceId')
        if service_ref:
            s_doc = db.collection('SERVICES').document(get_document_id_from_ref(service_ref)).get()
            if s_doc.exists:
                service_name = s_doc.to_dict().get('name', '')

        counter_name = ''
        counter_ref = data.get('counterId')
        if counter_ref:
            c_doc = db.collection('COUNTERS').document(get_document_id_from_ref(counter_ref)).get()
            if c_doc.exists:
                counter_name = c_doc.to_dict().get('name', '')

        arrived = data.get('arrivedTime') or data.get('arrivedtime')
        served  = data.get('servedTime')  or data.get('servedtime')

        result.append({
            'id': doc.id,
            'tokenNumber': data.get('tokenNumber', ''),
            'status': status,
            'serviceName': service_name,
            'queueName': queue_name,
            'counterName': counter_name,
            'position': data.get('position', 0),
            'bookedTime': format_timestamp(booked),
            'arrivedTime': format_timestamp(arrived),
            'servedTime': format_timestamp(served)
        })

    # Sort by bookedTime descending; tokens without bookedTime go to the end
    result.sort(key=lambda x: x.get('bookedTime') or 0, reverse=True)
    return jsonify({'tokens': result})

# ------------------- API: Change token status -------------------
@history_bp.route('/api/history/change-status', methods=['POST'])
def change_token_status():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    token_id        = data.get('tokenId')
    new_status      = data.get('newStatus')
    new_booked_time = data.get('bookedTime')

    if not token_id or not new_status:
        return jsonify({'error': 'Missing tokenId or newStatus'}), 400

    token_ref = db.collection('TOKENS').document(token_id)
    token_doc = token_ref.get()
    if not token_doc.exists:
        return jsonify({'error': 'Token not found'}), 404

    token_data = token_doc.to_dict()
    current_status = token_data.get('status')

    if current_status not in ['served', 'cancelled', 'skipped']:
        return jsonify({'error': 'Only served, cancelled, or skipped tokens can be changed'}), 400

    if new_status == 'waiting':
        update_data = {
            'status': 'waiting',
            'arrivedTime': None,
            'servedTime':  None,
            'arrivedtime': DELETE_FIELD,
            'servedtime':  DELETE_FIELD,
        }

        if new_booked_time:
            try:
                booked_dt = datetime.fromtimestamp(new_booked_time, tz=timezone.utc)
                update_data['bookedTime'] = booked_dt
                update_data['bookedtime'] = DELETE_FIELD
            except Exception as e:
                return jsonify({'error': f'Invalid bookedTime value: {str(e)}'}), 400
        else:
            # Keep existing bookedTime, but remove lowercase legacy field
            update_data['bookedtime'] = DELETE_FIELD

        token_ref.update(update_data)
        msg = 'Token status changed to waiting.'
        msg += ' Booked time updated.' if new_booked_time else ' Booked time unchanged.'
        return jsonify({'success': True, 'message': msg})

    return jsonify({'error': 'Invalid new status. Only "waiting" is allowed.'}), 400