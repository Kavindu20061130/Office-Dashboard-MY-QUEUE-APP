# test.py
# 100+ pytest tests for QueueLK application
# Each test is numbered for easy reference

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, ANY
from flask import Flask

# Import all blueprints (adjust paths as needed)
from counter_control import counter_control
from counter_qr_scanner import counter_qr_scanner
from counterdashboard import counterdashboard
from create_queue import createqueue
from createcounterstaff import createcounterstaff
from createservice import createservice
from dashboard import dashboard
from login import login
from qr_scanner import qr_scanner
from queue_management import queue_management
from reports import reports

# Create test app
app = Flask(__name__)
app.secret_key = 'test-key'
app.register_blueprint(counter_control)
app.register_blueprint(counter_qr_scanner)
app.register_blueprint(counterdashboard)
app.register_blueprint(createqueue)
app.register_blueprint(createcounterstaff)
app.register_blueprint(createservice)
app.register_blueprint(dashboard)
app.register_blueprint(login)
app.register_blueprint(qr_scanner)
app.register_blueprint(queue_management)
app.register_blueprint(reports)

@pytest.fixture
def client():
    return app.test_client()

@pytest.fixture
def mock_db():
    with patch('firebase_config.db') as m:
        m.collection.return_value.document.return_value.get.return_value.exists = False
        m.collection.return_value.stream.return_value = []
        m.collection.return_value.where.return_value.stream.return_value = []
        m.collection.return_value.add.return_value = (None, MagicMock(id='new_id'))
        yield m

def login_admin(client, office_id='off1'):
    with client.session_transaction() as s:
        s['user'] = 'admin'
        s['user_id'] = 'admin123'
        s['office_id'] = office_id
        s['role'] = 'admin'

def login_counter(client, office_id='off1'):
    with client.session_transaction() as s:
        s['user'] = 'counter'
        s['user_id'] = 'counter123'
        s['office_id'] = office_id
        s['role'] = 'counter'

