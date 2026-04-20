# Portfolio Dashboard V1

Executive portfolio tracker for managing projects and innovation ideas — with role-based access, Gantt timeline, and idea pitching board.

Built with **Python Flask** + **SQLite** backend and a single-page HTML/CSS/JS frontend (Thai language UI).

---

## Project Structure

```
portfolio-dashboard-V1/
├── backend/
│   ├── app.py              # Flask app, SQLAlchemy models, REST API
│   ├── requirements.txt    # Python dependencies
│   └── __init__.py
├── frontend/
│   └── index.html          # Single-page frontend (HTML + CSS + JS)
├── portfolio.db            # SQLite database (auto-created on first run)
├── run.py                  # Entry point
└── README.md
```

---

## Requirements

- Python 3.8+
- pip3

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/siwatsuk/portfolio-dashboard-V1.git
cd portfolio-dashboard-V1
```

**2. Install dependencies**

```bash
pip3 install -r backend/requirements.txt
```

---

## Running the App

```bash
python3 run.py
```

Then open your browser at:

```
http://localhost:5000
```

The SQLite database (`portfolio.db`) is created automatically on first run.

---
## Run on AWS
For the remote to the AWS server

ssh -i "your-key-name.pem" username@public-ip-address
Docker build
```
docker build -t dashboard-app .
```
Docker run image
```
sudo docker run -d -p 8504:8504 dashboard-app
```
If you didn't want to type sudo every time, use
sudo chown -R ubuntu:ubuntu (username: username) ....file path
This gives you the permission to user that will not require the sudo command
as an administrator.
```
13.213.3.238:8504
```
## Default Login

| Username | Password   | Role  |
|----------|------------|-------|
| `admin`  | `admin2026` | Admin |

> The admin account is built-in and cannot be deleted or overridden.

---

## Features

- **Dashboard** — KPI summary cards, donut charts by category and status
- **Gantt Timeline** — Plan vs. actual timeline visualization
- **Project Table** — Full CRUD with inline editing, progress bars, activity logs
- **Idea Pitching Board** — Kanban-style with impact/feasibility/strategic scoring
- **User Management** — Admin panel for approving, rejecting, and role assignment
- **Role-Based Access** — Admin / Manager / Viewer permissions
- **VIP Snapshot** — Executive print/PDF report

### Project Categories

| Code | Category       |
|------|----------------|
| ENE  | ⚡ Energy       |
| CST  | 💰 Cost         |
| QLT  | ✅ Quality      |
| PRD  | 📈 Productivity |
| SAF  | 🦺 Safety       |
| MRL  | 😊 Morale       |
| ENV  | 🌿 Environment  |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login |
| `POST` | `/api/auth/register` | Register (pending approval) |
| `POST` | `/api/auth/logout` | Logout |
| `GET` | `/api/users` | List all users (Admin only) |
| `POST` | `/api/users` | Create user (Admin only) |
| `PUT` | `/api/users/<id>` | Update user status/role (Admin only) |
| `DELETE` | `/api/users/<id>` | Delete user (Admin only) |
| `GET` | `/api/data` | Get all projects and ideas |
| `PUT` | `/api/data` | Save all projects and ideas |

---

## User Roles

| Role    | View | Edit Projects/Ideas | Manage Users |
|---------|------|---------------------|--------------|
| Admin   | ✅   | ✅                  | ✅           |
| Manager | ✅   | ✅                  | ❌           |
| Viewer  | ✅   | ❌                  | ❌           |

New registrations require Admin approval before login is granted.

---

## Campaign Period

Default campaign window: **1 April 2025 — 30 September 2026**

This affects Gantt timeline calculations and project progress indicators.
