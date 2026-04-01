import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate("my-queue-database-37c63-firebase-adminsdk-fbsvc-2403fb7960.json")
    firebase_admin.initialize_app(cred)

#  THIS LINE WAS MISSING
db = firestore.client()