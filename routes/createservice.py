from flask import Blueprint, request, session, jsonify
from firebase_config import db
from google.cloud.firestore import SERVER_TIMESTAMP
import re

createservice = Blueprint("createservice", __name__)


# ---------- Helper: generate next service ID ----------
def get_next_service_id():
    services_ref = db.collection("SERVICES")
    docs = services_ref.stream()

    max_num = 0
    for doc in docs:
        match = re.match(r'^service_(\d+)$', doc.id)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num

    return f"service_{max_num + 1}"


# ---------- Route: Create Service ----------
@createservice.route("/create-service", methods=["POST"])
def create_service():

    # 🔒 Auth guard
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        # 🔹 Get form data
        name = request.form.get("service_name", "").strip()
        charge = request.form.get("service_charge", "").strip()

        # ---------- Validation ----------
        if not name:
            return jsonify({"success": False, "error": "Service name is required."})

        if not charge:
            return jsonify({"success": False, "error": "Charge amount is required."})

        try:
            charge_int = int(float(charge))
            if charge_int < 0:
                return jsonify({"success": False, "error": "Charge must be positive."})
        except ValueError:
            return jsonify({"success": False, "error": "Invalid charge value."})

        # ---------- Get office reference from session ----------
        office_id = session.get("office_id")
        if not office_id:
            return jsonify({"success": False, "error": "Office not found in session."})
        office_ref = db.collection("OFFICES").document(office_id)

        # ---------- Generate ID ----------
        new_id = get_next_service_id()

        # ---------- Save to Firestore ----------
        db.collection("SERVICES").document(new_id).set({
            "name": name,
            "charge": charge_int,
            "officeId": office_ref,   # ← FIXED: saves as Firestore Reference
            "createdAt": SERVER_TIMESTAMP
        })

        # ---------- Success Response ----------
        return jsonify({
            "success": True,
            "message": "Service created successfully ✅",
            "service_id": new_id,
            "name": name,
            "charge": charge_int
        })

    except Exception as e:
        print("❌ Create Service Error:", e)
        return jsonify({
            "success": False,
            "error": "Something went wrong. Please try again."
        }), 500