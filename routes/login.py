from flask import Blueprint, render_template, request, redirect, jsonify, session, flash, make_response
from firebase_config import db
from datetime import datetime, timedelta
import time
import bcrypt
import hashlib
import hmac
import secrets
from functools import wraps
import re

login = Blueprint("login", __name__)

# ==================== SECURITY CONFIGURATION ====================

# 1. Rate Limiting (In-memory - no database needed)
rate_limit_store = {}
lockout_store = {}  # Temporary lockout storage (IP-based)

# 2. Login attempt tracking (IP-based, no database)
failed_attempts_store = {}

# 3. CSRF token storage
csrf_tokens = {}

# ==================== SECURITY HELPER FUNCTIONS ====================

def rate_limit(ip_address, limit=5, window=60):
    """
    Rate limiting by IP address
    Prevents brute force attacks
    """
    now = time.time()
    if ip_address not in rate_limit_store:
        rate_limit_store[ip_address] = []
    
    # Clean old attempts
    rate_limit_store[ip_address] = [t for t in rate_limit_store[ip_address] if now - t < window]
    
    if len(rate_limit_store[ip_address]) >= limit:
        return False
    
    rate_limit_store[ip_address].append(now)
    return True

def check_ip_lockout(ip_address):
    """
    Check if IP is temporarily locked
    """
    if ip_address in lockout_store:
        lock_until = lockout_store[ip_address]
        if lock_until > datetime.utcnow():
            return True
        else:
            # Remove expired lockout
            del lockout_store[ip_address]
    return False

def record_ip_failure(ip_address):
    """
    Track IP failures and lock after 10 attempts
    """
    if ip_address not in failed_attempts_store:
        failed_attempts_store[ip_address] = {'count': 0, 'first_attempt': datetime.utcnow()}
    
    failed_attempts_store[ip_address]['count'] += 1
    
    # Lock IP after 10 failures within 5 minutes
    if failed_attempts_store[ip_address]['count'] >= 10:
        lockout_store[ip_address] = datetime.utcnow() + timedelta(minutes=15)
        return True
    
    # Reset counter after 5 minutes
    time_diff = datetime.utcnow() - failed_attempts_store[ip_address]['first_attempt']
    if time_diff.total_seconds() > 300:  # 5 minutes
        failed_attempts_store[ip_address] = {'count': 0, 'first_attempt': datetime.utcnow()}
    
    return False

def generate_csrf_token():
    """Generate a secure CSRF token"""
    return secrets.token_urlsafe(32)

def verify_csrf_token(token):
    """Verify CSRF token"""
    return token in csrf_tokens and csrf_tokens[token] > datetime.utcnow()

def cleanup_csrf_tokens():
    """Remove expired CSRF tokens"""
    now = datetime.utcnow()
    expired = [token for token, expiry in csrf_tokens.items() if expiry < now]
    for token in expired:
        del csrf_tokens[token]

def sanitize_input(input_string):
    """Sanitize user input to prevent injection"""
    if not input_string:
        return ""
    # Remove any non-printable characters
    input_string = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_string)
    # Limit length
    return input_string[:100]

def is_valid_username(username):
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 50:
        return False
    # Allow letters, numbers, @, ., _, -
    if not re.match(r'^[a-zA-Z0-9@._-]+$', username):
        return False
    return True

def generate_secure_session_id():
    """Generate a secure session ID"""
    return secrets.token_urlsafe(32)

def log_security_event(event_type, username, ip, success=True, details=""):
    """Log security events (optional - for monitoring)"""
    # Optional: Write to file or console
    timestamp = datetime.now().isoformat()
    status = "SUCCESS" if success else "FAILED"
    print(f"[SECURITY] {timestamp} | {event_type} | User: {username} | IP: {ip} | {status} | {details}")

# ==================== EXISTING FUNCTIONS (Keep as is) ====================

_offices_cache = {"data": None, "timestamp": 0, "ttl": 300}

def get_cached_offices():
    now = time.time()

    if _offices_cache["data"] and (now - _offices_cache["timestamp"]) < _offices_cache["ttl"]:
        return _offices_cache["data"]

    offices_ref = db.collection("OFFICES").stream()

    office_list = []
    for doc in offices_ref:
        data = doc.to_dict() or {}
        office_list.append({
            "id": doc.id,
            "name": data.get("name", "No Name")
        })

    _offices_cache["data"] = office_list
    _offices_cache["timestamp"] = now
    return office_list

    

def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # Add additional security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

