from flask import Flask

from routes.login import login
#from routes.dashboard import dashboard
#from routes.queue import queue
#from routes.counter import counter
#from routes.scanner import scanner

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Register all routes
app.register_blueprint(login)
#app.register_blueprint(dashboard)
#app.register_blueprint(queue)
#app.register_blueprint(counter)
#app.register_blueprint(scanner)

if __name__ == "__main__":
    app.run(debug=True)