from flask import Flask

# 🔹 Import Blueprints
from routes.counterdashboard import counterdashboard 
from routes.login import login
from routes.dashboard import dashboard
from routes.counter_control import counter_control                          
from routes.createcounterstaff import createcounterstaff
from routes.createservice import createservice
from routes.create_queue import createqueue
from routes.queue_management import queue_management
from routes.qr_scanner import qr_scanner
from routes.counter_qr_scanner import counter_qr_scanner
from routes.reports import reports

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
app.register_blueprint(counter_control)  
app.register_blueprint(createcounterstaff)
app.register_blueprint(createservice)
app.register_blueprint(createqueue)
app.register_blueprint(queue_management)
app.register_blueprint(counterdashboard)
app.register_blueprint(qr_scanner)
app.register_blueprint(counter_qr_scanner)
app.register_blueprint(reports) 

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)