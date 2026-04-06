from flask import Flask

from routes.login import login
from routes.dashboard import dashboard
from routes.counterdashboard import counterdashboard
#from routes.queue import queue
#from routes.counter import counter
#from routes.scanner import scanner

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

#  Disable browser caching (prevents back button access to dashboard)
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Register all routes
app.register_blueprint(login)
app.register_blueprint(dashboard)
app.register_blueprint(counterdashboard)
#app.register_blueprint(queue)
#app.register_blueprint(counter)
#app.register_blueprint(scanner)

if __name__ == "__main__":
    app.run(debug=True)