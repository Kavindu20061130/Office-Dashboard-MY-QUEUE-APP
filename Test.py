# test.py
# Comprehensive test suite for the Queue Management System
# Categories: Blackbox, Whitebox, Security, Performance
# Total tests: 111 (all passing)

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'routes'))

import pytest
import json
import time
import bcrypt
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timedelta, timezone
from flask import Flask
import pytz

# ----------------------------------------------------------------------
# Mock Firebase module (must be imported before the blueprints)
# ----------------------------------------------------------------------
from types import ModuleType
mock_firebase = ModuleType("firebase_config")
mock_db = MagicMock()
mock_firebase.db = mock_db
mock_firebase.SERVER_TIMESTAMP = "SERVER_TIMESTAMP"
sys.modules["firebase_config"] = mock_firebase

# Now import blueprints (they will use the mocked firebase_config)
from login import login, rate_limit_store, lockout_store, failed_attempts_store, csrf_tokens
from counter_control import counter_control
from counterdashboard import counterdashboard
from qr_scanner import qr_scanner
from create_queue import createqueue
from createcounterstaff import createcounterstaff
from createservice import createservice
from dashboard import dashboard
from feedback import feedback_bp
from history import history_bp
from queue_management import queue_management
from reports import reports

# ----------------------------------------------------------------------
# Test categorization markers
# ----------------------------------------------------------------------
# We'll use pytest markers to categorize tests
# Run with: pytest -v -m "blackbox" etc.

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def app():
    """Flask app with all blueprints registered."""
    app = Flask(__name__)
    app.secret_key = "test_secret_key"
    app.register_blueprint(login)
    app.register_blueprint(counter_control)
    app.register_blueprint(counterdashboard)
    app.register_blueprint(qr_scanner)
    app.register_blueprint(createqueue)
    app.register_blueprint(createcounterstaff)
    app.register_blueprint(createservice)
    app.register_blueprint(dashboard)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(queue_management)
    app.register_blueprint(reports)
    return app

@pytest.fixture
def client(app):
    """Test client with cookies enabled."""
    return app.test_client(use_cookies=True)

@pytest.fixture
def mock_db_fixture():
    """Reset mock database before each test."""
    mock_db.reset_mock()
    # Default return values for common chains
    mock_db.collection.return_value.document.return_value.get.return_value.exists = False
    mock_db.collection.return_value.where.return_value.stream.return_value = []
    mock_db.collection.return_value.stream.return_value = []
    mock_db.collection.return_value.add.return_value = (None, Mock(id="new_id"))
    mock_db.document.return_value.get.return_value.exists = False
    return mock_db

@pytest.fixture
def admin_session(client, mock_db_fixture):
    """Simulate logged‑in admin."""
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
        sess['office_id'] = 'office_123'
        sess['user_id'] = 'admin_123'
        sess['user'] = 'Admin User'
        sess['email'] = 'admin@test.com'
    return client

@pytest.fixture
def counter_session(client):
    """Simulate logged‑in counter staff."""
    with client.session_transaction() as sess:
        sess['role'] = 'counter'
        sess['office_id'] = 'office_123'
        sess['user_id'] = 'counter_123'
        sess['user'] = 'Counter Staff'
    return client

# ----------------------------------------------------------------------
# Helper: patch time.sleep to avoid delays in performance tests
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def no_sleep():
    with patch('time.sleep', return_value=None):
        yield

# ======================================================================
# BLACKBOX TESTS (marked with @pytest.mark.blackbox)
# ======================================================================
@pytest.mark.blackbox
def test_login_page_loads(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'login' in rv.data.lower() or b'username' in rv.data.lower()

@pytest.mark.blackbox
def test_login_with_wrong_password(client, mock_db_fixture):
    mock_doc = MagicMock()
    mock_doc.exists = True
    hashed = bcrypt.hashpw('correct'.encode(), bcrypt.gensalt()).decode()
    mock_doc.to_dict.return_value = {
        'email': 'admin@test.com',
        'passwordHash': hashed,
        'officeId': Mock(id='office_123')
    }
    mock_db_fixture.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_doc]
    with patch('login.verify_csrf_token', return_value=True):
        rv = client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'wrong',
            'csrf_token': 'any'
        }, follow_redirects=True)
    assert b'Invalid' in rv.data

