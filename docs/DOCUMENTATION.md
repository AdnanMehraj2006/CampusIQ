# CampusIQ - Technical Documentation

## Project Overview

**CampusIQ** is a comprehensive Smart College Management & Analytics Platform designed to streamline academic operations, enhance student-faculty engagement, and provide data-driven insights for institutional decision-making.

### Project Information
| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Release Date** | September 2026 |
| **License** | MIT |
| **Repository** | GitHub |
| **Platform** | Web Application |

---

## Features

### Core Modules

1. **Attendance Management**
   - Real-time attendance tracking
   - Predictive analytics for at-risk students
   - Subject-wise breakdown
   - Zone classification (Safe/Warning/Critical)

2. **Assignment System**
   - File-based submissions
   - Automated grading workflow
   - Deadline tracking
   - Submission status monitoring

3. **Grades & Marks**
   - Assessment recording
   - Percentage calculations
   - Progress tracking
   - Performance reports

4. **Timetable Management**
   - Class scheduling
   - Faculty assignment
   - Student view
   - Conflict detection

5. **Project Management**
   - Group projects
   - Milestone tracking
   - Supervisor assignment
   - Progress monitoring

6. **Announcements**
   - Role-targeted messaging
   - Priority system
   - Delivery tracking
   - Notification system

7. **Reports & Analytics**
   - CSV/PDF export
   - Department performance
   - Faculty workload
   - Student progress

8. **Audit Logs**
   - Activity tracking
   - Security monitoring
   - Admin access control
   - Compliance support

---

## Technology Stack

### Backend
| Component | Technology |
|-----------|------------|
| Framework | FastAPI (Python 3.12+) |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Database | SQLite (Dev) / PostgreSQL (Prod) |
| Testing | pytest |
| Authentication | JWT (PyJWT) |
| Password Hashing | bcrypt / argon2 |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | React 18 |
| Language | TypeScript 5.x |
| Build Tool | Vite 5 |
| Styling | Tailwind CSS 3.x |
| State Management | TanStack Query |
| Routing | React Router 6.x |
| Forms | React Hook Form 7.x |
| Charts | Recharts |

---

## Architecture

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │  Admin    │  │   HOD     │  │  Faculty  │  │  Student  │  │
│  │  Portal   │  │  Portal   │  │  Portal   │  │  Portal   │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  │
│        │              │              │              │        │
│        └──────────────┴──────────────┴──────────────┘        │
│                              │                              │
│                      ┌───────┴───────┐                       │
│                      │   React UI    │                       │
│                      └───────┬───────┘                       │
│                              │                               │
│                       HTTP Requests                          │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────┐
│                           API LAYER                          │
│                      ┌───────┴───────┐                       │
│                      │  FastAPI App  │                       │
│                      └───────┬───────┘                       │
│                              │                               │
│                    ┌─────────┴─────────┐                     │
│                    │                   │                     │
│              ┌─────┴─────┐       ┌─────┴─────┐               │
│              │   Auth    │       │  Routes   │               │
│              │  Service  │       │   v1      │               │
│              └───────────┘       └───────────┘               │
│                    │                   │                     │
│                    └─────────┬─────────┘                     │
│                              │                               │
│                    ┌─────────┴─────────┐                     │
│                    │                   │                     │
│              ┌─────┴─────┐       ┌─────┴─────┐               │
│              │  Models   │       │ Services  │               │
│              └───────────┘       └───────────┘               │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────┐
│                         DATA LAYER                           │
│                      ┌───────┴───────┐                       │
│                      │  SQLAlchemy   │                       │
│                      │   Sessions    │                       │
│                      └───────┬───────┘                       │
│                              │                               │
│                    ┌─────────┴─────────┐                     │
│                    │                   │                     │
│              ┌─────┴─────┐       ┌─────┴─────┐               │
│              │  SQLite   │       │ PostgreSQL │               │
│              │  (Dev)    │       │  (Prod)   │               │
│              └───────────┘       └───────────┘               │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │
```

### Database Schema Overview

**Core Tables:**
- `User` - Authentication and authorization
- `Student` - Student profiles
- `Faculty` - Faculty profiles
- `Department` - Academic departments
- `Subject` - Course subjects
- `Attendance` - Attendance records
- `Assignment` - Assignment definitions
- `AssignmentSubmission` - Student submissions
- `Mark` - Grade records
- `Project` - Project definitions
- `Announcement` - System announcements
- `AuditLog` - Security audit trail

---

## Setup Instructions

### Prerequisites
- **Python** 3.12 or higher
- **Node.js** 18.x or higher
- **PostgreSQL** (for production)
- **Docker** (optional, for containerized deployment)

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed development data (optional)
python seed.py

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Docker Setup

```bash
# Start all services
docker-compose up -d

