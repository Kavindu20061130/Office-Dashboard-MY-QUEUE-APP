# QueueLK – Smart Queue Management System

## Overview 📌

QueueLK is a smart queue management system designed for government offices in Sri Lanka. It helps reduce long waiting times by allowing citizens to book queue tokens remotely and track their position in real time.

The system includes a mobile application for users and a web-based dashboard for office administrators and service counters.

---

# How to Run the Project 🚀

You can run this project using any of the following methods.

---

## Method 1 – Using Terminal 💻

Step 1 - Go to project folder (after extracting ZIP)
cd path\to\your\project

Step 2 - Create virtual environment
python -m venv .venv

Step 3 - Activate virtual environment
.venv\Scripts\activate

Step 4 - Install required packages
pip install -r requirements.txt

Step 5 - Run the application
python app.py

Open in browser:
http://127.0.0.1:5000

---

## Method 2 – Using VS Code Terminal 🧑‍💻

Step 1 - Open VS Code  
Click File → Open Folder → Select project folder  

Step 2 - Open terminal  
Click Terminal → New Terminal  

Step 3 - Create virtual environment  
python -m venv .venv  

Step 4 - Activate virtual environment  
.venv\Scripts\activate  

Step 5 - Install dependencies  
pip install -r requirements.txt  

Step 6 - Run the application  
python app.py  

Open in browser:  
http://127.0.0.1:5000  

---

## Method 3 – VS Code Easy Setup ⚡

Step 1 - Open project in VS Code  

Step 2 - Create virtual environment  
Click "Select Interpreter" (top right)  
Click "Create Virtual Environment"  
Choose "Venv"  
Select Python version  

Step 3 - Open terminal  
Click Terminal → New Terminal  
(Venv will activate automatically)  

Step 4 - Install dependencies  
pip install -r requirements.txt  

Step 5 - Run the application  
python app.py  

Open in browser:  
http://127.0.0.1:5000  

---

## Admin Dashboard (Office Management) 🏢

The Admin Dashboard is designed for office staff to manage daily queue operations efficiently.

### Key Features

- View all active queues in real time  
- Monitor current serving token  
- Manage and control token flow  
- Assign tokens to service counters  
- Track queue performance and waiting times  
- Configure token limits and queue capacity  

---

## Counter Dashboard (Service Counter View) 🪟

The Counter Dashboard is used by officers at service counters to handle customers directly.

### Key Features

- View assigned tokens for the counter  
- Call next token  
- Mark users as arrived or not arrived  
- Update arrival time if needed  
- Serve and complete tokens  
- Real-time updates without refreshing  

---

## How the System Works 🔄

1. A user books a token using the mobile app  
2. The system generates a unique token number  
3. The user can track their position in real time  
4. Admin manages the queue using the dashboard  
5. Counter staff call tokens and serve users  
6. The system updates all users instantly  

---

## Key Functionalities ⚙️

- Remote token booking  
- Real-time queue tracking  
- Notification system for users  
- Admin queue management  
- Counter-based token handling  
- Feedback and rating system  
- Secure authentication and data handling  

---

## Technologies Used 🛠️

- Backend: Python (Flask)  
- Frontend: HTML, CSS, JavaScript  
- Database: Firebase Firestore  
- Authentication: Firebase Authentication  
- Real-time updates: Firebase / Socket-based updates  

---

## Benefits for Office Administration 📊

- Reduces crowding in offices  
- Improves service efficiency  
- Provides better queue control  
- Minimizes manual errors  
- Enhances user satisfaction  
- Enables real-time monitoring  

---

## Future Improvements 🔮

- AI-based queue prediction  
- Voice assistant integration  
- Indoor navigation (AR)  
- IoT-based crowd monitoring  
- Advanced analytics dashboard  

---

## Target Users 👥

- Government office administrators  
- Service counter staff  
- Citizens using public services  

---

This system aims to create a faster, more organized, and transparent service experience for both citizens and government institutions.