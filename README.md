# Child-Vaccination-Management-System-
# VacciCare - Child Vaccination Management System

A web application for tracking child vaccination schedules, appointments, providers, and notifications.

---

## Project Overview

This repository contains a Flask backend and a static frontend. The backend provides APIs for authentication, child and vaccination management, appointment scheduling, dashboards, and PDF certificate generation.

---

## Project Structure

```
vaccination-project/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration settings
│   ├── models.py           # Database models
│   ├── requirements.txt    # Python dependencies
│   ├── routes/             # API route implementations
│   │   ├── admin.py
│   │   ├── appointment.py
│   │   ├── auth.py
│   │   ├── child.py
│   │   ├── dashboard.py
│   │   ├── notification.py
│   │   ├── parent.py
│   │   ├── provider.py
│   │   ├── reports.py
│   │   ├── staff.py
│   │   └── vaccination.py
│   ├── services/           # Helper services
│   │   ├── mailer.py
│   │   ├── pdf_generator.py
│   │   ├── qr_generator.py
│   │   └── schedule_generator.py
│   └── reports_storage/    # Generated PDF certificates
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js
│       ├── api.js
│       └── utils.js
├── .env.example            # Optional environment template
└── README.md               # This file
```

---

## Quick Start

### 1. Install backend dependencies
```bash
cd backend
python -m pip install -r requirements.txt
```

### 2. Start the backend server
```bash
python app.py
```

### 3. Start the frontend server
```bash
cd ../frontend
python -m http.server 8000
```

### 4. Open the app
- Frontend: http://localhost:8000
- Backend API: http://localhost:5000

---

## Key Features

- Parent signup with child registration and automatic vaccination scheduling
- Staff registration workflow with pending admin approval
- Unified login for parent, staff, and admin roles
- Role-based dashboards for parents, staff, and admins
- Vaccination record management and certificate generation
- Appointment scheduling and cancellation
- Notifications for appointments and vaccination reminders
- PDF certificates with QR codes
- SQLite data storage and runtime persistence

---

## Backend API Highlights

### Authentication
- `POST /api/auth/signup` – Parent signup with child data
- `POST /api/auth/register/staff` – Staff self-registration (pending approval)
- `POST /api/auth/signup/staff` – Create staff account (admin only)
- `POST /api/auth/login` – Parent/staff login
- `POST /api/admin/login` – Admin login

### Dashboards
- `GET /api/dashboard/parent` – Parent dashboard data
- `GET /api/dashboard/staff` – Staff dashboard data
- `GET /api/dashboard/admin` – Admin dashboard data

### Vaccinations
- `GET /api/vaccinations` – List vaccination records
- `GET /api/vaccinations/child/<id>` – Child vaccination records
- `POST /api/vaccinations` – Create vaccination record
- `PUT /api/vaccinations/<id>` – Update vaccination record
- `DELETE /api/vaccinations/<id>` – Delete vaccination record
- `GET /api/vaccinations/vaccines/` – Vaccine catalog
- `GET /api/vaccinations/certificate/<id>` – Download PDF certificate

### Appointments
- `GET /api/appointments` – List appointments
- `POST /api/appointments` – Create appointment
- `PUT /api/appointments/<id>` – Update appointment
- `DELETE /api/appointments/<id>` – Delete appointment
- `POST /api/appointments/<id>/cancel` – Cancel appointment

### Reports
- `POST /api/reports/generate/child/<id>` – Generate certificate
- `GET /api/reports/<id>` – Get report details
- `GET /api/reports/child/<id>` – List child reports
- `GET /api/reports/download/<id>` – Download PDF certificate

---

## Notes

- The backend seeds a default `City Hospital` provider and admin account if missing.
- JWT is used for authentication and role validation.
- `backend/instance/` and `backend/reports_storage/` contain runtime data and generated certificates.
- The frontend is a static SPA and does not require build tooling.

---

## Recommended files to keep

- `backend/app.py`
- `backend/config.py`
- `backend/models.py`
- `backend/routes/`
- `backend/services/`
- `frontend/index.html`
- `frontend/css/style.css`
- `frontend/js/app.js`
- `frontend/js/api.js`
- `frontend/js/utils.js`
