# CampusIQ Documentation

## Smart College Management & Analytics Platform

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Objectives](#2-project-objectives)
3. [User Roles and RBAC](#3-user-roles-and-rbac)
4. [System Architecture](#4-system-architecture)
5. [Technology Stack](#5-technology-stack)
6. [Repository Structure](#6-repository-structure)
7. [Authentication and Security](#7-authentication-and-security)
8. [Module Documentation](#8-module-documentation)
9. [API Documentation](#9-api-documentation)
10. [Database Design](#10-database-design)
11. [Frontend Architecture](#11-frontend-architecture)
12. [Backend Architecture](#12-backend-architecture)
13. [Docker & Deployment](#13-docker--deployment)
14. [Installation & Setup](#14-installation--setup)
15. [Testing & Quality Assurance](#15-testing--quality-assurance)
16. [Demo Accounts](#16-demo-accounts)
17. [Screenshots](#17-screenshots)
18. [Known Limitations](#18-known-limitations)
19. [Future Scope](#19-future-scope)
20. [License](#20-license)
21. [Changelog](#21-changelog)

---

# 1. Executive Summary

CampusIQ is a comprehensive web-based Smart College Management & Analytics Platform designed to streamline academic operations, enhance student-faculty engagement, and provide data-driven insights for institutional decision-making.

## Problem Statement
Educational institutions face challenges in:
- Managing student attendance across multiple courses
- Tracking assignment submissions and grading workflows
- Generating performance analytics and reports
- Coordinating department-level academic operations
- Maintaining secure access control across different user roles

## Solution
CampusIQ provides a unified platform that addresses these challenges through:
- Real-time attendance tracking with predictive analytics
- Comprehensive assignment management system
- Automated grade recording and performance tracking
- Role-based dashboards for different user types
- Exportable reports in CSV and PDF formats

## Intended Users
- **Administrators** - System-wide management
- **Heads of Department (HOD)** - Department-level oversight
- **Faculty Members** - Course management and grading
- **Class Representatives (CR)** - Class-level coordination
- **Students** - Personal academic tracking

---

# 2. Project Objectives

CampusIQ is designed to achieve the following objectives:

| Objective | Implementation |
|-----------|----------------|
| Streamline Attendance Management | Web-based attendance tracking with real-time updates and predictive analytics |
| Centralize Assignment Workflows | End-to-end assignment lifecycle from creation to grading |
| Enable Data-Driven Decisions | Comprehensive reports and analytics for all stakeholders |
| Ensure Secure Access Control | Role-based access control (RBAC) with 5 distinct user roles |
| Provide Department-Level Oversight | HOD-specific dashboards and analytics |
| Support Academic Planning | Timetable management and scheduling |
| Foster Communication | Announcement system with priority handling |
| Enable Project Management | Group project tracking with milestones |

---

# 3. User Roles and RBAC

CampusIQ implements a 5-role system with granular permissions.

## Role Matrix

| Role | Purpose | Module Access |
|------|---------|---------------|
| **ADMIN** | Full system administration | All modules, user management, audit logs, system settings |
| **HOD** | Department leadership | Department analytics, student/faculty management, reports |
| **FACULTY** | Course instructors | Attendance marking, assignment management, grading |
| **CR** | Class representatives | Class attendance view, feedback, requests |
| **STUDENT** | Students | Personal attendance, assignments, marks |

## Permission Overview

### ADMIN Permissions
- Full access to all system features
- User management (create, edit, suspend, activate)
- View audit logs
- System settings management
- Department/course/subject management
- Full reports and analytics access

### HOD Permissions
- View department analytics
- Manage students and faculty in department
- View class attendance and marks
- Generate reports
- Publish announcements
- AI Assistant access

### FACULTY Permissions
- Mark and edit attendance
- Manage assignments and grade submissions
- Enter marks for students
- Supervise projects
- View class marks and student information
- Publish announcements

### CR Permissions
- View class announcements
- View class attendance (aggregate)
- Submit class requests
- Submit feedback
- AI Assistant access
- View class student information (aggregate)

### STUDENT Permissions
- View own marks
- View own attendance
- View own analytics
- Submit assignments
- Join projects
- Submit feedback
- AI Assistant access

---

# 4. System Architecture

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │  Admin    │  │   HOD     │  │  Faculty  │  │  Student  │  │
│  │  Portal   │  │  Portal   │  │  Portal   │  │  Portal   │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  │
│        │              │              │              │        │
│        └──────────────┴──────────────┴──────────────┘        │
│                              │                               │
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
```

## Architecture Components

### Frontend Layer
- React 18 with TypeScript
- Component-based UI architecture
- Role-based routing and navigation
- React Query for data fetching
- Stateless components with hooks

### Backend Layer
- FastAPI for high-performance async API
- Pydantic for data validation
- SQLAlchemy ORM for database operations
- Alembic for database migrations
- Service layer for business logic
- Dependency injection for modular design

### Database Layer
- SQLite for development/testing
- PostgreSQL for production
- Support for both through DATABASE_URL configuration

---

# 5. Technology Stack

## Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool |
| Tailwind CSS | 3.x | Styling |
| React Router | 6.x | Routing |
| TanStack Query | 5.x | Data fetching |
| React Hook Form | 7.x | Form handling |
| Recharts | 2.x | Data visualization |
| Lucide React | 0.x | Icons |

## Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.141.1 | API framework |
| Python | 3.12+ | Runtime |
| SQLAlchemy | 2.0.54 | ORM |
| Alembic | 1.20.0 | Migrations |
| Pydantic | 2.13.5 | Data validation |
| PyJWT | 2.14.0 | JWT tokens |
| bcrypt | 5.0.0 | Password hashing |
| FPDF2 | 2.8.8 | PDF generation |
| SlowAPI | 0.1.10 | Rate limiting |

## Database

| Technology | Use |
|------------|-----|
| SQLite | Development/Testing |
| PostgreSQL | Production deployment |

## Authentication & Security

| Component | Implementation |
|-----------|----------------|
| Authentication | JWT (Access + Refresh tokens) |
| Password Hashing | bcrypt (primary), argon2 (optional) |
| Token Expiry | 30 min access, 7 day refresh |
| CORS | Configurable origins |

---

# 6. Repository Structure

```
CampusIQ/
├── .github/                      # GitHub templates
│   └── ISSUE_TEMPLATE/
├── backend/                      # FastAPI backend
│   ├── app/
│   │   ├── api/v1/               # API endpoints
│   │   ├── core/                 # Config, security, deps
│   │   ├── middleware/           # Error handling
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic schemas
│   │   └── services/             # Business logic
│   ├── tests/                    # Test suite
│   ├── alembic/                  # Database migrations
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── seed.py
│   └── pytest.ini
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── components/           # Reusable components
│   │   ├── pages/                # Page components
│   │   ├── lib/                  # API, auth utilities
│   │   └── types/                # TypeScript types
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docs/                         # Documentation
├── .env.example                  # Environment template
├── .gitignore
├── LICENSE
├── README.md
└── docker-compose.yml
```

### Directory Descriptions

| Directory | Purpose |
|-----------|---------|
| `backend/app/api/v1/` | REST API endpoints organized by feature |
| `backend/app/core/` | Core functionality (auth, permissions, config) |
| `backend/app/models/` | SQLAlchemy database models |
| `backend/app/services/` | Business logic layer |
| `backend/tests/` | Pytest test suite |
| `backend/alembic/` | Database migration files |
| `frontend/src/pages/` | Route-specific page components |
| `docs/` | Technical documentation |

---

# 7. Authentication and Security

## Authentication Flow

1. **Login**: User provides credentials → JWT access + refresh tokens returned
2. **Protected Access**: Access token sent in Authorization header
3. **Token Refresh**: Refresh token used to obtain new access token
4. **Logout**: Refresh tokens revoked

## Password Management
- Passwords hashed using bcrypt (default) or argon2
- Minimum 6 characters enforced
- Never stored or transmitted in plain text

## JWT Structure
- **Access Token**: 30-minute expiry
- **Refresh Token**: 7-day expiry, rotating
- Both stored in database for revocation capability

## Authorization
- RBAC enforced on every protected endpoint
- Resource-level scoping (e.g., faculty only sees own students)
- Frontend navigation adjusts to role permissions

## Security Headers
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

## Audit Logging
- All security-sensitive actions logged
- Timestamp, user, action, resource tracked
- Admin-only access to audit log viewer

---

# 8. Module Documentation

## Authentication Module
**Purpose**: User registration, login, token management
**Users**: All authenticated users
**Features**: Login, logout, token refresh, password change

## Attendance Module
**Purpose**: Track and analyze attendance
**Users**: Faculty (mark), HOD/Admin (view), Students (view own)
**Features**:
- Mark attendance by subject/section/date
- View analytics with zone classification (Safe/Warning/Critical)
- Predictive analytics showing future risk
- CSV/PDF reports

## Assignment Module
**Purpose**: Create, submit, and grade assignments
**Users**: Faculty (create/manage), Students (submit)
**Features**:
- Create assignments with deadline and max marks
- File or text submissions
- Grade with feedback
- Late submission tracking

## Marks/Performance Module
**Purpose**: Record and track academic performance
**Users**: Faculty (enter), Students (view own), HOD (view class)
**Features**:
- Enter marks per assessment
- View performance trends
- Percentage calculations

## Project Module
**Purpose**: Manage student projects
**Users**: Faculty (supervise), Students (join), HOD (manage)
**Features**:
- Project creation with supervisor assignment
- Milestone tracking
- Group formation and approval
- Progress reporting

## Announcement Module
**Purpose**: Broadcast messages to users
**Users**: Faculty/HOD/Admin (publish), All (view)
**Features**:
- Create announcements with priority levels
- Target by role, department, or section
- Pin important announcements

## Report Module
**Purpose**: Generate analytics reports
**Users**: Admin/HOD/Faculty
**Features**:
- Attendance reports (CSV/PDF)
- Performance reports (CSV/PDF)
- Faculty workload reports
- Project progress reports
- Department reports

## Audit Log Module
**Purpose**: Track system activity
**Users**: Admin only
**Features**:
- View all security-sensitive actions
- Search and filter
- User and action tracking

## Global Search
**Purpose**: Search across resources
**Users**: All authenticated users (permission-scoped)
**Features**:
- Search students, faculty, subjects, assignments
- Permission-filtered results

## AI Assistant
**Purpose**: Provide AI-powered help
**Users**: All authenticated users
**Features**:
- Context-aware responses
- Role-based information access

---

# 9. API Documentation

## Base URL
- Local: `http://localhost:8000/api/v1`
- Interactive docs: `http://localhost:8000/docs`

## Authentication Endpoints

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| POST | `/auth/login` | Authenticate | Public |
| POST | `/auth/logout` | Logout | Auth |
| POST | `/auth/refresh` | Refresh token | Auth |
| GET | `/auth/me` | Current user | Auth |

## Attendance Endpoints

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| GET | `/attendance` | List records | Role-based |
| POST | `/attendance` | Mark attendance | Faculty |
| GET | `/attendance/analytics/me` | My analytics | Student |
| GET | `/attendance/analytics/section/{section}` | Class analytics | Faculty/HOD |

## Assignment Endpoints

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| GET | `/assignments` | List assignments | Role-based |
| POST | `/assignments` | Create assignment | Faculty |
| POST | `/assignments/{id}/submit` | Submit | Student |
| PUT | `/submissions/{id}/grade` | Grade submission | Faculty |

## Report Endpoints

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| GET | `/reports/attendance` | Attendance report | Auth |
| GET | `/reports/performance` | Performance report | Auth |
| GET | `/reports/faculty-workload` | Faculty report | HOD/Admin |
| GET | `/reports/department` | Department report | HOD/Admin |

## Audit Log Endpoints

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| GET | `/audit-logs` | List logs | Admin |
| GET | `/audit-logs/actions` | List action types | Admin |

## Search Endpoint

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| GET | `/search` | Search resources | Auth |

---

# 10. Database Design

## Core Entities

### User
- id (PK)
- email
- role (ADMIN/HOD/FACULTY/CR/STUDENT)
- status (active/suspended)

### Student
- id (PK)
- user_id (FK → User)
- enrollment_number
- department_id (FK → Department)
- semester_id
- section

### Faculty
- id (PK)
- user_id (FK → User)
- department_id (FK → Department)
- designation

### Department
- id (PK)
- name
- code

### Subject
- id (PK)
- name
- code
- department_id (FK → Department)

### Assignment
- id (PK)
- title
- subject_id (FK → Subject)
- faculty_id (FK → Faculty)
- deadline
- max_marks

### Attendance
- id (PK)
- student_id (FK → Student)
- date
- status

### Mark
- id (PK)
- student_id (FK → Student)
- marks
- max_marks

### Project
- id (PK)
- title
- supervisor_id (FK → Faculty)
- status

## Relationships
- User ↔ Student (one-to-one)
- User ↔ Faculty (one-to-one)
- Department ↔ Student (one-to-many)
- Department ↔ Faculty (one-to-many)
- Subject ↔ Assignment (one-to-many)
- Faculty ↔ Assignment (one-to-many)
- Student ↔ AssignmentSubmission (one-to-many)

## Database Support
- **SQLite**: Default for development/testing
- **PostgreSQL**: Production (configured via DATABASE_URL)

---

# 11. Frontend Architecture

## Component Hierarchy
```
App.tsx (Router)
└── Layout (Sidebar, Navigation)
    ├── Admin Pages
    │   ├── Dashboard
    │   ├── Users
    │   ├── Audit Logs
    │   └── Reports
    ├── HOD Pages
    │   ├── Dashboard
    │   ├── Students
    │   ├── Faculty
    │   └── Reports
    ├── Faculty Pages
    │   ├── Dashboard
    │   ├── Attendance
    │   ├── Assignments
    │   └── Marks
    ├── CR Pages
    │   ├── Dashboard
    │   ├── Requests
    │   └── Feedback
    └── Student Pages
        ├── Dashboard
        ├── Attendance
        └── Assignments
```

## State Management
- **React Query**: Server state (API data)
- **Local State**: Component state (forms, dialogs)

## API Integration
- Centralized `api.ts` client
- Automatic token handling
- Error handling with toast notifications

## Routing
- Role-based route guards
- Protected routes with authentication check
- Redirect to appropriate dashboard based on role

---

# 12. Backend Architecture

## Request Flow
```
Frontend → API Route → Auth/RBAC Check → Service → Database → Response
```

## Component Structure

### API Layer
- `app/api/v1/*.py` - Route definitions
- Each file handles one feature domain

### Core Layer
- `app/core/deps.py` - FastAPI dependencies
- `app/core/permissions.py` - RBAC logic
- `app/core/security.py` - Authentication utilities

### Models Layer
- `app/models/*.py` - SQLAlchemy models
- Each file represents one entity domain

### Services Layer
- `app/services/*.py` - Business logic
- Decoupled from API layer

### Migrations
- `alembic/versions/` - Database schema evolution
- Auto-generated via Alembic

---

# 13. Docker & Deployment

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| db | postgres:16-alpine | 5432 | Database |
| backend | CampusIQ backend | 8000 | API server |
| frontend | CampusIQ frontend | 5173 | Web UI |

## Environment Variables

```env
DATABASE_URL=postgresql://campusiq:campusiq@db:5432/campusiq
JWT_SECRET=change-me-to-a-long-random-hex-string
JWT_REFRESH_SECRET=change-me-to-a-different-long-random-hex-string
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173
```

## Docker Network
- Services communicate via Docker network
- Backend connects to PostgreSQL on `db:5432`
- Frontend proxies /api requests to backend

## Build Process
1. Backend: Install requirements, copy source, set entrypoint
2. Frontend: Install dependencies, copy source, start dev server

---

# 14. Installation & Setup

## Prerequisites
- Python 3.12 or higher
- Node.js 18 or higher
- (Optional) Docker and Docker Compose

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
alembic upgrade head
python seed.py  # Creates demo data
uvicorn app.main:app --reload --port 8000
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev  # Start dev server
```

## Docker Setup

```bash
docker-compose up -d
```

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

# 15. Testing & Quality Assurance

## Backend Tests
```bash
cd backend
pytest
```

**Current Results**: 114 tests passing

## Frontend Verification
```bash
cd frontend
npm run build
npx tsc --noEmit
npm run lint
```

## Test Coverage
- Authentication and authorization
- Role-based access control
- API endpoints
- Database operations
- Timezone handling
- Security headers

---

# 16. Demo Accounts

**DEVELOPMENT / DEMO ONLY** - Change passwords before production use

| Email | Password | Role |
|-------|----------|------|
| admin@campusiq.edu | Admin@123 | ADMIN |
| hod.cse@campusiq.edu | Hod@12345 | HOD |
| faculty@campusiq.edu | Faculty@123 | FACULTY |
| cr@campusiq.edu | Cr@12345 | CR |
| adnan@campusiq.edu | Student@123 | STUDENT |

---

# 17. Screenshots

Screenshots can be added here for documentation purposes:
- Dashboard views for each role
- Key workflows (attendance marking, assignment submission, etc.)

---

# 18. Known Limitations

1. **Rate Limiting**: Default limits may need adjustment for high-traffic scenarios
2. **AI Integration**: Optional OpenAI provider; demo mode available without external API
3. **File Uploads**: Maximum 10MB per file, restricted extension types
4. **Database Migration**: SQLite lacks full production features; PostgreSQL recommended

---

# 19. Future Scope

**Potential Future Enhancements**:
- Real-time notifications via WebSocket
- Multi-factor authentication
- Mobile application
- Integration with external SIS/LMS systems
- Advanced analytics dashboard
- Bulk data import/export
- Customizable report templates
- Multi-language support

---

# 20. License

This project is licensed under the MIT License.

---

# 21. Changelog

## CampusIQ v1.0.0 (Initial Release)
- Complete 5-role RBAC system
- Full attendance management
- Assignment workflow
- Marks and performance tracking
- Report generation (CSV/PDF)
- Audit logging
- Docker deployment support
