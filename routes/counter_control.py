from flask import Blueprint, render_template, session, jsonify, request, redirect, url_for
from firebase_config import db
from google.cloud.firestore import SERVER_TIMESTAMP
from datetime import datetime, timezone
import pytz

counter_control = Blueprint('counter_control', __name__, url_prefix='/admin')

# Helper functions
def get_document_id_from_ref(ref):
    if hasattr(ref, 'id'):
        return ref.id
    return str(ref).split('/')[-1]

def is_admin():
    return session.get('role') == 'admin'

def get_admin_office():
    """Return office_id from session (admin belongs to an office)"""
    return session.get('office_id')

def get_today_range_utc():
    tz = pytz.timezone('Asia/Colombo')
    now = datetime.now(tz)
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=tz)
    today_end = datetime(now.year, now.month, now.day, 23, 59, 59, 999999, tzinfo=tz)
    return today_start.astimezone(timezone.utc), today_end.astimezone(timezone.utc)

@counter_control.route('/counter-control')
def counter_control_page():
    if not is_admin():
        return redirect(url_for('login.index'))
    return render_template('countercontrol.html')

# ------------------- API: Get counters for this admin's office -------------------
@counter_control.route('/api/counters')
def api_get_counters():
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        office_id = get_admin_office()
        if not office_id:
            return jsonify({'error': 'No office assigned to admin'}), 400
        
        office_ref = db.collection('OFFICES').document(office_id)
        # Query counters where officeId == this office reference
        counters = db.collection('COUNTERS').where('officeId', '==', office_ref).stream()
        
        result = []
        for doc in counters:
            data = doc.to_dict()
            result.append({
                'id': doc.id,
                'name': data.get('name', 'Unnamed'),
                'status': data.get('status', 'inactive'),
                'officeId': office_id
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------- API: Get single counter details -------------------
@counter_control.route('/api/counter/<counter_id>')
def api_get_counter(counter_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        counter_doc = db.collection('COUNTERS').document(counter_id).get()
        if not counter_doc.exists:
            return jsonify({'error': 'Counter not found'}), 404
        data = counter_doc.to_dict()
        office_name = ''
        office_ref = data.get('officeId')
        if office_ref:
            office_id = get_document_id_from_ref(office_ref)
            office_doc = db.collection('OFFICES').document(office_id).get()
            if office_doc.exists:
                office_name = office_doc.to_dict().get('name', '')
        return jsonify({
            'id': counter_id,
            'name': data.get('name', ''),
            'status': data.get('status', 'inactive'),
            'officeName': office_name,
            'officeId': get_document_id_from_ref(office_ref) if office_ref else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------- API: Update counter status -------------------
@counter_control.route('/api/counter/<counter_id>/status', methods=['PUT'])
def api_update_counter_status(counter_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        new_status = data.get('status')
        if new_status not in ['active', 'inactive']:
            return jsonify({'error': 'Invalid status'}), 400
        db.collection('COUNTERS').document(counter_id).update({'status': new_status})
        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------- API: Get tokens for a counter (today, not served) -------------------
@counter_control.route('/api/counter/<counter_id>/tokens')
def api_get_counter_tokens(counter_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        counter_ref = db.collection('COUNTERS').document(counter_id)
        tokens_query = db.collection('TOKENS').where('counterId', '==', counter_ref).stream()
        
        start_utc, end_utc = get_today_range_utc()
        filtered = []
        for doc in tokens_query:
            data = doc.to_dict()
            booked = data.get('bookedTime') or data.get('bookedtime')
            if not booked:
                continue
            if hasattr(booked, 'timestamp'):
                booked_dt = datetime.fromtimestamp(booked.timestamp(), tz=timezone.utc)
            else:
                booked_dt = booked
            if not (start_utc <= booked_dt <= end_utc):
                continue
            if data.get('status') == 'served':
                continue
            filtered.append(doc)
        
        result = []
        for doc in filtered:
            data = doc.to_dict()
            # Service name
            service_ref = data.get('serviceId')
            service_name = ''
            if service_ref:
                service_id = get_document_id_from_ref(service_ref)
                service_doc = db.collection('SERVICES').document(service_id).get()
                if service_doc.exists:
                    service_name = service_doc.to_dict().get('name', '')
            
            # Queue name and type
            queue_ref = data.get('queueId')
            queue_name = ''
            queue_type = ''
            if queue_ref:
                queue_id = get_document_id_from_ref(queue_ref)
                queue_doc = db.collection('QUEUES').document(queue_id).get()
                if queue_doc.exists:
                    qdata = queue_doc.to_dict()
                    queue_name = qdata.get('name', '')
                    queue_type = qdata.get('type', 'regular')
            
            result.append({
                'id': doc.id,
                'tokenNumber': data.get('tokenNumber', ''),
                'status': data.get('status', 'waiting'),
                'serviceName': service_name,
                'queueName': queue_name,
                'queueType': queue_type,
                'position': data.get('position', 0),
                'bookedTime': data.get('bookedTime').timestamp() if hasattr(data.get('bookedTime'), 'timestamp') else None,
                'arrivedTime': data.get('arrivedTime').timestamp() if hasattr(data.get('arrivedTime'), 'timestamp') else None
            })
        
        result.sort(key=lambda x: x.get('position', 9999))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------- Token actions -------------------
@counter_control.route('/api/token/<token_id>/serve', methods=['POST'])
def api_serve_token(token_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        db.collection('TOKENS').document(token_id).update({
            'status': 'served',
            'servedTime': SERVER_TIMESTAMP
        })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@counter_control.route('/api/token/<token_id>/skip', methods=['POST'])
def api_skip_token(token_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        db.collection('TOKENS').document(token_id).update({'status': 'skipped'})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@counter_control.route('/api/token/<token_id>/arrive', methods=['POST'])
def api_set_arrival(token_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        arrived_ts = data.get('arrivedtime')
        if not arrived_ts:
            return jsonify({'error': 'Missing arrivedtime'}), 400
        dt = datetime.fromtimestamp(arrived_ts, tz=timezone.utc)
        db.collection('TOKENS').document(token_id).update({'arrivedTime': dt})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------- Complete counter (clear today's tokens) -------------------
@counter_control.route('/api/counter/<counter_id>/complete', methods=['POST'])
def api_complete_counter(counter_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        counter_ref = db.collection('COUNTERS').document(counter_id)
        start_utc, end_utc = get_today_range_utc()
        tokens_query = db.collection('TOKENS').where('counterId', '==', counter_ref).stream()
        deleted_count = 0
        for doc in tokens_query:
            data = doc.to_dict()
            booked = data.get('bookedTime') or data.get('bookedtime')
            if not booked:
                continue
            if hasattr(booked, 'timestamp'):
                booked_dt = datetime.fromtimestamp(booked.timestamp(), tz=timezone.utc)
            else:
                booked_dt = booked
            if not (start_utc <= booked_dt <= end_utc):
                continue
            if data.get('status') == 'served':
                continue
            doc.reference.delete()
            deleted_count += 1
        return jsonify({'success': True, 'deletedCount': deleted_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------- DELETE counter (permanently remove counter and ALL tokens) -------------------
@counter_control.route('/api/counter/<counter_id>/delete', methods=['DELETE'])
def api_delete_counter(counter_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get the counter reference
        counter_ref = db.collection('COUNTERS').document(counter_id)
        counter_doc = counter_ref.get()
        
        if not counter_doc.exists:
            return jsonify({'error': 'Counter not found'}), 404
        
        # Get counter name for logging/response
        counter_data = counter_doc.to_dict()
        counter_name = counter_data.get('name', 'Unknown')
        
        # Delete ALL tokens associated with this counter (no date filtering)
        tokens_query = db.collection('TOKENS').where('counterId', '==', counter_ref).stream()
        deleted_tokens_count = 0
        
        for token_doc in tokens_query:
            token_doc.reference.delete()
            deleted_tokens_count += 1
        
        # Delete the counter itself
        counter_ref.delete()
        
        # Optional: Log this action to an audit collection
        try:
            audit_log = {
                'action': 'delete_counter',
                'counter_id': counter_id,
                'counter_name': counter_name,
                'deleted_tokens_count': deleted_tokens_count,
                'admin_id': session.get('user_id'),
                'admin_email': session.get('email'),
                'office_id': get_admin_office(),
                'timestamp': SERVER_TIMESTAMP
            }
            db.collection('AUDIT_LOGS').add(audit_log)
        except Exception as audit_error:
            # Don't fail the main operation if audit logging fails
            print(f"Audit log error: {audit_error}")
        
        return jsonify({
            'success': True,
            'message': f'Counter "{counter_name}" and {deleted_tokens_count} associated tokens deleted successfully',
            'deletedTokensCount': deleted_tokens_count,
            'counterName': counter_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------- OPTIONAL: Archive counter (soft delete) -------------------
@counter_control.route('/api/counter/<counter_id>/archive', methods=['POST'])
def api_archive_counter(counter_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        counter_ref = db.collection('COUNTERS').document(counter_id)
        counter_doc = counter_ref.get()
        
        if not counter_doc.exists:
            return jsonify({'error': 'Counter not found'}), 404
        
        # Archive the counter (soft delete)
        counter_ref.update({
            'status': 'archived',
            'archivedAt': SERVER_TIMESTAMP,
            'archivedBy': session.get('user_id')
        })
        
        # Archive all associated tokens
        tokens_query = db.collection('TOKENS').where('counterId', '==', counter_ref).stream()
        archived_tokens_count = 0
        
        for token_doc in tokens_query:
            token_doc.reference.update({
                'archived': True,
                'archivedAt': SERVER_TIMESTAMP
            })
            archived_tokens_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Counter archived with {archived_tokens_count} tokens',
            'archivedTokensCount': archived_tokens_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ------------------- OPTIONAL: Restore archived counter -------------------
@counter_control.route('/api/counter/<counter_id>/restore', methods=['POST'])
def api_restore_counter(counter_id):
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        counter_ref = db.collection('COUNTERS').document(counter_id)
        counter_doc = counter_ref.get()
        
        if not counter_doc.exists:
            return jsonify({'error': 'Counter not found'}), 404
        
        # Restore counter
        counter_ref.update({
            'status': 'inactive',  # Restore as inactive, admin can activate if needed
            'archivedAt': None,
            'archivedBy': None
        })
        
        # Restore associated tokens (optional - you might want to keep them archived)
        tokens_query = db.collection('TOKENS').where('counterId', '==', counter_ref).stream()
        restored_tokens_count = 0
        
        for token_doc in tokens_query:
            token_doc.reference.update({
                'archived': False,
                'archivedAt': None
            })
            restored_tokens_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Counter restored with {restored_tokens_count} tokens',
            'restoredTokensCount': restored_tokens_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500