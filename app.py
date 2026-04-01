from flask import Flask, render_template, request, redirect, jsonify, session
from firebase_config import db

app = Flask(__name__)
app.secret_key = "your_secret_key_here" # Required for session handling

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/get-offices")
def get_offices():
    """Helper to populate the dropdown menu"""
    offices_ref = db.collection("OFFICES")
    docs = offices_ref.stream()
    office_list = [{"id": doc.id, "name": doc.to_dict().get("name")} for doc in docs]
    return jsonify(office_list)



@app.route("/login", methods=["POST"])
def do_login():
    selected_office_id = request.form.get("office_id")
    email = request.form.get("email")
    password = request.form.get("password")

    # 1. Check if the officer exists by email
    officers_ref = db.collection("OFFICERS").where("email", "==", email).limit(1).get()
    
    if not officers_ref:
        return render_template("login.html", error="Email not found")

    officer_data = officers_ref[0].to_dict()
    
    # 2. Check Password
    # Note: In production, use werkzeug.security to check hashes!
    if officer_data.get("passwordHash") != password:
        return render_template("login.html", error="Wrong password")

    # 3. Verify Office ID
    # In your Firestore, officeId is likely a Reference field: /OFFICES/office_1
    expected_path = f"OFFICES/{selected_office_id}"
    actual_path = officer_data.get("officeId")
    
    # Check if the path string or the reference path matches
    if hasattr(actual_path, 'path'): # If it's a Firestore Reference object
        actual_path = actual_path.path
    
    if expected_path not in str(actual_path):
        return render_template("login.html", error="You are not authorized for this office")

    # Success
    session['user'] = officer_data.get("name")
    return redirect("/dashboard")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/queue")
def queue():
    return render_template("queue.html")

@app.route("/counter")
def counter():
    return render_template("counter.html")

@app.route("/create-queue")
def create_queue():
    return render_template("create_queue.html")

@app.route("/scanner")
def scanner():
    return render_template("scanner.html")

if __name__ == "__main__":
    app.run(debug=True)