# ========== LOGIN TESTS ==========
# test 1
def test_login_page_ok(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'Login' in r.data

# test 2
def test_get_offices_success(client, mock_db):
    doc1 = MagicMock(id='o1', to_dict=lambda: {'name': 'Office1'})
    doc2 = MagicMock(id='o2', to_dict=lambda: {'name': 'Office2'})
    mock_db.collection.return_value.stream.return_value = [doc1, doc2]
    r = client.get('/get-offices')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert len(data) == 2
    assert data[0]['name'] == 'Office1'

# test 3
def test_get_offices_exception(client, mock_db):
    mock_db.collection.side_effect = Exception('DB fail')
    r = client.get('/get-offices')
    assert r.status_code == 500
    assert 'error' in json.loads(r.data)

# test 4
def test_admin_login_success(client, mock_db):
    doc = MagicMock()
    doc.to_dict.return_value = {
        'email': 'a@a.com',
        'passwordHash': 'pass',
        'name': 'Admin',
        'officeId': MagicMock(id='off1')
    }
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [doc]
    r = client.post('/login', data={
        'office_id': 'off1',
        'email': 'a@a.com',
        'password': 'pass',
        'user_role': 'admin'
    }, follow_redirects=False)
    assert r.status_code == 302
    assert '/dashboard' in r.headers['Location']

# test 5
def test_admin_login_wrong_password(client, mock_db):
    doc = MagicMock()
    doc.to_dict.return_value = {
        'email': 'a@a.com',
        'passwordHash': 'pass',
        'officeId': MagicMock(id='off1')
    }
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [doc]
    r = client.post('/login', data={
        'office_id': 'off1',
        'email': 'a@a.com',
        'password': 'wrong',
        'user_role': 'admin'
    }, follow_redirects=False)
    assert b'Invalid' in r.data

# test 6
def test_counter_login_success(client, mock_db):
    doc = MagicMock()
    doc.to_dict.return_value = {
        'Username': 'counter1',
        'password': 'pass123',
        'status': 'active',
        'officeId': MagicMock(id='off1')
    }
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [doc]
    r = client.post('/login', data={
        'office_id': 'off1',
        'email': 'counter1',
        'password': 'pass123',
        'user_role': 'counter'
    }, follow_redirects=False)
    assert r.status_code == 302
    assert '/counterdashboard' in r.headers['Location']

# test 7
def test_counter_login_inactive(client, mock_db):
    doc = MagicMock()
    doc.to_dict.return_value = {
        'Username': 'c1',
        'password': 'p',
        'status': 'inactive',
        'officeId': MagicMock(id='off1')
    }
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [doc]
    r = client.post('/login', data={
        'office_id': 'off1',
        'email': 'c1',
        'password': 'p',
        'user_role': 'counter'
    })
    assert b'inactive' in r.data

# test 8
def test_login_wrong_office(client, mock_db):
    doc = MagicMock()
    doc.to_dict.return_value = {
        'email': 'a@a.com',
        'passwordHash': 'pass',
        'officeId': MagicMock(id='off2')
    }
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [doc]
    r = client.post('/login', data={
        'office_id': 'off1',
        'email': 'a@a.com',
        'password': 'pass',
        'user_role': 'admin'
    })
    assert b'not authorized' in r.data

# test 9
def test_logout(client):
    with client.session_transaction() as s:
        s['user'] = 'test'
    r = client.get('/logout', follow_redirects=False)
    assert r.status_code == 302
    assert '/' in r.headers['Location']

# test 10
def test_debug_session(client):
    with client.session_transaction() as s:
        s['foo'] = 'bar'
    r = client.get('/debug-session')
    assert r.status_code == 200
    assert 'bar' in r.data.decode()

# ========== DASHBOARD TESTS ==========
# test 11
def test_dashboard_redirect_if_not_logged_in(client):
    r = client.get('/dashboard')
    assert r.status_code == 302
    assert '/' in r.headers['Location']

# test 12
def test_dashboard_page_logged_in(client, mock_db):
    login_admin(client)
    office_doc = MagicMock()
    office_doc.exists = True
    office_doc.to_dict.return_value = {'name': 'Test Office', 'openTime': '9:00', 'closeTime': '17:00'}
    mock_db.collection.return_value.document.return_value.get.return_value = office_doc
    mock_db.collection.return_value.where.return_value.stream.return_value = []
    r = client.get('/dashboard')
    assert r.status_code == 200
    assert b'Dashboard' in r.data

# test 13
def test_dashboard_api_data(client, mock_db):
    login_admin(client)
    office_doc = MagicMock()
    office_doc.exists = True
    office_doc.to_dict.return_value = {'name': 'Office', 'openTime': '9:00', 'closeTime': '17:00'}
    mock_db.collection.return_value.document.return_value.get.return_value = office_doc
    mock_db.collection.return_value.where.return_value.stream.return_value = []
    r = client.get('/dashboard/api/data')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert 'office_name' in data

# test 14
def test_update_office_hours(client, mock_db):
    login_admin(client)
    r = client.post('/dashboard/update_hours', json={'openTime': '10:00', 'closeTime': '18:00'})
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

# test 15
def test_update_office_hours_missing_data(client):
    login_admin(client)
    r = client.post('/dashboard/update_hours', json={})
    assert r.status_code == 400

# ========== COUNTER CONTROL TESTS ==========
# test 16
def test_counter_control_page_redirect(client):
    r = client.get('/admin/counter-control')
    assert r.status_code == 302

# test 17
def test_counter_control_page_authorized(client, mock_db):
    login_admin(client)
    office_doc = MagicMock()
    office_doc.exists = True
    office_doc.to_dict.return_value = {'name': 'My Office'}
    mock_db.collection.return_value.document.return_value.get.return_value = office_doc
    r = client.get('/admin/counter-control')
    assert r.status_code == 200
    assert b'Counter Control' in r.data

# test 18
def test_api_get_counters(client, mock_db):
    login_admin(client)
    counter1 = MagicMock(id='c1')
    counter1.to_dict.return_value = {'name': 'Counter1', 'status': 'active'}
    mock_db.collection.return_value.where.return_value.stream.return_value = [counter1]
    r = client.get('/admin/api/counters')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert len(data) == 1
    assert data[0]['name'] == 'Counter1'

# test 19
def test_api_create_counter_success(client, mock_db):
    login_admin(client)
    mock_db.collection.return_value.where.return_value.stream.return_value = []  # no duplicate
    r = client.post('/admin/api/counter/create', json={'name': 'New Counter'})
    assert r.status_code == 201
    assert json.loads(r.data)['success'] is True

# test 20
def test_api_create_counter_duplicate(client, mock_db):
    login_admin(client)
    existing = MagicMock()
    mock_db.collection.return_value.where.return_value.stream.return_value = [existing]
    r = client.post('/admin/api/counter/create', json={'name': 'Duplicate'})
    assert r.status_code == 400
    assert 'already exists' in json.loads(r.data)['error']

# test 21
def test_api_get_single_counter(client, mock_db):
    login_admin(client)
    counter_doc = MagicMock()
    counter_doc.exists = True
    counter_doc.to_dict.return_value = {'name': 'C1', 'status': 'active', 'officeId': MagicMock(id='off1')}
    mock_db.collection.return_value.document.return_value.get.return_value = counter_doc
    r = client.get('/admin/api/counter/c1')
    assert r.status_code == 200
    assert json.loads(r.data)['name'] == 'C1'

# test 22
def test_api_update_counter_status(client, mock_db):
    login_admin(client)
    r = client.put('/admin/api/counter/c1/status', json={'status': 'active'})
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

# test 23
def test_api_get_counter_tokens(client, mock_db):
    login_admin(client)
    token_doc = MagicMock()
    token_doc.to_dict.return_value = {
        'bookedTime': datetime.now(timezone.utc),
        'status': 'waiting',
        'counterId': MagicMock(),
        'serviceId': MagicMock(),
        'queueId': MagicMock(),
        'tokenNumber': 'A001',
        'position': 1
    }
    mock_db.collection.return_value.where.return_value.stream.return_value = [token_doc]
    r = client.get('/admin/api/counter/c1/tokens')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert isinstance(data, list)

# test 24
def test_api_serve_token(client, mock_db):
    login_admin(client)
    r = client.post('/admin/api/token/tok1/serve')
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

# test 25
def test_api_skip_token(client, mock_db):
    login_admin(client)
    r = client.post('/admin/api/token/tok1/skip')
    assert r.status_code == 200

# test 26
def test_api_arrive_token(client, mock_db):
    login_admin(client)
    r = client.post('/admin/api/token/tok1/arrive', json={'arrivedtime': 1234567890})
    assert r.status_code == 200

# test 27
def test_api_complete_counter(client, mock_db):
    login_admin(client)
    token_doc = MagicMock()
    token_doc.to_dict.return_value = {'bookedTime': datetime.now(timezone.utc), 'status': 'waiting'}
    token_doc.reference.delete = MagicMock()
    mock_db.collection.return_value.where.return_value.stream.return_value = [token_doc]
    r = client.post('/admin/api/counter/c1/complete')
    assert r.status_code == 200
    assert 'deletedCount' in json.loads(r.data)

# test 28
def test_api_delete_counter(client, mock_db):
    login_admin(client)
    counter_doc = MagicMock()
    counter_doc.exists = True
    counter_doc.to_dict.return_value = {'name': 'ToDelete'}
    mock_db.collection.return_value.document.return_value.get.return_value = counter_doc
    r = client.delete('/admin/api/counter/c1/delete')
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

# test 29
def test_api_archive_counter(client, mock_db):
    login_admin(client)
    counter_doc = MagicMock()
    counter_doc.exists = True
    mock_db.collection.return_value.document.return_value.get.return_value = counter_doc
    r = client.post('/admin/api/counter/c1/archive')
    assert r.status_code == 200

# test 30
def test_api_restore_counter(client, mock_db):
    login_admin(client)
    counter_doc = MagicMock()
    counter_doc.exists = True
    mock_db.collection.return_value.document.return_value.get.return_value = counter_doc
    r = client.post('/admin/api/counter/c1/restore')
    assert r.status_code == 200

# ========== COUNTER DASHBOARD TESTS ==========
# test 31
def test_counter_dashboard_home_redirect(client):
    r = client.get('/counterdashboard')
    assert r.status_code == 302

# test 32
def test_counter_dashboard_home_logged_in(client, mock_db):
    login_counter(client)
    r = client.get('/counterdashboard')
    assert r.status_code == 200
    assert b'Counter Dashboard' in r.data

# test 33
def test_api_current_counter(client, mock_db):
    login_counter(client)
    session_doc = MagicMock()
    session_doc.exists = True
    session_doc.to_dict.return_value = {
        'counterId': MagicMock(id='c1'),
        'officeId': MagicMock(id='off1')
    }
    mock_db.collection.return_value.document.return_value.get.return_value = session_doc
    counter_doc = MagicMock()
    counter_doc.to_dict.return_value = {'name': 'C1', 'status': 'active'}
    mock_db.collection.return_value.document.return_value.get.return_value = counter_doc
    r = client.get('/counterdashboard/api/current-counter')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['counterName'] == 'C1'

# test 34
def test_api_get_data_tokens(client, mock_db):
    login_counter(client)
    session_doc = MagicMock()
    session_doc.exists = True
    session_doc.to_dict.return_value = {'counterId': MagicMock(id='c1'), 'officeId': MagicMock(id='off1')}
    mock_db.collection.return_value.document.return_value.get.return_value = session_doc
    counter_doc = MagicMock()
    counter_doc.to_dict.return_value = {'name': 'C1', 'status': 'active'}
    mock_db.collection.return_value.document.return_value.get.return_value = counter_doc
    queue_doc = MagicMock()
    queue_doc.reference = MagicMock()
    queue_doc.to_dict.return_value = {'name': 'Q1', 'status': 'active'}
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [queue_doc]
    token_doc = MagicMock()
    token_doc.id = 't1'
    token_doc.to_dict.return_value = {
        'bookedtime': datetime.now(timezone.utc),
        'status': 'waiting',
        'tokenNumber': 'T001',
        'position': 1
    }
    mock_db.collection.return_value.where.return_value.stream.return_value = [token_doc]
    r = client.get('/counterdashboard/api/data')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['hasCounter'] is True

# test 35
def test_counter_serve_token(client, mock_db):
    login_counter(client)
    # Mock permission check
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {'queueId': MagicMock(id='q1')}
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    queue_doc = MagicMock()
    queue_doc.exists = True
    queue_doc.to_dict.return_value = {'counterId': MagicMock(id='c1'), 'status': 'active'}
    mock_db.collection.return_value.document.return_value.get.return_value = queue_doc
    counter_doc = MagicMock()
    counter_doc.exists = True
    counter_doc.to_dict.return_value = {'status': 'active'}
    mock_db.collection.return_value.document.return_value.get.return_value = counter_doc
    r = client.post('/counterdashboard/api/serve/tok1')
    assert r.status_code == 200

# test 36
def test_counter_skip_token(client, mock_db):
    login_counter(client)
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {'queueId': MagicMock(id='q1')}
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    queue_doc = MagicMock()
    queue_doc.exists = True
    queue_doc.to_dict.return_value = {'counterId': MagicMock(id='c1'), 'status': 'active'}
    mock_db.collection.return_value.document.return_value.get.return_value = queue_doc
    counter_doc = MagicMock()
    counter_doc.exists = True
    counter_doc.to_dict.return_value = {'status': 'active'}
    mock_db.collection.return_value.document.return_value.get.return_value = counter_doc
    r = client.post('/counterdashboard/api/skip/tok1')
    assert r.status_code == 200

# test 37
def test_counter_arrive_token(client, mock_db):
    login_counter(client)
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {'queueId': MagicMock(id='q1')}
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    queue_doc = MagicMock()
    queue_doc.exists = True
    queue_doc.to_dict.return_value = {'counterId': MagicMock(id='c1'), 'status': 'active'}
    mock_db.collection.return_value.document.return_value.get.return_value = queue_doc
    counter_doc = MagicMock()
    counter_doc.exists = True
    counter_doc.to_dict.return_value = {'status': 'active'}
    mock_db.collection.return_value.document.return_value.get.return_value = counter_doc
    r = client.post('/counterdashboard/api/arrive/tok1', json={'arrivedtime': 1234567890})
    assert r.status_code == 200

# ========== COUNTER QR SCANNER TESTS ==========
# test 38
def test_scanner_page_redirect(client):
    r = client.get('/counterdashboard/scanner')
    assert r.status_code == 302

# test 39
def test_scanner_page_logged_in(client, mock_db):
    login_counter(client)
    r = client.get('/counterdashboard/scanner')
    assert r.status_code == 200
    assert b'Scanner' in r.data

# test 40
def test_token_info_api(client, mock_db):
    login_counter(client)
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {
        'queueId': MagicMock(path='queues/q1'),
        'serviceId': MagicMock(),
        'tokenNumber': 'T001',
        'status': 'waiting'
    }
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    # Mock counter queue
    session_doc = MagicMock()
    session_doc.exists = True
    session_doc.to_dict.return_value = {'counterId': MagicMock(id='c1')}
    mock_db.collection.return_value.document.return_value.get.return_value = session_doc
    queue_doc = MagicMock()
    queue_doc.reference = MagicMock()
    queue_doc.to_dict.return_value = {'counterId': MagicMock(id='c1')}
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [queue_doc]
    r = client.get('/counterdashboard/scanner/api/token-info/tok1')
    assert r.status_code == 200

# test 41
def test_arrive_token_scanner(client, mock_db):
    login_counter(client)
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {
        'queueId': MagicMock(),
        'status': 'waiting',
        'arrivedtime': None
    }
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    session_doc = MagicMock()
    session_doc.exists = True
    session_doc.to_dict.return_value = {'counterId': MagicMock(id='c1')}
    mock_db.collection.return_value.document.return_value.get.return_value = session_doc
    queue_doc = MagicMock()
    queue_doc.reference = MagicMock()
    queue_doc.to_dict.return_value = {'counterId': MagicMock(id='c1')}
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [queue_doc]
    r = client.post('/counterdashboard/scanner/api/arrive', json={'tokenId': 'tok1'})
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

# test 42
def test_serve_token_scanner(client, mock_db):
    login_counter(client)
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {
        'queueId': MagicMock(),
        'status': 'waiting',
        'arrivedtime': datetime.now(timezone.utc)
    }
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    session_doc = MagicMock()
    session_doc.exists = True
    session_doc.to_dict.return_value = {'counterId': MagicMock(id='c1')}
    mock_db.collection.return_value.document.return_value.get.return_value = session_doc
    queue_doc = MagicMock()
    queue_doc.reference = MagicMock()
    queue_doc.to_dict.return_value = {'counterId': MagicMock(id='c1')}
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [queue_doc]
    r = client.post('/counterdashboard/scanner/api/serve', json={'tokenId': 'tok1'})
    assert r.status_code == 200

# test 43
def test_waiting_tokens_scanner(client, mock_db):
    login_counter(client)
    session_doc = MagicMock()
    session_doc.exists = True
    session_doc.to_dict.return_value = {'counterId': MagicMock(id='c1')}
    mock_db.collection.return_value.document.return_value.get.return_value = session_doc
    queue_doc = MagicMock()
    queue_doc.reference = MagicMock()
    queue_doc.to_dict.return_value = {'counterId': MagicMock(id='c1')}
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [queue_doc]
    r = client.get('/counterdashboard/scanner/api/waiting-tokens')
    assert r.status_code == 200
    assert 'waiting' in json.loads(r.data)

# ========== CREATE QUEUE TESTS ==========
# test 44
def test_create_queue_page_redirect(client):
    r = client.get('/create-queue')
    assert r.status_code == 302

# test 45
def test_create_queue_page_get(client, mock_db):
    login_admin(client)
    r = client.get('/create-queue')
    assert r.status_code == 200
    assert b'Create New Queue' in r.data

# test 46
def test_create_queue_post_success(client, mock_db):
    login_admin(client)
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []  # no conflict
    data = {
        'service_option': 'existing',
        'existing_service_id': 'svc1',
        'queue_name': 'Test Queue',
        'token_letter': 'A',
        'token_start_number': '1',
        'max_capacity': '50',
        'queue_type': 'Medium',
        'counters': ['c1']
    }
    r = client.post('/create-queue', data=data, follow_redirects=False)
    assert r.status_code == 302
    assert '/create-queue' in r.headers['Location']

# test 47
def test_create_queue_with_custom_service(client, mock_db):
    login_admin(client)
    data = {
        'service_option': 'custom',
        'custom_service_name': 'New Service',
        'custom_service_charge': '100',
        'queue_name': 'Q',
        'token_letter': 'B',
        'token_start_number': '10',
        'max_capacity': '30',
        'queue_type': 'Short',
        'counters': ['c1']
    }
    r = client.post('/create-queue', data=data)
    assert r.status_code == 302

# test 48
def test_create_queue_conflicting_counter(client, mock_db):
    login_admin(client)
    # Mock active queue on counter
    active_queue = MagicMock()
    mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = [active_queue]
    data = {
        'service_option': 'existing',
        'existing_service_id': 'svc1',
        'queue_name': 'Q',
        'token_letter': 'A',
        'token_start_number': '1',
        'max_capacity': '50',
        'queue_type': 'Medium',
        'counters': ['c1']
    }
    r = client.post('/create-queue', data=data)
    assert b'already have an active queue' in r.data

# ========== CREATE COUNTER STAFF TESTS ==========
# test 49
def test_create_staff_page_redirect(client):
    r = client.get('/create-staff')
    assert r.status_code == 302

# test 50
def test_create_staff_page_get(client, mock_db):
    login_admin(client)
    r = client.get('/create-staff')
    assert r.status_code == 200

# test 51
def test_check_username_available(client, mock_db):
    login_admin(client)
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
    r = client.get('/check-username?username=newuser')
    assert r.status_code == 200
    assert json.loads(r.data)['available'] is True

# test 52
def test_check_username_taken(client, mock_db):
    login_admin(client)
    mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [MagicMock()]
    r = client.get('/check-username?username=taken')
    assert json.loads(r.data)['available'] is False

# test 53
def test_create_staff_post_success(client, mock_db):
    login_admin(client)
    data = {
        'username': 'staff123',
        'password': 'pass1234',
        'confirm_password': 'pass1234',
        'existing_counter_id': 'c1',
        'queue_id': ''
    }
    r = client.post('/create-staff', data=data)
    assert r.status_code == 200
    assert 'success' in json.loads(r.data)

# test 54
def test_create_staff_password_mismatch(client):
    login_admin(client)
    data = {'username': 'u', 'password': 'p1', 'confirm_password': 'p2'}
    r = client.post('/create-staff', data=data)
    assert r.status_code == 400
    assert 'do not match' in json.loads(r.data)['error']

# test 55
def test_update_staff(client, mock_db):
    login_admin(client)
    data = {'status': 'inactive'}
    r = client.post('/update-staff/sid', data=data)
    assert r.status_code == 200

# test 56
def test_delete_staff(client, mock_db):
    login_admin(client)
    staff_doc = MagicMock()
    staff_doc.exists = True
    staff_doc.to_dict.return_value = {'counterId': MagicMock()}
    mock_db.collection.return_value.document.return_value.get.return_value = staff_doc
    r = client.post('/delete-staff/sid')
    assert r.status_code == 200

# test 57
def test_update_counter_name(client, mock_db):
    login_admin(client)
    r = client.post('/update-counter/c1', data={'name': 'New Name'})
    assert r.status_code == 200

# ========== CREATE SERVICE TESTS ==========
# test 58
def test_create_service_success(client, mock_db):
    login_admin(client)
    r = client.post('/create-service', data={'service_name': 'Test', 'service_charge': '50'})
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

# test 59
def test_create_service_missing_name(client):
    login_admin(client)
    r = client.post('/create-service', data={'service_charge': '50'})
    assert json.loads(r.data)['success'] is False

# test 60
def test_create_service_negative_charge(client):
    login_admin(client)
    r = client.post('/create-service', data={'service_name': 'S', 'service_charge': '-10'})
    assert 'positive' in json.loads(r.data)['error']

# ========== QR SCANNER (ADMIN) TESTS ==========
# test 61
def test_admin_scanner_page_redirect(client):
    r = client.get('/admin/scanner')
    assert r.status_code == 302

# test 62
def test_admin_scanner_page_authorized(client, mock_db):
    login_admin(client)
    r = client.get('/admin/scanner')
    assert r.status_code == 200

# test 63
def test_api_token_info_admin(client, mock_db):
    login_admin(client)
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {
        'officeId': MagicMock(id='off1'),
        'serviceId': MagicMock(),
        'queueId': MagicMock(),
        'tokenNumber': 'T1'
    }
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    r = client.get('/api/qr/token-info/tok1')
    assert r.status_code == 200

# test 64
def test_api_arrive_admin(client, mock_db):
    login_admin(client)
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {
        'officeId': MagicMock(id='off1'),
        'status': 'waiting',
        'arrivedtime': None
    }
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    r = client.post('/api/qr/arrive', json={'tokenId': 'tok1'})
    assert r.status_code == 200

# test 65
def test_api_serve_admin(client, mock_db):
    login_admin(client)
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {
        'officeId': MagicMock(id='off1'),
        'status': 'waiting',
        'arrivedtime': datetime.now(timezone.utc)
    }
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    r = client.post('/api/qr/serve', json={'tokenId': 'tok1'})
    assert r.status_code == 200

# test 66
def test_api_waiting_tokens_admin(client, mock_db):
    login_admin(client)
    token_doc = MagicMock()
    token_doc.to_dict.return_value = {'status': 'waiting', 'officeId': MagicMock(id='off1')}
    mock_db.collection.return_value.where.return_value.stream.return_value = [token_doc]
    r = client.get('/api/qr/waiting-tokens')
    assert r.status_code == 200

# test 67
def test_api_recent_scans_admin(client, mock_db):
    login_admin(client)
    token_doc = MagicMock()
    token_doc.to_dict.return_value = {'status': 'served', 'servedtime': datetime.now(timezone.utc), 'officeId': MagicMock(id='off1')}
    mock_db.collection.return_value.where.return_value.stream.return_value = [token_doc]
    r = client.get('/api/qr/recent-scans')
    assert r.status_code == 200

# ========== QUEUE MANAGEMENT TESTS ==========
# test 68
def test_queue_management_page_redirect(client):
    r = client.get('/queue-management')
    assert r.status_code == 302

# test 69
def test_queue_management_page_logged_in(client, mock_db):
    login_admin(client)
    r = client.get('/queue-management')
    assert r.status_code == 200

# test 70
def test_api_get_queues_data(client, mock_db):
    login_admin(client)
    queue_doc = MagicMock()
    queue_doc.id = 'q1'
    queue_doc.reference = MagicMock()
    queue_doc.to_dict.return_value = {'name': 'Q1', 'status': 'active', 'counterId': MagicMock(id='c1')}
    mock_db.collection.return_value.where.return_value.stream.return_value = [queue_doc]
    r = client.get('/api/get-queues-data')
    assert r.status_code == 200
    assert json.loads(r.data)['success'] is True

# test 71
def test_update_queue(client, mock_db):
    login_admin(client)
    r = client.post('/update-queue', json={'id': 'q1', 'name': 'New', 'type': 'short', 'max': 100, 'status': 'active', 'counter': 'c1'})
    assert r.status_code == 200

# test 72
def test_delete_token(client, mock_db):
    login_admin(client)
    token_doc = MagicMock()
    token_doc.exists = True
    token_doc.to_dict.return_value = {'queueId': MagicMock()}
    mock_db.collection.return_value.document.return_value.get.return_value = token_doc
    r = client.post('/delete-token', json={'id': 't1'})
    assert r.status_code == 200

# test 73
def test_delete_queue_no_bookings(client, mock_db):
    login_admin(client)
    queue_doc = MagicMock()
    queue_doc.exists = True
    queue_doc.to_dict.return_value = {'bookedCount': 0}
    mock_db.collection.return_value.document.return_value.get.return_value = queue_doc
    r = client.post('/delete-queue', json={'id': 'q1', 'force': False})
    assert r.status_code == 200

# test 74
def test_delete_queue_with_bookings(client, mock_db):
    login_admin(client)
    queue_doc = MagicMock()
    queue_doc.exists = True
    queue_doc.to_dict.return_value = {'bookedCount': 5}
    mock_db.collection.return_value.document.return_value.get.return_value = queue_doc
    r = client.post('/delete-queue', json={'id': 'q1', 'force': False})
    assert json.loads(r.data)['error'] == 'HAS_BOOKINGS'

# test 75
def test_force_delete_queue(client, mock_db):
    login_admin(client)
    queue_doc = MagicMock()
    queue_doc.exists = True
    queue_doc.to_dict.return_value = {'bookedCount': 5}
    mock_db.collection.return_value.document.return_value.get.return_value = queue_doc
    r = client.post('/delete-queue', json={'id': 'q1', 'force': True})
    assert r.status_code == 200

# ========== REPORTS TESTS ==========
# test 76
def test_reports_page_redirect(client):
    r = client.get('/reports/')
    assert r.status_code == 302

# test 77
def test_reports_page_logged_in(client, mock_db):
    login_admin(client)
    r = client.get('/reports/')
    assert r.status_code == 200

# test 78
def test_api_daily_report(client, mock_db):
    login_admin(client)
    office_ref = MagicMock(id='off1')
    mock_db.collection.return_value.document.return_value = office_ref
    # Mock fetch_office_data return
    with patch('reports.fetch_office_data') as mock_fetch:
        mock_fetch.return_value = {
            'total_tokens': 10, 'served': 8, 'waiting': 2, 'active_counters': 3,
            'office_working_hours': '9-5', 'office_working_duration': '8h',
            'queue_data': [{'service_name': 'S1', 'tokens_served': 5}]
        }
        r = client.get('/reports/api/daily')
        assert r.status_code == 200
        assert json.loads(r.data)['success'] is True

# test 79
def test_api_weekly_report(client, mock_db):
    login_admin(client)
    with patch('reports.fetch_office_data') as mock_fetch:
        mock_fetch.return_value = {'served': 5, 'waiting': 2, 'active_counters': 2, 'office_working_duration': '8h', 'queue_data': []}
        r = client.get('/reports/api/weekly')
        assert r.status_code == 200

# test 80
def test_api_monthly_report(client, mock_db):
    login_admin(client)
    with patch('reports.fetch_office_data') as mock_fetch:
        mock_fetch.return_value = {'served': 5, 'waiting': 2, 'active_counters': 2, 'office_working_duration': '8h', 'queue_data': []}
        r = client.get('/reports/api/monthly')
        assert r.status_code == 200

# test 81
def test_download_daily_pdf(client, mock_db):
    login_admin(client)
    with patch('reports.fetch_office_data') as mock_fetch, patch('weasyprint.HTML') as mock_html:
        mock_fetch.return_value = {'total_tokens': 10, 'served': 8, 'waiting': 2, 'active_counters': 3, 'office_working_hours': '9-5', 'office_working_duration': '8h', 'queue_data': []}
        mock_pdf = MagicMock()
        mock_html.return_value.write_pdf.return_value = b'PDF content'
        r = client.get('/reports/download/daily')
        assert r.status_code == 200
        assert r.headers['Content-Type'] == 'application/pdf'

# test 82
def test_download_weekly_pdf(client, mock_db):
    login_admin(client)
    with patch('reports.fetch_office_data') as mock_fetch, patch('weasyprint.HTML') as mock_html:
        mock_fetch.return_value = {'served': 5, 'waiting': 2, 'active_counters': 2, 'office_working_duration': '8h', 'queue_data': []}
        mock_html.return_value.write_pdf.return_value = b'PDF'
        r = client.get('/reports/download/weekly')
        assert r.status_code == 200

# test 83
def test_download_monthly_pdf(client, mock_db):
    login_admin(client)
    with patch('reports.fetch_office_data') as mock_fetch, patch('weasyprint.HTML') as mock_html:
        mock_fetch.return_value = {'served': 5, 'waiting': 2, 'active_counters': 2, 'office_working_duration': '8h', 'queue_data': []}
        mock_html.return_value.write_pdf.return_value = b'PDF'
        r = client.get('/reports/download/monthly')
        assert r.status_code == 200

# ========== ADDITIONAL HELPER FUNCTION TESTS ==========
# test 84
def test_get_document_id_from_ref():
    from counter_control import get_document_id_from_ref
    ref = MagicMock(id='doc123')
    assert get_document_id_from_ref(ref) == 'doc123'
    assert get_document_id_from_ref('some/path/doc456') == 'doc456'

# test 85
def test_is_admin():
    from counter_control import is_admin
    with app.test_request_context():
        from flask import session
        session['role'] = 'admin'
        assert is_admin() is True
        session['role'] = 'user'
        assert is_admin() is False

# test 86
def test_get_admin_office():
    from counter_control import get_admin_office
    with app.test_request_context():
        session['office_id'] = 'off123'
        assert get_admin_office() == 'off123'

# test 87
def test_get_today_range_utc():
    from counter_control import get_today_range_utc
    start, end = get_today_range_utc()
    assert start.tzinfo is not None
    assert end.tzinfo is not None

# test 88
def test_get_next_service_id_createservice():
    from createservice import get_next_service_id
    with patch('firebase_config.db') as mock:
        doc1 = MagicMock(id='service_1')
        doc2 = MagicMock(id='service_5')
        mock.collection.return_value.stream.return_value = [doc1, doc2]
        assert get_next_service_id() == 'service_6'

# test 89
def test_get_next_queue_base():
    from create_queue import get_next_queue_base
    with patch('firebase_config.db') as mock:
        doc1 = MagicMock(id='queue_1')
        doc2 = MagicMock(id='queue_3')
        mock.collection.return_value.stream.return_value = [doc1, doc2]
        assert get_next_queue_base() == 4

# test 90
def test_get_next_counter_id():
    from createcounterstaff import get_next_counter_id
    with patch('firebase_config.db') as mock:
        mock.collection.return_value.document.return_value.get.return_value.exists = False
        with patch('google.cloud.firestore.Transaction') as mock_trans:
            # simulate transaction
            def fake_transactional(func):
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                return wrapper
            from createcounterstaff import firestore
            firestore.transactional = fake_transactional
            # simplified test
            assert get_next_counter_id().startswith('counter_')

# test 91
def test_get_next_session_id():
    from createcounterstaff import get_next_session_id
    with patch('firebase_config.db') as mock:
        mock.collection.return_value.document.return_value.get.return_value.exists = False
        assert get_next_session_id().startswith('session_')

# test 92
def test_parse_wait_time():
    from reports import parse_wait_time
    assert parse_wait_time('5 mins') == 5
    assert parse_wait_time('2 hrs') == 120
    assert parse_wait_time('1 hr 30 mins') == 90
    assert parse_wait_time(None) == 0
    assert parse_wait_time('') == 0

# test 93
def test_compute_wait_time():
    from qr_scanner import compute_wait_time
    from datetime import timedelta
    start = datetime.now(timezone.utc)
    end = start + timedelta(minutes=75)
    assert compute_wait_time(start, end) == '1 hr 15 mins'
    end2 = start + timedelta(hours=2)
    assert compute_wait_time(start, end2) == '2 hrs'

# test 94
def test_get_doc_id():
    from qr_scanner import get_doc_id
    ref = MagicMock(id='xyz')
    assert get_doc_id(ref) == 'xyz'
    assert get_doc_id('path/to/doc/abc') == 'abc'

# test 95
def test_is_counter_active():
    from counterdashboard import is_counter_active
    with patch('firebase_config.db') as mock:
        counter_doc = MagicMock()
        counter_doc.exists = True
        counter_doc.to_dict.return_value = {'status': 'active'}
        mock.collection.return_value.document.return_value.get.return_value = counter_doc
        assert is_counter_active(MagicMock(id='c1')) is True
        counter_doc.to_dict.return_value = {'status': 'inactive'}
        assert is_counter_active(MagicMock(id='c1')) is False

# test 96
def test_is_queue_active():
    from counterdashboard import is_queue_active
    with patch('firebase_config.db') as mock:
        queue_doc = MagicMock()
        queue_doc.exists = True
        queue_doc.to_dict.return_value = {'status': 'active'}
        mock.collection.return_value.document.return_value.get.return_value = queue_doc
        assert is_queue_active(MagicMock(id='q1')) is True

# test 97
def test_check_operation_permission():
    from counterdashboard import check_operation_permission
    with patch('firebase_config.db') as mock:
        token_doc = MagicMock()
        token_doc.exists = True
        token_doc.to_dict.return_value = {'queueId': MagicMock(id='q1')}
        mock.collection.return_value.document.return_value.get.return_value = token_doc
        queue_doc = MagicMock()
        queue_doc.exists = True
        queue_doc.to_dict.return_value = {'counterId': MagicMock(id='c1'), 'status': 'active'}
        mock.collection.return_value.document.return_value.get.return_value = queue_doc
        counter_doc = MagicMock()
        counter_doc.exists = True
        counter_doc.to_dict.return_value = {'status': 'active'}
        mock.collection.return_value.document.return_value.get.return_value = counter_doc
        allowed, msg = check_operation_permission('tok1')
        assert allowed is True

# test 98
def test_get_ref_path():
    from counterdashboard import get_ref_path
    ref = MagicMock(path='col/doc')
    assert get_ref_path(ref) == 'col/doc'
    assert get_ref_path('/col/doc') == 'col/doc'

# test 99
def test_get_counter_queue_ref():
    from counter_qr_scanner import get_counter_queue_ref
    with patch('firebase_config.db') as mock:
        session_doc = MagicMock()
        session_doc.exists = True
        session_doc.to_dict.return_value = {'counterId': MagicMock(id='c1')}
        mock.collection.return_value.document.return_value.get.return_value = session_doc
        queue_doc = MagicMock()
        queue_doc.reference = MagicMock()
        mock.collection.return_value.where.return_value.limit.return_value.stream.return_value = [queue_doc]
        ref, doc = get_counter_queue_ref()
        assert ref is not None

# test 100
def test_get_office_working_hours():
    from reports import get_office_working_hours
    with patch('firebase_config.db') as mock:
        office_doc = MagicMock()
        office_doc.exists = True
        office_doc.to_dict.return_value = {'openTime': '9:00', 'closeTime': '17:00'}
        mock.collection.return_value.document.return_value.get.return_value = office_doc
        assert get_office_working_hours('off1') == '9:00 - 17:00'

# test 101
def test_get_office_working_duration():
    from reports import get_office_working_duration
    with patch('firebase_config.db') as mock:
        office_doc = MagicMock()
        office_doc.exists = True
        office_doc.to_dict.return_value = {'openTime': '9:00 AM', 'closeTime': '5:00 PM'}
        mock.collection.return_value.document.return_value.get.return_value = office_doc
        dur = get_office_working_duration('off1')
        assert 'hours' in dur or 'mins' in dur

# test 102
def test_fetch_office_data():
    from reports import fetch_office_data
    with patch('firebase_config.db') as mock:
        office_ref = MagicMock(id='off1')
        token_doc = MagicMock()
        token_doc.to_dict.return_value = {
            'bookedtime': datetime.now(timezone.utc),
            'status': 'served'
        }
        mock.collection.return_value.where.return_value.stream.return_value = [token_doc]
        data = fetch_office_data(office_ref, datetime.now(timezone.utc), datetime.now(timezone.utc))
        assert 'total_tokens' in data

# test 103
def test_get_service_name():
    from reports import get_service_name
    with patch('firebase_config.db') as mock:
        service_doc = MagicMock()
        service_doc.exists = True
        service_doc.to_dict.return_value = {'name': 'Passport Renewal'}
        mock.collection.return_value.document.return_value.get.return_value = service_doc
        assert get_service_name(MagicMock(id='svc1')) == 'Passport Renewal'

# test 104
def test_get_next_analytics_id():
    from qr_scanner import get_next_analytics_id
    with patch('firebase_config.db') as mock:
        doc1 = MagicMock(id='log_1')
        doc2 = MagicMock(id='log_5')
        mock.collection.return_value.stream.return_value = [doc1, doc2]
        assert get_next_analytics_id() == 'log_6'

# test 105
def test_no_cache_decorator():
    from login import no_cache
    resp = MagicMock()
    resp.headers = {}
    resp = no_cache(resp)
    assert resp.headers['Cache-Control'] == 'no-store, no-cache, must-revalidate, max-age=0'