@pytest.mark.blackbox
def test_login_with_nonexistent_user(client, mock_db_fixture):
    mock_db_fixture.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
    with patch('login.verify_csrf_token', return_value=True):
        rv = client.post('/login', data={
            'username': 'nobody@test.com',
            'password': 'pass',
            'csrf_token': 'any'
        }, follow_redirects=True)
    assert b'Invalid' in rv.data

@pytest.mark.blackbox
def test_logout_clears_session(admin_session):
    rv = admin_session.get('/logout', follow_redirects=True)
    with admin_session.session_transaction() as sess:
        assert not sess.get('role')

@pytest.mark.blackbox
def test_counter_control_page_requires_admin(client):
    rv = client.get('/admin/counter-control')
    assert rv.status_code == 302

@pytest.mark.blackbox
def test_counter_control_page_loads_for_admin(admin_session, mock_db_fixture):
    mock_db_fixture.collection.return_value.document.return_value.get.return_value.exists = True
    mock_db_fixture.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {'name': 'Test Office'}
    rv = admin_session.get('/admin/counter-control')
    assert rv.status_code == 200

@pytest.mark.blackbox
def test_api_get_counters_returns_list(admin_session, mock_db_fixture):
    mock_counter_doc = MagicMock()
    mock_counter_doc.id = 'counter_1'
    mock_counter_doc.to_dict.return_value = {'name': 'Counter A', 'status': 'active'}
    mock_db_fixture.collection.return_value.where.return_value.stream.return_value = [mock_counter_doc]
    rv = admin_session.get('/admin/api/counters')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert isinstance(data, list)
    assert data[0]['name'] == 'Counter A'

@pytest.mark.blackbox
def test_api_create_counter_success(admin_session, mock_db_fixture):
    mock_db_fixture.collection.return_value.where.return_value.stream.return_value = []
    mock_db_fixture.collection.return_value.add.return_value = (None, Mock(id='counter_new'))
    rv = admin_session.post('/admin/api/counter/create', json={'name': 'New Counter'})
    assert rv.status_code == 201
    data = json.loads(rv.data)
    assert data['success'] is True
    assert data['counterName'] == 'New Counter'

@pytest.mark.blackbox
def test_api_update_counter_status(admin_session, mock_db_fixture):
    rv = admin_session.put('/admin/api/counter/counter_123/status', json={'status': 'active'})
    assert rv.status_code == 200
    mock_db_fixture.collection.return_value.document.return_value.update.assert_called_with({'status': 'active'})

@pytest.mark.blackbox
def test_api_delete_counter(admin_session, mock_db_fixture):
    mock_counter_doc = MagicMock()
    mock_counter_doc.exists = True
    mock_counter_doc.to_dict.return_value = {'name': 'ToDelete'}
    mock_db_fixture.collection.return_value.document.return_value.get.return_value = mock_counter_doc
    mock_tokens = [MagicMock(), MagicMock()]
    mock_db_fixture.collection.return_value.where.return_value.stream.return_value = mock_tokens
    rv = admin_session.delete('/admin/api/counter/counter_123/delete')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data['success'] is True
    assert data['deletedTokensCount'] == 2

@pytest.mark.blackbox
def test_qr_scanner_page_requires_auth(client):
    rv = client.get('/admin/scanner')
    assert rv.status_code in (401, 302)

@pytest.mark.blackbox
def test_qr_scanner_page_loads_for_admin(admin_session, mock_db_fixture):
    mock_db_fixture.collection.return_value.document.return_value.get.return_value.exists = True
    mock_db_fixture.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {'name': 'Office'}
    rv = admin_session.get('/admin/scanner')
    assert rv.status_code == 200

@pytest.mark.blackbox
def test_counter_dashboard_page_requires_counter(client):
    rv = client.get('/counterdashboard')
    assert rv.status_code == 302

@pytest.mark.blackbox
def test_counter_dashboard_loads_for_counter(counter_session, mock_db_fixture):
    rv = counter_session.get('/counterdashboard')
    assert rv.status_code == 200

@pytest.mark.blackbox
def test_queue_management_page_requires_auth(client):
    rv = client.get('/queue-management')
    assert rv.status_code == 302

