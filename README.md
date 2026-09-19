# CampusIQ

Smart College Management & Analytics Platform

CampusIQ is a comprehensive web application for managing college operations, including attendance tracking, assignment management, grade recording, timetabling, and analytics. Built with a modern tech stack featuring FastAPI backend and React frontend.

## Features

- **Attendance Management** - Track student attendance with predictions and analytics
- **Assignments** - Create, assign, submit, and grade assignments
- **Marks & Grades** - Record and track student performance
- **Timetable** - View and manage class schedules
- **Projects** - Manage student projects with milestones
- **Announcements** - Broadcast messages to students and faculty
- **Reports** - Generate CSV/PDF reports for attendance, performance, and more
- **Audit Logs** - Track system activity (admin only)
- **AI Assistant** - Get AI-powered help with college operations

## Role-Based Access Control

The system supports five user roles:

| Role | Access |
|------|--------|
| **ADMIN** | Full system access, user management, audit logs |
| **HOD** | Department-level oversight, reports, analytics |
| **FACULTY** | Course management, attendance, assignments, marks |
| **CR** | Class representative access, requests, feedback |
| **STUDENT** | Personal attendance, assignments, timetable |

## Technology Stack

### Backend
- FastAPI (Python)
- SQLAlchemy
- SQLite (development) / PostgreSQL (production)
- Alembic migrations
- pytest for testing

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Router
- TanStack Query

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed database (creates demo users)
python seed.py

# Start server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=sqlite:///./campusiq.db
JWT_SECRET=your-secret-key
JWT_REFRESH_SECRET=your-refresh-secret
FRONTEND_URL=http://localhost:5173
```

## Demo Accounts

| Email | Password | Role |
|-------|----------|------|
| admin@campusiq.edu | Admin@123 | ADMIN |
| hod.cse@campusiq.edu | Hod@12345 | HOD |
| faculty@campusiq.edu | Faculty@123 | FACULTY |
| cr@campusiq.edu | Cr@12345 | CR |
| adnan@campusiq.edu | Student@123 | STUDENT |

## Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run build
npm run lint
```

## Docker Deployment

```bash
docker-compose up -d
```

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
CampusIQ/
├── backend/
│   ├── app/           # Application code
│   ├── tests/         # Test suite
│   ├── alembic/       # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/           # React source code
│   └── package.json
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Security Notes

- Never commit `.env` files to version control
- Change JWT secrets for production
- Use HTTPS in production
- Demo passwords should be changed in production

## License

MIT License