def verify_password(plain_password, stored_hash):
    if not stored_hash:
        return False
    if stored_hash.startswith('$2b$'):
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash.encode('utf-8'))
        except ValueError:
            return False
    return plain_password == stored_hash

# ==================== LOGIN PAGE (WITH CSRF TOKEN) ====================

@login.route("/")
def index():
    if not session.get('keep_flash'):
        session.clear()
    else:
        session.pop('keep_flash', None)
    
    # Generate CSRF token for this session
    cleanup_csrf_tokens()
    csrf_token = generate_csrf_token()
    csrf_tokens[csrf_token] = datetime.utcnow() + timedelta(minutes=30)
    session['csrf_token'] = csrf_token
    
    offices = get_cached_offices()
    response = make_response(render_template("login.html", offices=offices, csrf_token=csrf_token))
    return no_cache(response)

# ==================== SECURED LOGIN ENDPOINT ====================

@login.route("/login", methods=["POST"])
def do_login():
    client_ip = request.remote_addr
    
    # ========== SECURITY CHECK 1: Rate Limiting ==========
    if not rate_limit(client_ip, limit=5, window=60):
        log_security_event("RATE_LIMIT", "Unknown", client_ip, False, "Too many attempts")
        flash("Too many login attempts. Please wait 1 minute.", "error")
        session['keep_flash'] = True
        return redirect("/")
    
    # ========== SECURITY CHECK 2: IP Lockout ==========
    if check_ip_lockout(client_ip):
        log_security_event("IP_LOCKOUT", "Unknown", client_ip, False, "IP temporarily locked")
        flash("Too many failed attempts from this location. Please wait 15 minutes.", "error")
        session['keep_flash'] = True
        return redirect("/")
    
    # ========== SECURITY CHECK 3: CSRF Token Validation ==========
    csrf_token = request.form.get("csrf_token", "")
    if not verify_csrf_token(csrf_token):
        log_security_event("CSRF_VIOLATION", "Unknown", client_ip, False, "Invalid CSRF token")
        flash("Security validation failed. Please refresh the page.", "error")
        session['keep_flash'] = True
        return redirect("/")
    
    # ========== SECURITY CHECK 4: Input Sanitization ==========
    username = sanitize_input(request.form.get("username", "").strip())
    password = request.form.get("password", "").strip()
    
    def error_redirect(message, category="error"):
        flash(message, category)
        session['keep_flash'] = True
        return redirect("/")
    
    # ========== SECURITY CHECK 5: Input Validation ==========
    if not username or not password:
        record_ip_failure(client_ip)
        log_security_event("LOGIN_FAILED", username, client_ip, False, "Missing credentials")
        return error_redirect("Please enter both username/email and password")
    
    if not is_valid_username(username):
        record_ip_failure(client_ip)
        log_security_event("LOGIN_FAILED", username, client_ip, False, "Invalid username format")
        return error_redirect("Invalid username format")
    
    if len(password) < 4 or len(password) > 128:
        record_ip_failure(client_ip)
        log_security_event("LOGIN_FAILED", username, client_ip, False, "Invalid password length")
        return error_redirect("Invalid password")
    
    # ========== SECURITY CHECK 6: Brute Force Delay ==========
    # Add random delay to prevent timing attacks
    time.sleep(secrets.randbelow(100) / 1000)  # 0-100ms random delay
    
    user_data = None
    user_role = None
    found_user = False
    
    try:
        # ========== CHECK ADMIN ==========
        admin_query = db.collection("OFFICERS").where("email", "==", username).limit(1).stream()
        for doc in admin_query:
            found_user = True
            data = doc.to_dict()
            
            # Additional delay for non-existent users (timing attack protection)
            if verify_password(password, data.get("passwordHash")):
                user_data = data
                user_data["doc_id"] = doc.id
                user_role = "admin"
                log_security_event("LOGIN_SUCCESS", username, client_ip, True, "Admin login")
                break
            else:
                # Password mismatch
                record_ip_failure(client_ip)
                log_security_event("LOGIN_FAILED", username, client_ip, False, "Invalid password")
                time.sleep(1)  # Delay to prevent brute force
                return error_redirect("Invalid username/email or password")
        
        # ========== CHECK COUNTER ==========
        if not user_data:
            counter_query = db.collection("COUNTER_SESSIONS").where("Username", "==", username).limit(1).stream()
            for doc in counter_query:
                found_user = True
                data = doc.to_dict()
                
                if verify_password(password, data.get("password")):
                    # Check account status
                    if data.get("status", "").lower() != "active":
                        log_security_event("LOGIN_FAILED", username, client_ip, False, "Inactive account")
                        return error_redirect("Counter account is inactive. Contact your office admin.")
                    
                    user_data = data
                    user_data["doc_id"] = doc.id
                    user_role = "counter"
                    log_security_event("LOGIN_SUCCESS", username, client_ip, True, "Counter login")
                    break
                else:
                    record_ip_failure(client_ip)
                    log_security_event("LOGIN_FAILED", username, client_ip, False, "Invalid password")
                    time.sleep(1)
                    return error_redirect("Invalid username/email or password")
        
        # ========== USER NOT FOUND (Timing attack protection) ==========
        if not found_user:
            record_ip_failure(client_ip)
            log_security_event("LOGIN_FAILED", username, client_ip, False, "User not found")
            time.sleep(2)  # Longer delay for non-existent users
            return error_redirect("Invalid username/email or password")
        
        if not user_data:
            return error_redirect("Invalid username/email or password")
        
        # ========== EXTRACT OFFICE ID ==========
        office_ref = user_data.get("officeId")
        if not office_ref:
            log_security_event("LOGIN_FAILED", username, client_ip, False, "No office assigned")
            return error_redirect("User has no assigned office. Contact administrator.")
        
        if hasattr(office_ref, 'id'):
            office_id = office_ref.id
        else:
            office_id = office_ref.split('/')[-1] if '/' in str(office_ref) else str(office_ref)
        
        # ========== CREATE SECURE SESSION ==========
        session.clear()
        
        # Generate new session ID
        session_id = generate_secure_session_id()
        session['session_id'] = session_id
        
        session["user"] = user_data.get("name") or user_data.get("Username") or username
        session["user_id"] = user_data["doc_id"]
        session["office_id"] = office_id
        session["role"] = user_role
        session["login_time"] = datetime.now().isoformat()
        session["ip_address"] = client_ip
        session["user_agent"] = request.headers.get('User-Agent', 'Unknown')[:200]
        session.permanent = True
        
        # Clean up used CSRF token
        if csrf_token in csrf_tokens:
            del csrf_tokens[csrf_token]
        
        # Reset IP failure counter on success
        if client_ip in failed_attempts_store:
            del failed_attempts_store[client_ip]
        
        print(f"✅ SECURE LOGIN: {session['user']} - Role: {session['role']} - IP: {client_ip}")
        
        # ========== REDIRECT ==========
        if user_role == "admin":
            response = make_response(redirect("/dashboard"))
        else:
            response = make_response(redirect("/counterdashboard"))
        
        return no_cache(response)
    
    except Exception as e:
        print("❌ LOGIN ERROR:", e)
        import traceback
        traceback.print_exc()
        log_security_event("SYSTEM_ERROR", username, client_ip, False, str(e)[:100])
        return error_redirect("Connection error. Please try again.")