# Access services
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/logout` | User logout |
| POST | `/api/v1/auth/refresh` | Refresh token |
| GET | `/api/v1/auth/me` | Get current user |

### Role-Based Endpoints

| Role | Access Level | Key Endpoints |
|------|--------------|---------------|
| **ADMIN** | Full system | `/api/v1/people/users`, `/api/v1/audit-logs` |
| **HOD** | Department | `/api/v1/reports/department`, `/api/v1/people/students` |
| **FACULTY** | Course | `/api/v1/assignments`, `/api/v1/marks` |
| **CR** | Class | `/api/v1/cr/requests`, `/api/v1/attendance/analytics/section` |
| **STUDENT** | Personal | `/api/v1/attendance/analytics/me`, `/api/v1/assignments` |

### Report Generation

| Endpoint | Formats | Description |
|----------|---------|-------------|
| `/api/v1/reports/attendance` | CSV, PDF | Student attendance report |
| `/api/v1/reports/performance` | CSV, PDF | Student performance report |
| `/api/v1/reports/faculty-workload` | CSV, PDF | Faculty workload report |
| `/api/v1/reports/project-progress` | CSV, PDF | Project progress report |
| `/api/v1/reports/assignment-submissions` | CSV, PDF | Assignment submissions |
| `/api/v1/reports/department` | CSV, PDF | Department-wide report |

---

## Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_rbac.py
```

**Test Coverage:**
- Authentication and authorization
- Role-based access control (RBAC)
- API endpoints
- Database operations
- Timezone handling
- Security headers

### Frontend Tests

```bash
# Build for production
npm run build

# Type check
npx tsc --noEmit

# Linting
npm run lint
```

---

## Security

### Authentication
- JWT-based authentication (Access + Refresh tokens)
- Short-lived access tokens (30 minutes)
- Rotating refresh tokens
- Password hashing with bcrypt

### Authorization
- Role-based access control
- Permission checks on every endpoint
- Resource-level scoping

### Data Protection
- HTTPS for production
- SQL injection prevention (parameterized queries)
- File upload validation
- XSS and CSRF protection headers

---

## Deployment

### Production Requirements
- Environment variables configured
- Secure JWT secrets generated
- HTTPS enabled
- PostgreSQL database
- Rate limiting enabled

### Environment Variables

```env
DATABASE_URL=postgresql://user:password@host:5432/campusiq
JWT_SECRET=your-secure-secret-key
JWT_REFRESH_SECRET=your-secure-refresh-secret
FRONTEND_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
```

---

## File Structure

```
CampusIQ/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # API endpoints
│   │   ├── core/          # Config, security, permissions
│   │   ├── middleware/    # Error handling
│   │   ├── models/        # Database models
│   │   └── services/      # Business logic
│   ├── tests/
│   ├── alembic/           # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── lib/           # API client, auth
│   │   └── types/         # TypeScript types
│   └── package.json
├── docs/
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── docker-compose.yml
```

---

## Support & Contact

For issues, feature requests, or questions, please:
1. Check existing documentation
2. Review open issues on GitHub
3. Create a new issue with details

---

## License

This project is licensed under the MIT License - see LICENSE for details.

---

*Generated: September 19, 2026*