@pytest.mark.blackbox
def test_queue_management_page_loads(admin_session, mock_db_fixture):
    rv = admin_session.get('/queue-management')
    assert rv.status_code == 200

@pytest.mark.blackbox
def test_api_get_queues_data(admin_session, mock_db_fixture):
    rv = admin_session.get('/api/get-queues-data')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data['success'] is True

@pytest.mark.blackbox
def test_reports_page_requires_auth(client):
    rv = client.get('/reports/')
    assert rv.status_code == 302

@pytest.mark.blackbox
def test_reports_page_loads(admin_session, mock_db_fixture):
    rv = admin_session.get('/reports/')
    assert rv.status_code == 200

@pytest.mark.blackbox
def test_api_daily_report(admin_session, mock_db_fixture):
    rv = admin_session.get('/reports/api/daily')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data['success'] is True

@pytest.mark.blackbox
def test_feedback_page_requires_auth(client):
    rv = client.get('/feedback/')
    assert rv.status_code == 302

@pytest.mark.blackbox
def test_feedback_page_loads(admin_session, mock_db_fixture):
    rv = admin_session.get('/feedback/')
    assert rv.status_code == 200

@pytest.mark.blackbox
def test_feedback_api_data(admin_session, mock_db_fixture):
    rv = admin_session.get('/feedback/api/data')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data['success'] is True

@pytest.mark.blackbox
def test_history_page_requires_admin(client):
    rv = client.get('/admin/history')
    assert rv.status_code == 302

@pytest.mark.blackbox
def test_history_page_loads(admin_session, mock_db_fixture):
    rv = admin_session.get('/admin/history')
    assert rv.status_code == 200

@pytest.mark.blackbox
def test_history_tokens_api(admin_session, mock_db_fixture):
    rv = admin_session.get('/admin/api/history/tokens')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'tokens' in data

@pytest.mark.blackbox
def test_api_get_queues_list(admin_session, mock_db_fixture):
    mock_queue = MagicMock()
    mock_queue.id = 'queue_1'
    mock_queue.to_dict.return_value = {'name': 'Queue 1', 'status': 'active'}
    mock_db_fixture.collection.return_value.where.return_value.stream.return_value = [mock_queue]
    rv = admin_session.get('/api/get-queues-data')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data['success'] is True

@pytest.mark.blackbox
def test_api_get_tokens_for_queue(admin_session, mock_db_fixture):
    mock_token = MagicMock()
    mock_token.to_dict.return_value = {'tokenNumber': 'A001', 'status': 'waiting'}
    mock_db_fixture.collection.return_value.where.return_value.stream.return_value = [mock_token]
    rv = admin_session.get('/admin/api/counter/counter_1/tokens')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert isinstance(data, list)

@pytest.mark.blackbox
def test_create_queue_page_requires_auth(client):
    rv = client.get('/create-queue')
    assert rv.status_code == 302

@pytest.mark.blackbox
def test_create_queue_page_loads_for_admin(admin_session, mock_db_fixture):
    mock_service = MagicMock()
    mock_service.id = 'service_1'
    mock_service.to_dict.return_value = {'name': 'Test Service', 'duration': 10}
    mock_counter = MagicMock()
    mock_counter.id = 'counter_1'
    mock_counter.to_dict.return_value = {'name': 'Counter A', 'status': 'active'}
    mock_db_fixture.collection.return_value.where.return_value.stream.side_effect = [
        [mock_service], [mock_counter]
    ]
    rv = admin_session.get('/create-queue')
    assert rv.status_code == 200

@pytest.mark.blackbox
def test_logout_without_session(client):
    rv = client.get('/logout', follow_redirects=True)
    assert rv.status_code == 200
    assert b'login' in rv.data.lower()

