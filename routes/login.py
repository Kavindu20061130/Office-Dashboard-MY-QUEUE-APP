from flask import Blueprint, render_template, request, redirect, jsonify, session, flash
from firebase_config import db

login = Blueprint("login", __name__)

# LOGIN PAGE
@login.route("/")
def index():
    return render_template("login.html")

# GET OFFICES (for dropdown)
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
        return jsonify({"error": str(e)})


# LOGIN LOGIC
@login.route("/login", methods=["POST"])
def do_login():

    selected_office_id = request.form.get("office_id")
    email = request.form.get("email").strip()
    password = request.form.get("password").strip()

    officers = db.collection("OFFICERS").where("email", "==", email).limit(1).stream()

    officer = None
    for doc in officers:
        officer = doc.to_dict()
        break

    # Email not found
    if not officer:
        flash("Email not found", "error")
        return redirect("/")

    # Wrong password
    if officer.get("passwordHash") != password:
        flash("Wrong password", "error")
        return redirect("/")

    # Check office authorization
    office_ref = officer.get("officeId")

    if hasattr(office_ref, "path"):
        office_path = office_ref.path
    else:
        office_path = str(office_ref)

    expected_path = f"OFFICES/{selected_office_id}"

    if not office_path.endswith(expected_path):
        flash("Not authorized for this office", "error")
        return redirect("/")

    # Login success
    session["user"] = officer.get("name")
    session["office_id"] = selected_office_id

    # Do not flash success here (prevents stacking issue)
    return redirect("/dashboard")


# LOGOUT
@login.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect("/")