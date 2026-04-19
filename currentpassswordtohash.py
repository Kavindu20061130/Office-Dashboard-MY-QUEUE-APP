import bcrypt
from firebase_config import db  # your existing Firebase init

def hash_collection(collection_name, password_field):
    docs = db.collection(collection_name).stream()
    for doc in docs:
        data = doc.to_dict()
        plain = data.get(password_field)
        if plain and not plain.startswith('$2b$'):   # not already hashed
            hashed = bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            doc.reference.update({password_field: hashed})
            print(f"✅ Updated {collection_name}/{doc.id}")

if __name__ == "__main__":
    # Hash admin passwords (field name: "passwordHash")
    hash_collection("OFFICERS", "passwordHash")
    # Hash counter passwords (field name: "password")
    hash_collection("COUNTER_SESSIONS", "password")
    print("Done!")