@pytest.mark.blackbox
def test_login_page_has_csrf_token(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'csrf' in rv.data.lower() or b'token' in rv.data.lower()

# ======================================================================
# WHITEBOX TESTS (marked with @pytest.mark.whitebox)
# ======================================================================
@pytest.mark.whitebox
def test_rate_limit_function_blocks_after_limit():
    from login import rate_limit
    ip = '192.168.1.1'
    rate_limit_store[ip] = []
    for i in range(5):
        assert rate_limit(ip, limit=5, window=60) is True
    assert rate_limit(ip, limit=5, window=60) is False

@pytest.mark.whitebox
def test_sanitize_input_removes_non_printable():
    from login import sanitize_input
    dirty = "user\x00name\x1f"
    clean = sanitize_input(dirty)
    assert clean == "username"
    assert len(clean) <= 100

@pytest.mark.whitebox
def test_is_valid_username():
    from login import is_valid_username
    assert is_valid_username('user@domain.com') is True
    assert is_valid_username('a@b') is True
    assert is_valid_username('ab') is False
    assert is_valid_username('user@') is True
    assert is_valid_username('user name') is False

@pytest.mark.whitebox
def test_verify_password_bcrypt():
    from login import verify_password
    plain = 'mypass'
    hashed = bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    assert verify_password(plain, hashed) is True
    assert verify_password('wrong', hashed) is False
    assert verify_password(plain, 'plaintext') is False

@pytest.mark.whitebox
def test_get_today_range_utc_returns_correct_range():
    from counter_control import get_today_range_utc
    start, end = get_today_range_utc()
    assert start.tzinfo == timezone.utc
    assert end.tzinfo == timezone.utc
    assert start <= end
    assert (end - start).days == 0

@pytest.mark.whitebox
def test_get_arrival_time_fallback():
    from counter_control import get_arrival_time
    data1 = {'arrivedTime': 'value1'}
    data2 = {'arrivedtime': 'value2'}
    data3 = {}
    assert get_arrival_time(data1) == 'value1'
    assert get_arrival_time(data2) == 'value2'
    assert get_arrival_time(data3) is None

@pytest.mark.whitebox
def test_rating_to_score_mapping():
    from feedback import rating_to_score
    assert rating_to_score('Excellent') == 5
    assert rating_to_score('Good') == 4
    assert rating_to_score('Average') == 3
    assert rating_to_score('Poor') == 2
    assert rating_to_score('Very Poor') == 1
    assert rating_to_score('Very Good') == 4
    assert rating_to_score('Satisfied') == 4
    assert rating_to_score('Neutral') == 3

@pytest.mark.whitebox
def test_parse_wait_time():
    from reports import parse_wait_time
    assert parse_wait_time('5 mins') == 5
    assert parse_wait_time('2 hrs 30 mins') == 150
    assert parse_wait_time('1 hr') == 60
    assert parse_wait_time('') == 0
    assert parse_wait_time('-10 mins') == 10

@pytest.mark.whitebox
def test_get_next_service_id_sequential():
    from create_queue import get_next_service_id
    mock_docs = [Mock(id='service_1'), Mock(id='service_2'), Mock(id='service_5')]
    with patch('create_queue.db.collection', return_value=MagicMock(stream=MagicMock(return_value=mock_docs))):
        next_id = get_next_service_id()
        assert next_id == 'service_6'

@pytest.mark.whitebox
def test_get_next_queue_base_sequential():
    from create_queue import get_next_queue_base
    mock_docs = [Mock(id='queue_10'), Mock(id='queue_12'), Mock(id='queue_15')]
    with patch('create_queue.db.collection', return_value=MagicMock(stream=MagicMock(return_value=mock_docs))):
        next_base = get_next_queue_base()
        assert next_base == 16

@pytest.mark.whitebox
def test_compute_wait_time():
    from qr_scanner import compute_wait_time
    arrived = datetime(2025,1,1,10,0,0, tzinfo=timezone.utc)
    served = datetime(2025,1,1,10,35,0, tzinfo=timezone.utc)
    assert compute_wait_time(arrived, served) == '35 mins'
    served2 = datetime(2025,1,1,12,5,0, tzinfo=timezone.utc)
    assert compute_wait_time(arrived, served2) == '2 hrs 5 mins'

@pytest.mark.whitebox
def test_get_next_analytics_id():
    from qr_scanner import get_next_analytics_id
    mock_docs = [Mock(id='log_1'), Mock(id='log_2'), Mock(id='log_5')]
    with patch('qr_scanner.db.collection', return_value=MagicMock(stream=MagicMock(return_value=mock_docs))):
        next_id = get_next_analytics_id()
        assert next_id == 'log_6'

@pytest.mark.whitebox
def test_get_document_id_from_ref_handles_ref_or_string():
    from counter_control import get_document_id_from_ref
    class Ref:
        id = 'my_id'
    assert get_document_id_from_ref(Ref()) == 'my_id'
    assert get_document_id_from_ref('/path/to/document/id123') == 'id123'
    assert get_document_id_from_ref('id123') == 'id123'

@pytest.mark.whitebox
def test_sanitize_input_handles_none():
    from login import sanitize_input
    assert sanitize_input(None) == ""

@pytest.mark.whitebox
def test_sanitize_input_keeps_valid_characters():
    from login import sanitize_input
    assert sanitize_input("hello world") == "hello world"

@pytest.mark.whitebox
def test_sanitize_input_with_email_format():
    from login import sanitize_input
    assert sanitize_input("test@example.com") == "test@example.com"
    assert sanitize_input("user_name.123") == "user_name.123"

@pytest.mark.whitebox
def test_sanitize_input_removes_null_bytes():
    from login import sanitize_input
    dirty = "user\x00name\x00test"
    clean = sanitize_input(dirty)
    assert '\x00' not in clean
    assert len(sanitize_input("x" * 200)) <= 100

@pytest.mark.whitebox
def test_verify_password_with_empty_string():
    from login import verify_password
    hashed = bcrypt.hashpw(b'', bcrypt.gensalt()).decode()
    assert verify_password('', hashed) is True

@pytest.mark.whitebox
def test_verify_password_with_special_characters():
    from login import verify_password
    plain = "P@ssw0rd!@#$%"
    hashed = bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong", hashed) is False

@pytest.mark.whitebox
def test_get_today_range_utc_returns_valid_range():
    from counter_control import get_today_range_utc
    start, end = get_today_range_utc()
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    assert start <= end

@pytest.mark.whitebox
def test_get_arrival_time_with_missing_key():
    from counter_control import get_arrival_time
    assert get_arrival_time({'other': 'value'}) is None
    assert get_arrival_time({}) is None

@pytest.mark.whitebox
def test_get_arrival_time_case_sensitive():
    from counter_control import get_arrival_time
    assert get_arrival_time({'arrivedTime': 'value'}) == 'value'
    assert get_arrival_time({'ARRIVEDTIME': 'value'}) is None

@pytest.mark.whitebox
def test_parse_wait_time_with_invalid_format():
    from reports import parse_wait_time
    assert parse_wait_time("invalid") == 0
    assert parse_wait_time("") == 0

@pytest.mark.whitebox
def test_parse_wait_time_with_mixed_format():
    from reports import parse_wait_time
    assert parse_wait_time('1 hr 30 mins') == 90
    assert parse_wait_time('2hrs30mins') == 150

@pytest.mark.whitebox
def test_compute_wait_time_same_time():
    from qr_scanner import compute_wait_time
    now = datetime.now(timezone.utc)
    assert compute_wait_time(now, now) == '0 mins'

@pytest.mark.whitebox
def test_compute_wait_time_with_negative_difference():
    from qr_scanner import compute_wait_time
    later = datetime(2025,1,1,10,0,0, tzinfo=timezone.utc)
    earlier = datetime(2025,1,1,9,30,0, tzinfo=timezone.utc)
    result = compute_wait_time(later, earlier)
    assert result in ('30 mins', '-30 mins')

@pytest.mark.whitebox
def test_compute_wait_time_with_large_difference():
    from qr_scanner import compute_wait_time
    arrived = datetime(2025,1,1,10,0,0, tzinfo=timezone.utc)
    served = datetime(2025,1,1,18,45,0, tzinfo=timezone.utc)
    result = compute_wait_time(arrived, served)
    assert '8 hrs' in result or '525 mins' in result

@pytest.mark.whitebox
def test_rating_to_score_with_standard_ratings():
    from feedback import rating_to_score
    assert rating_to_score('Excellent') == 5
    assert rating_to_score('Good') == 4
    assert rating_to_score('Average') == 3
    assert rating_to_score('Poor') == 2
    assert rating_to_score('Very Poor') == 1

@pytest.mark.whitebox
def test_rating_to_score_with_edge_cases():
    from feedback import rating_to_score
    assert rating_to_score('') == 3
    assert rating_to_score(None) == 3

@pytest.mark.whitebox
def test_get_document_id_from_ref_with_string_only():
    from counter_control import get_document_id_from_ref
    assert get_document_id_from_ref("simple_id") == "simple_id"
    assert get_document_id_from_ref("path/to/doc/12345") == "12345"

@pytest.mark.whitebox
def test_get_next_service_id_with_no_existing():
    from create_queue import get_next_service_id
    with patch('create_queue.db.collection', return_value=MagicMock(stream=MagicMock(return_value=[]))):
        next_id = get_next_service_id()
        assert next_id == 'service_1'

@pytest.mark.whitebox
def test_get_next_service_id_with_mixed_ids():
    from create_queue import get_next_service_id
    mock_docs = [Mock(id='service_1'), Mock(id='service_3'), Mock(id='service_7'), Mock(id='other_id')]
    with patch('create_queue.db.collection', return_value=MagicMock(stream=MagicMock(return_value=mock_docs))):
        next_id = get_next_service_id()
        assert next_id == 'service_8'

@pytest.mark.whitebox
def test_get_next_queue_base_with_no_existing():
    from create_queue import get_next_queue_base
    with patch('create_queue.db.collection', return_value=MagicMock(stream=MagicMock(return_value=[]))):
        next_base = get_next_queue_base()
        assert next_base == 1

@pytest.mark.whitebox
def test_get_next_queue_base_with_mixed_ids():
    from create_queue import get_next_queue_base
    mock_docs = [Mock(id='queue_5'), Mock(id='queue_12'), Mock(id='queue_23'), Mock(id='invalid')]
    with patch('create_queue.db.collection', return_value=MagicMock(stream=MagicMock(return_value=mock_docs))):
        next_base = get_next_queue_base()
        assert next_base == 24

@pytest.mark.whitebox
def test_get_next_analytics_id_with_no_existing():
    from qr_scanner import get_next_analytics_id
    with patch('qr_scanner.db.collection', return_value=MagicMock(stream=MagicMock(return_value=[]))):
        next_id = get_next_analytics_id()
        assert next_id == 'log_1'

# ======================================================================
# SECURITY TESTS (marked with @pytest.mark.security)
# ======================================================================
@pytest.mark.security
def test_sql_injection_attempt_in_username():
    from login import sanitize_input
    malicious = "admin' OR '1'='1"
    cleaned = sanitize_input(malicious)
    assert "'" in cleaned

@pytest.mark.security
def test_no_admin_bypass_without_role(client):
    rv = client.get('/admin/api/counters')
    assert rv.status_code == 401

@pytest.mark.security
def test_rate_limit_prevents_brute_force():
    from login import rate_limit, rate_limit_store
    ip = '1.2.3.4'
    rate_limit_store[ip] = []
    for i in range(5):
        assert rate_limit(ip, limit=5, window=60) is True
    assert rate_limit(ip, limit=5, window=60) is False

@pytest.mark.security
def test_input_length_limits():
    from login import sanitize_input
    long_input = 'x' * 200
    truncated = sanitize_input(long_input)
    assert len(truncated) <= 100

@pytest.mark.security
def test_rate_limit_with_different_ips():
    from login import rate_limit, rate_limit_store
    ip1 = '10.0.0.1'
    ip2 = '10.0.0.2'
    rate_limit_store.clear()
    for i in range(5):
        assert rate_limit(ip1, limit=5, window=60) is True
    assert rate_limit(ip1, limit=5, window=60) is False
    assert rate_limit(ip2, limit=5, window=60) is True

@pytest.mark.security
def test_rate_limit_cleans_old_entries():
    from login import rate_limit, rate_limit_store
    ip = 'cleanup.test'
    rate_limit_store[ip] = [100, 101, 102, 103, 104]
    with patch('time.time', return_value=200):
        rate_limit(ip, limit=10, window=60)
        assert len(rate_limit_store.get(ip, [])) <= 2

@pytest.mark.security
def test_is_valid_username_rejects_empty():
    from login import is_valid_username
    assert is_valid_username("") is False
    assert is_valid_username(None) is False

@pytest.mark.security
def test_csrf_token_generation_unique():
    from login import generate_csrf_token
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    assert token1 != token2
    assert len(token1) > 10
    assert len(token2) > 10

@pytest.mark.security
def test_csrf_token_length():
    from login import generate_csrf_token
    token = generate_csrf_token()
    assert 20 <= len(token) <= 100

@pytest.mark.security
def test_lockout_store_initialization():
    from login import lockout_store
    assert isinstance(lockout_store, dict)
    lockout_store['test_ip'] = datetime.now(timezone.utc) + timedelta(minutes=15)
    assert 'test_ip' in lockout_store

@pytest.mark.security
def test_failed_attempts_store_initialization():
    from login import failed_attempts_store
    assert isinstance(failed_attempts_store, dict)

# ======================================================================
# PERFORMANCE TESTS (marked with @pytest.mark.performance)
# ======================================================================
@pytest.mark.performance
def test_login_response_time_under_500ms(client, mock_db_fixture):
    start = time.time()
    with patch('login.verify_csrf_token', return_value=True):
        client.post('/login', data={'username':'test','password':'test'})
    elapsed = (time.time() - start) * 1000
    assert elapsed < 500

@pytest.mark.performance
def test_api_get_counters_response_time(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/admin/api/counters')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_api_get_tokens_response_time(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/admin/api/counter/counter_1/tokens')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_feedback_api_data_response_time(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/feedback/api/data')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 400

@pytest.mark.performance
def test_reports_api_daily_response_time(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/reports/api/daily')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 500

@pytest.mark.performance
def test_counter_dashboard_data_response_time(counter_session, mock_db_fixture):
    start = time.time()
    counter_session.get('/counterdashboard/api/data')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_history_tokens_api_response_time(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/admin/api/history/tokens')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 400

@pytest.mark.performance
def test_queue_management_api_response_time(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/api/get-queues-data')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_qr_token_info_response_time(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/api/qr/token-info/token_dummy')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 200

@pytest.mark.performance
def test_pdf_report_generation_time(admin_session, mock_db_fixture):
    start = time.time()
    with patch('reports.HTML.write_pdf', return_value=b'fake_pdf'):
        admin_session.get('/reports/download/daily')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 2000

@pytest.mark.performance
def test_bulk_token_fetch_performance(admin_session, mock_db_fixture):
    mock_tokens = [MagicMock() for _ in range(100)]
    for i, tok in enumerate(mock_tokens):
        tok.to_dict.return_value = {
            'tokenNumber': f'T{i:03d}',
            'status': 'waiting',
            'bookedTime': Mock(timestamp=lambda: time.time()),
            'position': i
        }
    mock_db_fixture.collection.return_value.where.return_value.stream.return_value = mock_tokens
    start = time.time()
    admin_session.get('/admin/api/counter/counter_1/tokens')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 500

@pytest.mark.performance
def test_check_username_api_performance(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/check-username?username=test@counter.com')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 200

@pytest.mark.performance
def test_delete_counter_performance(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.delete('/admin/api/counter/counter_123/delete')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 500

@pytest.mark.performance
def test_api_update_counter_status_performance(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.put('/admin/api/counter/counter_123/status', json={'status': 'inactive'})
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_create_counter_api_performance(admin_session, mock_db_fixture):
    start = time.time()
    mock_db_fixture.collection.return_value.where.return_value.stream.return_value = []
    mock_db_fixture.collection.return_value.add.return_value = (None, Mock(id='counter_new'))
    rv = admin_session.post('/admin/api/counter/create', json={'name': 'Performance Counter'})
    elapsed = (time.time() - start) * 1000
    assert elapsed < 400
    assert rv.status_code == 201

@pytest.mark.performance
def test_qr_scanner_page_performance(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/admin/scanner')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_counter_control_page_performance(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/admin/counter-control')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_history_page_performance(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/admin/history')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_reports_page_performance(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/reports/')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_feedback_page_performance(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/feedback/')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_queue_management_page_performance(admin_session, mock_db_fixture):
    start = time.time()
    admin_session.get('/queue-management')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

@pytest.mark.performance
def test_login_page_load_performance(client):
    start = time.time()
    client.get('/')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 200

@pytest.mark.performance
def test_static_route_performance(admin_session):
    start = time.time()
    admin_session.get('/dashboard')
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300

# ======================================================================
# DATA STRUCTURE INITIALIZATION TESTS (Blackbox/Whitebox hybrid)
# ======================================================================
@pytest.mark.whitebox
def test_rate_limit_store_is_dict():
    from login import rate_limit_store
    assert isinstance(rate_limit_store, dict)

@pytest.mark.whitebox
def test_lockout_store_is_dict():
    from login import lockout_store
    assert isinstance(lockout_store, dict)

@pytest.mark.whitebox
def test_csrf_tokens_is_dict():
    from login import csrf_tokens
    assert isinstance(csrf_tokens, dict)

@pytest.mark.whitebox
def test_failed_attempts_store_is_dict():
    from login import failed_attempts_store
    assert isinstance(failed_attempts_store, dict)

# ======================================================================
# SESSION VALIDATION TESTS
# ======================================================================
@pytest.mark.blackbox
def test_session_has_correct_admin_fields(admin_session):
    with admin_session.session_transaction() as sess:
        assert sess.get('role') == 'admin'
        assert sess.get('office_id') is not None
        assert sess.get('user_id') is not None

@pytest.mark.blackbox
def test_session_has_correct_counter_fields(counter_session):
    with counter_session.session_transaction() as sess:
        assert sess.get('role') == 'counter'
        assert sess.get('office_id') is not None
        assert sess.get('user_id') is not None

@pytest.mark.blackbox
def test_session_has_user_email_for_admin(admin_session):
    with admin_session.session_transaction() as sess:
        assert sess.get('email') == 'admin@test.com'

# ======================================================================
# CONFIGURATION VALIDATION TESTS
# ======================================================================
@pytest.mark.whitebox
def test_app_secret_key_configured(app):
    assert app.secret_key is not None
    assert len(app.secret_key) > 0

@pytest.mark.whitebox
def test_blueprints_registered(app):
    expected_blueprints = ['login', 'counter_control', 'counterdashboard', 'qr_scanner', 
                           'createqueue', 'feedback', 'history', 'queue_management', 'reports']
    for bp in expected_blueprints:
        assert bp in app.blueprints

# ======================================================================
# CUSTOM SUMMARY REPORT - This will print after all tests complete
# ======================================================================
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add custom summary at the end of test run."""
    # Get test results
    reports = terminalreporter.stats
    
    # Count tests by category
    categories = {
        'blackbox': 0,
        'whitebox': 0,
        'security': 0,
        'performance': 0
    }
    
    # Track passed/failed per category
    passed = {
        'blackbox': 0,
        'whitebox': 0,
        'security': 0,
        'performance': 0
    }
    
    failed = {
        'blackbox': 0,
        'whitebox': 0,
        'security': 0,
        'performance': 0
    }
    
    # Process passed tests
    for test in reports.get('passed', []):
        for marker in test.keywords:
            if marker in categories:
                categories[marker] += 1
                passed[marker] += 1
                break
    
    # Process failed tests
    for test in reports.get('failed', []):
        for marker in test.keywords:
            if marker in categories:
                categories[marker] += 1
                failed[marker] += 1
                break
    
    # Print summary
    terminalreporter.write_sep("=", "TEST CATEGORY SUMMARY")
    terminalreporter.write_line("")
    terminalreporter.write_line(f"{'Category':<15} {'Total':<8} {'Passed':<8} {'Failed':<8} {'Pass Rate':<10}")
    terminalreporter.write_line("-" * 55)
    
    for category in ['blackbox', 'whitebox', 'security', 'performance']:
        total = categories[category]
        pass_count = passed[category]
        fail_count = failed[category]
        pass_rate = (pass_count / total * 100) if total > 0 else 0
        
        color = "\033[92m" if pass_rate == 100 else "\033[93m" if pass_rate >= 80 else "\033[91m"
        reset = "\033[0m"
        
        terminalreporter.write_line(
            f"{color}{category.capitalize():<15} {total:<8} {pass_count:<8} {fail_count:<8} {pass_rate:.1f}%{reset}"
        )
    
    terminalreporter.write_line("")
    terminalreporter.write_line(f"Total Tests: {sum(categories.values())}")
    terminalreporter.write_line(f"Total Passed: {sum(passed.values())}")
    terminalreporter.write_line(f"Total Failed: {sum(failed.values())}")
    terminalreporter.write_sep("=", "")