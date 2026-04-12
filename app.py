from flask import Flask

# 🔹 Existing routes
from routes.login import login
from routes.dashboard import dashboard
from routes.counterdashboard import counterdashboard

# 🔹 NEW route (Create Counter Staff)
from routes.createcounterstaff import createcounterstaff

# Optional future routes
# from routes.queue import queue
# from routes.counter import counter
# from routes.scanner import scanner

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# ---------------- NO CACHE (SECURITY) ----------------
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ---------------- REGISTER ROUTES ----------------
app.register_blueprint(login)
app.register_blueprint(dashboard)
app.register_blueprint(counterdashboard)

#  Register NEW feature
app.register_blueprint(createcounterstaff)

# Optional future routes
# app.register_blueprint(queue)
# app.register_blueprint(counter)
# app.register_blueprint(scanner)

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)