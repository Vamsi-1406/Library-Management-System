# Library Management System (LMS)

A full-featured Library Management System built with **Flask**, providing complete workflows for managing books, members, admins, transactions, payments, locations, and reservations. The system includes authentication, role-based access, inventory controls, reporting, and media uploads.

---

## 🚀 Features

### **User & Admin Management**
- Login, logout, secure session handling  
- Role-based actions (Admin vs Member)  
- Member registration & profile management  

### **Book & Inventory Management**
- Add, edit, delete books  
- Track stock across multiple locations  
- Book details with images (upload + static serving)  
- Reserve, borrow, return workflow  

### **Transactions & Payments**
- Issue/return book transactions  
- Fine/payment records  
- Automated due-date handling  

### **Locations & Stores**
- Manage library branches / stores  
- Track book availability by location  

### **Dashboard & Reporting**
- Admin dashboard for:
  - Total books, members, transactions  
  - Low-stock alerts  
  - Popular books  
- Member dashboard showing borrowed books & history  

---

## 🛠️ Tech Stack
**Backend:** Python, Flask  
**Templates:** Jinja2, HTML, CSS  
**Storage:** JSON-based collections (NoSQL-style store)  
**Images:** Uploads stored in `/static/uploads/books/`  
**Other:** Werkzeuge, session management, enums  

---

## 📂 Project Structure
LMS/
│
├── collections/ # JSON datasets (admins, books, members, transactions, etc.)
│
└── lms_project/
├── app.py # Main Flask app
├── db.py # JSON "database" handler
├── enums.py # Enum classes for roles, statuses
├── static/
│ ├── css/
│ ├── js/
│ └── uploads/books/ # Book images
└── templates/
├── admin/ # Admin UI pages
├── user/ # Member UI pages
└── shared/ # Layout, headers, footers


---

## ▶️ Running the Application

### **1. Install dependencies**
```bash
pip install -r requirements.txt

2. Launch the server
python app.py

3. Open in browser
http://127.0.0.1:5000

🧪 Test Data

The /collections/ folder includes preloaded JSON files:

books.json

members.json

admins.json

stores.json

locations.json

transactions.json

reserved_books.json

payments.json


👤 Author

Mantravadi Jaya Vamsi Krishna
Email: vamsimantravadi99@gmail.com