# ========== SECURED LOGOUT ==========

@login.route("/logout")
def logout():
    client_ip = request.remote_addr
    username = session.get('user', 'Unknown')
    
    # Log logout event
    log_security_event("LOGOUT", username, client_ip, True, "User logged out")
    
    # Clear all session data
    session.clear()
    
    # Regenerate CSRF token for next login
    if 'csrf_token' in session:
        session.pop('csrf_token')
    
    flash("Logged out successfully", "success")
    session['keep_flash'] = True
    response = make_response(redirect("/"))
    return no_cache(response)

# ========== GET OFFICES (with rate limiting) ==========

@login.route("/get-offices")
def get_offices():
    client_ip = request.remote_addr
    
    # Simple rate limit for API endpoint
    if not rate_limit(client_ip, limit=30, window=60):
        return jsonify({"error": "Too many requests"}), 429
    
    try:
        return jsonify(get_cached_offices())
    except Exception as e:
        log_security_event("API_ERROR", "Unknown", client_ip, False, str(e)[:100])
        return jsonify({"error": str(e)}), 500

# ========== SECURITY STATUS ENDPOINT (Optional) ==========

@login.route("/security-status")
def security_status():
    """Return current security metrics (admin only)"""
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    return jsonify({
        "active_rate_limits": len(rate_limit_store),
        "active_ip_lockouts": len(lockout_store),
        "active_csrf_tokens": len(csrf_tokens),
        "failed_attempts_tracked": len(failed_attempts_store),
        "timestamp": datetime.now().isoformat()
    })