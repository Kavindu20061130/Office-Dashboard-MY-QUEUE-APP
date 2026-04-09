from flask import Blueprint, render_template, request, redirect, jsonify, session, flash, make_response
from firebase_config import db
from datetime import datetime

login = Blueprint("login", __name__)

# ---------------- NO CACHE ----------------
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ---------------- LOGIN PAGE ----------------
@login.route("/")
def index():
    # Only clear session if there is NO keep_flash flag (i.e., not coming from an error or logout)
    if not session.get('keep_flash'):
        session.clear()
    else:
        # Remove the flag so future requests don't incorrectly preserve session
        session.pop('keep_flash', None)
    
    response = make_response(render_template("login.html"))
    return no_cache(response)

# ---------------- GET OFFICES ----------------
@login.route("/get-offices")
def get_offices():
    try:
        offices_ref = db.collection("OFFICES")
        docs = offices_ref.stream()

        office_list = []
        for doc in docs:
            data = doc.to_dict()
            office_list.append({
                "id": doc.id,
                "name": data.get("name", "No Name")
            })

        return jsonify(office_list)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- LOGIN LOGIC ----------------
@login.route("/login", methods=["POST"])
def do_login():

    selected_office_id = request.form.get("office_id")
    user_input = request.form.get("email").strip()
    password_input = request.form.get("password").strip()
    user_role = request.form.get("user_role")

    # Helper to preserve flash messages on error redirects
    def error_redirect(message, category="error"):
        flash(message, category)
        session['keep_flash'] = True   # <-- KEY FIX
        return redirect("/")

    # Validate required fields
    if not selected_office_id:
        return error_redirect("Please select an office")
    
    if not user_input:
        return error_redirect("Please enter username/email")
    
    if not password_input:
        return error_redirect("Please enter password")

    user_data = None

    try:
        # ================= ADMIN LOGIN =================
        if user_role == "admin":

            query = db.collection("OFFICERS") \
                      .where("email", "==", user_input) \
                      .limit(1).stream()

            for doc in query:
                temp_data = doc.to_dict()

                if temp_data.get("passwordHash") == password_input:
                    user_data = temp_data
                    user_data['display_name'] = temp_data.get("name", temp_data.get("email"))
                    user_data['doc_id'] = doc.id

            if not user_data:
                return error_redirect("Invalid Admin email or password")

        # ================= COUNTER LOGIN =================
        else:
            query = db.collection("COUNTER_SESSIONS") \
                      .where("Username", "==", user_input) \
                      .limit(1).stream()

            found_user = False

            for doc in query:
                found_user = True
                temp_data = doc.to_dict()

                # 1️⃣ PASSWORD CHECK
                if temp_data.get("password") != password_input:
                    return error_redirect("Invalid Counter username or password")

                # 2️⃣ STATUS CHECK
                if temp_data.get("status", "").lower() != "active":
                    return error_redirect("Counter account is inactive. Please contact your office admin.")

                # 3️⃣ SUCCESS
                user_data = temp_data
                user_data['display_name'] = temp_data.get("Username")
                user_data['doc_id'] = doc.id

            # ❌ USER NOT FOUND
            if not found_user:
                return error_redirect("Invalid Counter username or password")

        # ================= OFFICE VALIDATION =================
        office_ref = user_data.get("officeId")

        if not office_ref:
            return error_redirect("User has no assigned office. Please contact administrator.")

        # Extract office ID from reference
        if hasattr(office_ref, 'id'):
            user_office_id = office_ref.id
        else:
            office_path_str = office_ref.path if hasattr(office_ref, 'path') else str(office_ref)
            user_office_id = office_path_str.split('/')[-1]

        if user_office_id != selected_office_id:
            return error_redirect("You are not authorized for the selected office")

        # ================= SUCCESS SESSION =================
        session.clear()   # clear any stale data (including keep_flash)
        session["user"] = user_data.get('display_name')
        session["user_id"] = user_data.get('doc_id')
        session["office_id"] = selected_office_id
        session["role"] = user_role
        session["login_time"] = str(datetime.now())
        session.permanent = True

        print(f"✅ Login successful: {session['user']} - Role: {session['role']}")

        # ================= REDIRECT =================
        if user_role == "admin":
            response = make_response(redirect("/dashboard"))
        else:
            response = make_response(redirect("/counterdashboard"))

        return no_cache(response)

    except Exception as e:
        print("❌ ERROR in login:", e)
        import traceback
        traceback.print_exc()
        return error_redirect("A connection error occurred. Please try again.")

# ---------------- LOGOUT ----------------
@login.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    session['keep_flash'] = True
    response = make_response(redirect("/"))
    return no_cache(response)

# ---------------- DEBUG ----------------
@login.route("/debug-session")
def debug_session():
    if not session:
        return jsonify({"message": "No session data", "session": {}})
    session_dict = {}
    for key in session:
        try:
            session_dict[key] = str(session[key])
        except:
            session_dict[key] = "Unserializable"
    return jsonify({"session": session_dict})