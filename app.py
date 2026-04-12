from flask import Flask

# 🔹 Import Blueprints
from routes.login import login
from routes.dashboard import dashboard
from routes.counterdashboard import counterdashboard
from routes.createcounterstaff import createcounterstaff

#  ADD THIS
from routes.create_queue import createqueue

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# ---------------- SECURITY: NO CACHE ----------------
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ---------------- REGISTER BLUEPRINTS ----------------
app.register_blueprint(login)
app.register_blueprint(dashboard)
app.register_blueprint(counterdashboard)
app.register_blueprint(createcounterstaff)

#  ADD THIS
app.register_blueprint(createqueue)

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)