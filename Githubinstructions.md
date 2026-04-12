# 🚀 Office Dashboard Queue App – Setup & Live Updates Guide

## 📦 1. Clone the Project (First Time Setup)

Open terminal / PowerShell and run:

```bash
git clone https://github.com/Kavindu20061130/Office-Dashboard-MY-QUEUE-APP.git
cd Office-Dashboard-MY-QUEUE-APP
```
ask me for the JSON for working code

---

## 🧪 2. Setup Virtual Environment

```bash
python -m venv .venv
```

Activate:

### Windows:

```bash
.venv\Scripts\activate
```

### Mac/Linux:

```bash
source .venv/bin/activate
```

---

## 📥 3. Install Requirements

```bash
pip install -r requirements.txt
```

---

## ▶️ 4. Run the Project

```bash
python app.py
```

Then open in browser:

```
http://127.0.0.1:5000
```

---

# 🔄 5. Get Updates (VERY IMPORTANT)

Whenever I push new updates, you MUST pull:

```bash
git pull origin create-counter-staff-ui
```

👉 This updates your code to latest version.

---

# ⚡ 6. Real-Time Workflow (While I’m Developing)

### 🔁 Before you start coding EACH TIME:

```bash
git pull
```

### 💻 After you make changes:

```bash
git add .
git commit -m "your message"
git push
```

---

# ⚠️ 7. If You Get Errors While Pulling

Run:

```bash
git stash
git pull
git stash pop
```

---

# 🧹 8. If Project Breaks (Quick Fix)

```bash
git reset --hard origin/create-counter-staff-ui
```

👉 This resets your project to latest working version.

---

# 📁 Project Structure (Important)

```
project/
│
├── templates/
│   └── *.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── vedio/
│
├── routes/
│
├── app.py
```

---

# 💡 Notes

* Always pull before coding
* Do NOT edit same file at same time without pulling
* If something breaks → pull again
* Keep branch: `create-counter-staff-ui`

---

# ✅ Done

You are now synced with the project in real-time 🚀


