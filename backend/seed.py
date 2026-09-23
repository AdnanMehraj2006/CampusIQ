"""CampusIQ seed script.

Creates a fully-populated demo college so every dashboard looks alive on first
login. Idempotent: re-running adds nothing new.

Demo credentials (also documented in README.md):
    admin@campusiq.edu    / Admin@123      (ADMIN)
    hod.cse@campusiq.edu  / Hod@12345      (HOD, Computer Science & Engineering)
    faculty@campusiq.edu  / Faculty@123    (FACULTY)
    cr@campusiq.edu       / Cr@12345       (CR, section A)
    adnan@campusiq.edu    / Student@123    (STUDENT, section A)
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session  # noqa: E402

from app.core.permissions import Role  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    AcademicSession,
    Announcement,
    AnnouncementTarget,
    Assignment,
    AssignmentSubmission,
    Attendance,
    AttendanceStatus,
    AuditLog,
    Classroom,
    Course,
    Department,
    Faculty,
    Feedback,
    Mark,
    Notification,
    Priority,
    Project,
    ProjectGroup,
    ProjectGroupMember,
    ProjectMilestone,
    ProjectStatus,
    RefreshToken,
    Semester,
    Section,
    Student,
    Subject,
    SubjectAssignment,
    SystemSetting,
    TimetableEntry,
    User,
    UserStatus,
)
from app.models.timetable import DayOfWeek  # noqa: E402

random.seed(42)

DEMO_PASSWORDS = {
    "admin@campusiq.edu": "Admin@123",
    "hod.cse@campusiq.edu": "Hod@12345",
    "hod.it@campusiq.edu": "Hod@12345",
    "hod.ece@campusiq.edu": "Hod@12345",
    "faculty@campusiq.edu": "Faculty@123",
    "faculty2@campusiq.edu": "Faculty@123",
    "faculty3@campusiq.edu": "Faculty@123",
    "cr@campusiq.edu": "Cr@12345",
    "adnan@campusiq.edu": "Student@123",
}

FIRST_NAMES = [
    "Adnan", "Burhan", "Faizan", "Tufail", "Ayesha", "Zoya", "Rohan", "Neha",
    "Karan", "Sana", "Imran", "Priya", "Vikram", "Riya", "Arjun", "Meera",
    "Sameer", "Pooja", "Nikhil", "Anjali", "Rahul", "Isha", "Vivek", "Nisha",
    "Aman", "Kavya", "Sohail", "Divya", "Faisal", "Tanvi", "Omar", "Sneha",
]
LAST_NAMES = [
    "Khan", "Sharma", "Patel", "Reddy", "Singh", "Gupta", "Malik", "Verma",
    "Nair", "Das", "Ali", "Joshi", "Rao", "Mehta", "Sheikh", "Iyer",
]

SUBJECTS_CSE = [
    ("Data Structures & Algorithms", "DSA", 4, 3),
    ("Database Management Systems", "DBMS", 4, 3),
    ("Operating Systems", "OS", 3, 3),
    ("Computer Networks", "CN", 3, 3),
    ("Object Oriented Programming", "OOP", 4, 3),
    ("Engineering Mathematics", "MATH", 4, 4),
    ("Technical Communication", "TC", 2, 2),
]

SUBJECTS_IT = [
    ("Web Technologies", "WEB", 4, 3),
    ("Software Engineering", "SE", 3, 3),
    ("Cloud Computing", "CLOUD", 3, 3),
    ("Machine Learning", "ML", 4, 3),
]

SUBJECTS_ECE = [
    ("Digital Electronics", "DE", 4, 3),
    ("Signals & Systems", "SS", 3, 3),
    ("Microprocessors", "MP", 3, 3),
    ("Analog Communication", "AC", 3, 3),
]

ASSIGNMENT_TITLES = [
    "Assignment 1 - Fundamentals",
    "Assignment 2 - Practical Implementation",
    "Assignment 3 - Case Study Analysis",
    "Assignment 4 - Project Proposal",
    "Assignment 5 - Research Report",
]


def _password(email: str) -> str:
    return DEMO_PASSWORDS.get(email, "CampusIQ@123")


def _user_exists(db: Session, email: str) -> bool:
    return db.query(User).filter(User.email == email).first() is not None


def seed(db: Session) -> dict:
    created: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Academic session + semester
    # ------------------------------------------------------------------
    session = db.query(AcademicSession).filter(AcademicSession.is_active.is_(True)).first()
    if not session:
        session = AcademicSession(
            name="2025-2026 Session",
            start_date="2025-07-01",
            end_date="2026-05-31",
            is_active=True,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        created["sessions"] = 1

    semester = db.query(Semester).filter(Semester.semester_number == 5).first()
    if not semester:
        semester = Semester(semester_number=5, academic_session_id=session.id)
        db.add(semester)
        db.commit()
        db.refresh(semester)
    created.setdefault("semesters", 1)

    semester6 = db.query(Semester).filter(Semester.semester_number == 3).first()
    if not semester6:
        semester6 = Semester(semester_number=3, academic_session_id=session.id)
        db.add(semester6)
        db.commit()
        db.refresh(semester6)

    # ------------------------------------------------------------------
    # Departments + courses
    # ------------------------------------------------------------------
    dept_specs = [
        ("Computer Science & Engineering", "CSE", SUBJECTS_CSE),
        ("Information Technology", "IT", SUBJECTS_IT),
        ("Electronics & Communication", "ECE", SUBJECTS_ECE),
    ]
    departments: dict[str, Department] = {}
    for name, code, _subs in dept_specs:
        dept = db.query(Department).filter(Department.code == code).first()
        if not dept:
            dept = Department(name=name, code=code, description=f"{name} department")
            db.add(dept)
            db.commit()
            db.refresh(dept)
        departments[code] = dept
    created["departments"] = len(departments)

    course_codes = {"CSE": "BTech", "IT": "BTech", "ECE": "BTech"}
    courses: dict[str, Course] = {}
    for code in departments:
        course = db.query(Course).filter(Course.code == f"{course_codes[code]}-{code}").first()
        if not course:
            course = Course(
                name=f"B.Tech {departments[code].name}",
                code=f"{course_codes[code]}-{code}",
                department_id=departments[code].id,
                duration_years=4,
            )
            db.add(course)
            db.commit()
            db.refresh(course)
        courses[code] = course
    created["courses"] = len(courses)

    # ------------------------------------------------------------------
    # Sections (contextual sections with academic hierarchy)
    # Same section name (e.g., "A") can exist in different academic contexts
    # ------------------------------------------------------------------
    
    # Get CSE B.Tech course and create semesters for testing
    cse_dept = departments["CSE"]
    cse_course = courses["CSE"]
    
    # Create semester 6 for CSE B.Tech
    semester6 = db.query(Semester).filter(
        Semester.semester_number == 6,
        Semester.course_id == cse_course.id,
    ).first()
    if not semester6:
        semester6 = Semester(semester_number=6, academic_session_id=session.id, course_id=cse_course.id)
        db.add(semester6)
        db.commit()
    
    # Create semester 1 for CSE M.Tech (different course)
    mtech_course = db.query(Course).filter(Course.code == "MTECH-CSE").first()
    if not mtech_course:
        mtech_course = Course(
            name="M.Tech Computer Science",
            code="MTECH-CSE",
            department_id=cse_dept.id,
            duration_years=2,
        )
        db.add(mtech_course)
        db.commit()
    
    semester1 = db.query(Semester).filter(
        Semester.semester_number == 1,
        Semester.course_id == mtech_course.id,
    ).first()
    if not semester1:
        semester1 = Semester(semester_number=1, academic_session_id=session.id, course_id=mtech_course.id)
        db.add(semester1)
        db.commit()
    
    # IT B.Tech course (if not already exists)
    it_dept = departments["IT"]
    it_course = courses["IT"]
    
    # Create sections across different academic contexts - same name but different context
    # CSE B.Tech Semester 5
    for sec_name, sec_desc in [("A", "Section A - CSE B.Tech Sem 5"), ("B", "Section B - CSE B.Tech Sem 5")]:
        sec = db.query(Section).filter(
            Section.name == sec_name,
            Section.course_id == cse_course.id,
            Section.semester_id == semester.id,
        ).first()
        if not sec:
            db.add(Section(
                name=sec_name,
                description=sec_desc,
                is_active=True,
                course_id=cse_course.id,
                semester_id=semester.id,
            ))
            db.commit()
    
    # CSE B.Tech Semester 6 (same course, different semester)
    for sec_name, sec_desc in [("A", "Section A - CSE B.Tech Sem 6"), ("B", "Section B - CSE B.Tech Sem 6")]:
        sec = db.query(Section).filter(
            Section.name == sec_name,
            Section.course_id == cse_course.id,
            Section.semester_id == semester6.id,
        ).first()
        if not sec:
            db.add(Section(
                name=sec_name,
                description=sec_desc,
                is_active=True,
                course_id=cse_course.id,
                semester_id=semester6.id,
            ))
            db.commit()
    
    # CSE M.Tech Semester 1 (different course, same section name)
    for sec_name, sec_desc in [("A", "Section A - CSE M.Tech Sem 1"), ("B", "Section B - CSE M.Tech Sem 1")]:
        sec = db.query(Section).filter(
            Section.name == sec_name,
            Section.course_id == mtech_course.id,
            Section.semester_id == semester1.id,
        ).first()
        if not sec:
            db.add(Section(
                name=sec_name,
                description=sec_desc,
                is_active=True,
                course_id=mtech_course.id,
                semester_id=semester1.id,
            ))
            db.commit()
    
    # IT B.Tech Semester 5 (different department)
    for sec_name, sec_desc in [("A", "Section A - IT B.Tech Sem 5"), ("B", "Section B - IT B.Tech Sem 5")]:
        sec = db.query(Section).filter(
            Section.name == sec_name,
            Section.course_id == it_course.id,
            Section.semester_id == semester.id,
        ).first()
        if not sec:
            db.add(Section(
                name=sec_name,
                description=sec_desc,
                is_active=True,
                course_id=it_course.id,
                semester_id=semester.id,
            ))
            db.commit()
    
    created["sections"] = db.query(Section).count()

    # ------------------------------------------------------------------
    # Users: admin, HODs, faculty
    # ------------------------------------------------------------------
    admin = db.query(User).filter(User.email == "admin@campusiq.edu").first()
    if not admin:
        admin = User(
            college_id="ADMIN001",
            name="System Administrator",
            email="admin@campusiq.edu",
            password_hash=hash_password(_password("admin@campusiq.edu")),
            role=str(Role.ADMIN),
            status=str(UserStatus.ACTIVE),
            phone="+91 98765 43210",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        created["admin"] = 1

    faculty_specs = [
        ("hod.cse@campusiq.edu", "Dr. Rajesh Khanna", "CSE", "Professor & HOD", "Head of Department", True),
        ("hod.it@campusiq.edu", "Dr. Meenakshi Iyer", "IT", "Professor & HOD", "Head of Department", True),
        ("hod.ece@campusiq.edu", "Dr. Suresh Nair", "ECE", "Professor & HOD", "Head of Department", True),
        ("faculty@campusiq.edu", "Prof. Anita Desai", "CSE", "Associate Professor", "Distributed Systems, Databases", False),
        ("faculty2@campusiq.edu", "Prof. Vivek Menon", "CSE", "Assistant Professor", "Networking, Operating Systems", False),
        ("faculty3@campusiq.edu", "Prof. Kavita Reddy", "CSE", "Assistant Professor", "Algorithms, Mathematics", False),
    ]
    faculty_map: dict[str, Faculty] = {}
    for email, name, dept_code, designation, spec, is_hod in faculty_specs:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                college_id=f"FAC{len(faculty_map) + 1:03d}",
                name=name,
                email=email,
                password_hash=hash_password(_password(email)),
                role=str(Role.HOD if is_hod else Role.FACULTY),
                status=str(UserStatus.ACTIVE),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        fac = db.query(Faculty).filter(Faculty.user_id == user.id).first()
        if not fac:
            fac = Faculty(
                user_id=user.id,
                department_id=departments[dept_code].id,
                designation=designation,
                specialization=spec,
            )
            db.add(fac)
            db.commit()
            db.refresh(fac)
        faculty_map[email] = fac
        if is_hod and departments[dept_code].hod_id is None:
            departments[dept_code].hod_id = fac.id
            db.commit()
    created["faculty"] = len(faculty_map)

    # ------------------------------------------------------------------
    # Classrooms
    # ------------------------------------------------------------------
    room_specs = [
        ("A-101", "Main Block", 60), ("A-102", "Main Block", 60), ("A-103", "Main Block", 40),
        ("B-201", "Science Block", 80), ("B-202", "Science Block", 60), ("B-203", "Science Block", 40),
        ("C-301", "IT Block", 70), ("C-302", "IT Block", 50), ("Lab-1", "Lab Block", 35),
        ("Lab-2", "Lab Block", 35),
    ]
    rooms: list[Classroom] = []
    for num, bldg, cap in room_specs:
        room = db.query(Classroom).filter(Classroom.room_number == num).first()
        if not room:
            room = Classroom(room_number=num, building=bldg, capacity=cap,
                             room_type="Laboratory" if num.startswith("Lab") else "Lecture Hall")
            db.add(room)
            db.commit()
            db.refresh(room)
        rooms.append(room)
    created["classrooms"] = len(rooms)

    # ------------------------------------------------------------------
    # Subjects
    # ------------------------------------------------------------------
    subjects: list[Subject] = []
    for dept_name, dept_code, subs in dept_specs:
        for sname, scode, credits, periods in subs:
            stored_code = scode if dept_code == "CSE" else f"{scode}-{dept_code}"
            subj = db.query(Subject).filter(
                Subject.code == stored_code, Subject.department_id == departments[dept_code].id
            ).first()
            if not subj:
                subj = Subject(
                    name=sname,
                    code=stored_code,
                    credits=credits,
                    semester_id=semester.id if dept_code == "CSE" else semester6.id,
                    department_id=departments[dept_code].id,
                    weekly_periods=periods,
                )
                db.add(subj)
                db.commit()
                db.refresh(subj)
            subjects.append(subj)
    created["subjects"] = len(subjects)

    cse_subjects = [s for s in subjects if s.department_id == departments["CSE"].id]

    # ------------------------------------------------------------------
    # Students (section A = main demo section)
    # ------------------------------------------------------------------
    section = "A"
    students: list[Student] = []

    # Named demo students first
    demo_students = [
        ("adnan@campusiq.edu", "ADNAN", "Adnan Khan", "CSE", section, False),
    ]
    cr_user = db.query(User).filter(User.email == "cr@campusiq.edu").first()

    enrollment_counter = 1
    for email, _cid, name, dept_code, sec, _is_cr in demo_students:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                college_id=f"CSE{2300 + enrollment_counter}",
                name=name,
                email=email,
                password_hash=hash_password(_password(email)),
                role=str(Role.STUDENT),
                status=str(UserStatus.ACTIVE),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        st = db.query(Student).filter(Student.user_id == user.id).first()
        if not st:
            st = Student(
                user_id=user.id,
                enrollment_number=f"CS23{1000 + enrollment_counter:03d}",
                department_id=departments[dept_code].id,
                course_id=courses[dept_code].id,
                semester_id=semester.id,
                section=sec,
                admission_year=2023,
                guardian_name="Mr. Salman Khan",
                guardian_phone="+91 98000 11111",
            )
            db.add(st)
            db.commit()
            db.refresh(st)
        students.append(st)
        enrollment_counter += 1

    # CR account
    if not cr_user:
        cr_user = User(
            college_id="CR230001",
            name="Burhan Ahmed",
            email="cr@campusiq.edu",
            password_hash=hash_password(_password("cr@campusiq.edu")),
            role=str(Role.CR),
            status=str(UserStatus.ACTIVE),
        )
        db.add(cr_user)
        db.commit()
        db.refresh(cr_user)
    cr_student = (
        db.query(Student)
        .filter((Student.user_id == cr_user.id) | (Student.enrollment_number == "CS231002"))
        .first()
    )
    if not cr_student:
        cr_student = Student(
            user_id=cr_user.id,
            enrollment_number="CS231002",
            department_id=departments["CSE"].id,
            course_id=courses["CSE"].id,
            semester_id=semester.id,
            section=section,
            admission_year=2023,
        )
        db.add(cr_student)
        db.commit()
        db.refresh(cr_student)
    if cr_student not in students:
        students.append(cr_student)

    # Generated students
    for i in range(2, 26):
        fname = FIRST_NAMES[i % len(FIRST_NAMES)]
        lname = LAST_NAMES[(i * 3) % len(LAST_NAMES)]
        name = f"{fname} {lname}"
        email = f"{fname.lower()}.{lname.lower()}{i}@campusiq.edu"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                college_id=f"CSE{2300 + i}",
                name=name,
                email=email,
                password_hash=hash_password(_password(email)),
                role=str(Role.STUDENT),
                status=str(UserStatus.ACTIVE),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        st = db.query(Student).filter(
            (Student.user_id == user.id) | (Student.enrollment_number == f"CS23{1000 + i:03d}")
        ).first()
        if not st:
            st = Student(
                user_id=user.id,
                enrollment_number=f"CS23{1000 + i:03d}",
                department_id=departments["CSE"].id,
                course_id=courses["CSE"].id,
                semester_id=semester.id,
                section=section if i <= 20 else "B",
                admission_year=2023,
            )
            db.add(st)
            db.commit()
            db.refresh(st)
        if st.section == section:
            students.append(st)
    created["students"] = db.query(Student).count()

    section_a = list({s.id: s for s in students if s.section == section}.values())

    # ------------------------------------------------------------------
    # Subject assignments (faculty -> subject -> section)
    # ------------------------------------------------------------------
    faculty_by_email = {e: f for e, f in faculty_map.items()}
    assignment_specs = [
        ("faculty@campusiq.edu", 0, "A"), ("faculty@campusiq.edu", 1, "A"),
        ("faculty2@campusiq.edu", 2, "A"), ("faculty2@campusiq.edu", 3, "A"),
        ("faculty3@campusiq.edu", 4, "A"), ("faculty3@campusiq.edu", 5, "A"),
        ("faculty@campusiq.edu", 6, "A"),
        ("faculty@campusiq.edu", 0, "B"), ("faculty2@campusiq.edu", 2, "B"),
    ]
    sa_records: list[SubjectAssignment] = []
    for email, subj_index, sec in assignment_specs:
        subj = cse_subjects[subj_index % len(cse_subjects)]
        fac = faculty_by_email[email]
        existing = db.query(SubjectAssignment).filter(
            SubjectAssignment.subject_id == subj.id,
            SubjectAssignment.faculty_id == fac.id,
            SubjectAssignment.section == sec,
        ).first()
        if existing:
            sa_records.append(existing)
            continue
        sa = SubjectAssignment(subject_id=subj.id, faculty_id=fac.id, section=sec, semester_id=semester.id)
        db.add(sa)
        db.commit()
        db.refresh(sa)
        sa_records.append(sa)
    created["subject_assignments"] = len(sa_records)

    # ------------------------------------------------------------------
    # Attendance (past ~12 weeks per subject, per section A student)
    # ------------------------------------------------------------------
    if db.query(Attendance).count() == 0:
        today = date.today()
        seen: set[tuple[int, int, date]] = set()
        att_records = []
        for subj in cse_subjects:
            # Which faculty teaches this subject in section A
            sa = db.query(SubjectAssignment).filter(
                SubjectAssignment.subject_id == subj.id, SubjectAssignment.section == section
            ).first()
            if not sa:
                continue
            marked_by = sa.faculty.user_id
            # weekly_periods sessions per week for 12 weeks
            for week in range(12):
                for k in range(subj.weekly_periods):
                    d = today - timedelta(days=week * 7 + k + 1)
                    if d.weekday() > 5:
                        continue
                    for st in section_a:
                        key = (st.id, subj.id, d)
                        if key in seen:
                            continue
                        seen.add(key)
                        roll = random.random()
                        if st.user.email == "adnan@campusiq.edu":
                            prob = 0.87
                        else:
                            prob = random.choice([0.95, 0.88, 0.82, 0.75, 0.68, 0.6])
                        status = AttendanceStatus.PRESENT if roll < prob else AttendanceStatus.ABSENT
                        if roll > 0.97:
                            status = AttendanceStatus.LATE
                        elif roll < 0.03:
                            status = AttendanceStatus.EXCUSED
                        att_records.append(
                            Attendance(
                                student_id=st.id,
                                subject_id=subj.id,
                                date=d,
                                status=status,
                                marked_by=marked_by,
                            )
                        )
                        if len(att_records) >= 4000:
                            break
                    if len(att_records) >= 4000:
                        break
                if len(att_records) >= 4000:
                    break
            if len(att_records) >= 4000:
                break
        db.bulk_save_objects(att_records)
        db.commit()
        created["attendance_records"] = len(att_records)
    else:
        created["attendance_records"] = db.query(Attendance).count()

    # ------------------------------------------------------------------
    # Assignments + submissions
    # ------------------------------------------------------------------
    assignments: list[Assignment] = []
    now = datetime.now(timezone.utc)
    for i, title in enumerate(ASSIGNMENT_TITLES):
        subj = cse_subjects[i % len(cse_subjects)]
        sa = db.query(SubjectAssignment).filter(
            SubjectAssignment.subject_id == subj.id, SubjectAssignment.section == section
        ).first()
        if not sa:
            continue
        existing = db.query(Assignment).filter(
            Assignment.title == title, Assignment.subject_id == subj.id
        ).first()
        if existing:
            assignments.append(existing)
            continue
        deadline = now + timedelta(days=(i - 2) * 5 + 3)
        a = Assignment(
            title=f"{subj.code}: {title}",
            description=f"Complete the {title.lower()} for {subj.name}. Follow the submission guidelines.",
            instructions="Submit a PDF report. Late submissions attract a 10% penalty.",
            subject_id=subj.id,
            faculty_id=sa.faculty_id,
            section=section,
            semester_id=semester.id,
            deadline=deadline,
            max_marks=20,
            allow_late=True,
        )
        db.add(a)
        db.commit()
        db.refresh(a)
        assignments.append(a)
    created["assignments"] = len(assignments)

    # Submissions for the first two (past-deadline) assignments
    if db.query(AssignmentSubmission).count() == 0:
        subs = []
        for st in section_a:
            for a in assignments[:2]:
                if random.random() < 0.8:
                    subs.append(
                        AssignmentSubmission(
                            assignment_id=a.id,
                            student_id=st.id,
                            submitted_at=a.deadline - timedelta(hours=random.randint(1, 48)),
                            is_late=False,
                            grade=random.randint(12, 20),
                            text_submission="Submitted as per the guidelines.",
                            graded_by=faculty_map["faculty@campusiq.edu"].user_id,
                            graded_at=now - timedelta(days=1),
                        )
                    )
        db.bulk_save_objects(subs)
        db.commit()
        created["submissions"] = len(subs)
    else:
        created["submissions"] = db.query(AssignmentSubmission).count()

    # ------------------------------------------------------------------
    # Marks
    # ------------------------------------------------------------------
    if db.query(Mark).count() == 0:
        marks = []
        assessment_types = [
            ("internal_exam", "Internal Exam 1", 20, 20),
            ("midterm", "Midterm Examination", 50, 50),
            ("quiz", "Surprise Quiz", 10, 10),
            ("assignment", "Coursework", 15, 15),
        ]
        for st in section_a:
            for subj in cse_subjects:
                for atype, title, mx, score_cap in assessment_types:
                    base = 0.82 if st.user.email == "adnan@campusiq.edu" else random.uniform(0.5, 0.95)
                    score = max(0, min(mx, round(mx * base)))
                    marks.append(
                        Mark(
                            student_id=st.id,
                            subject_id=subj.id,
                            assessment_type=atype,
                            title=title,
                            marks=score,
                            max_marks=mx,
                            entered_by=faculty_map["faculty@campusiq.edu"].user_id,
                        )
                    )
        db.bulk_save_objects(marks)
        db.commit()
        created["marks"] = len(marks)
    else:
        created["marks"] = db.query(Mark).count()

    # ------------------------------------------------------------------
    # Projects + milestones
    # ------------------------------------------------------------------
    projects_spec = [
        ("CampusIQ - Smart College Management Platform",
         "A centralized platform for attendance, analytics, timetable and project management.",
         "faculty@campusiq.edu", ProjectStatus.IN_PROGRESS, ["Adnan Khan", "Burhan Ahmed", "Faizan Sheikh"]),
        ("AI-Powered Traffic Sign Recognition",
         "Real-time traffic sign detection using convolutional neural networks.",
         "faculty2@campusiq.edu", ProjectStatus.IN_PROGRESS, ["Ayesha Sharma", "Rohan Verma"]),
        ("Blockchain-Based Certificate Verification",
         "Tamper-proof academic certificate issuance and verification.",
         "faculty3@campusiq.edu", ProjectStatus.APPROVED, ["Karan Reddy", "Sana Gupta"]),
        ("Campus Bus Tracking System",
         "IoT-based live tracking of college transport.",
         "faculty@campusiq.edu", ProjectStatus.PROPOSED, ["Imran Khan", "Priya Nair", "Vikram Das"]),
    ]
    milestone_names = [
        ("Problem Statement", "Define the problem and objectives."),
        ("Proposal", "Literature survey and project proposal."),
        ("System Design", "Architecture, data model and UI wireframes."),
        ("Implementation", "Build the core modules."),
        ("Testing", "Functional and non-functional testing."),
        ("Final Report", "Documentation and presentation."),
    ]
    projects: list[Project] = []
    name_to_student = {s.user.name: s for s in students}
    for title, desc, fac_email, status, member_names in projects_spec:
        fac = faculty_map[fac_email]
        existing = db.query(Project).filter(Project.title == title).first()
        if existing:
            projects.append(existing)
            continue
        p = Project(
            title=title,
            description=desc,
            department_id=departments["CSE"].id,
            semester_id=semester.id,
            supervisor_id=fac.id,
            status=str(status),
            deadline=now + timedelta(days=random.randint(20, 90)),
            max_group_size=4,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        projects.append(p)

        # group + members
        g = ProjectGroup(
            project_id=p.id,
            name=f"Team {p.id}",
            proposal=desc,
            status=str(ProjectStatus.APPROVED if status != ProjectStatus.PROPOSED else ProjectStatus.PROPOSED),
            approved=status != ProjectStatus.PROPOSED,
            approved_at=now - timedelta(days=5) if status != ProjectStatus.PROPOSED else None,
        )
        db.add(g)
        db.commit()
        db.refresh(g)
        members = [name_to_student[n] for n in member_names if n in name_to_student]
        for idx, mem in enumerate(members):
            db.add(ProjectGroupMember(group_id=g.id, student_id=mem.id, role="lead" if idx == 0 else "member"))
        db.commit()

        # milestones with progressive completion
        completed_count = {"proposed": 1, "approved": 3, "in_progress": 4, "completed": 6}.get(str(status), 2)
        for mi, (mname, mdesc) in enumerate(milestone_names):
            ms_status = "completed" if mi < completed_count else ("in_progress" if mi == completed_count else "pending")
            db.add(
                ProjectMilestone(
                    project_id=p.id,
                    title=mname,
                    description=mdesc,
                    order_index=mi,
                    deadline=now + timedelta(days=(mi - 2) * 12),
                    status=ms_status,
                    submission_text="Delivered." if ms_status == "completed" else None,
                    submitted_at=now - timedelta(days=20 - mi * 3) if ms_status == "completed" else None,
                    feedback="Good work, approved." if ms_status == "completed" else None,
                    reviewed_at=now - timedelta(days=19 - mi * 3) if ms_status == "completed" else None,
                )
            )
        db.commit()
    created["projects"] = len(projects)

    # ------------------------------------------------------------------
    # Timetable (section A)
    # ------------------------------------------------------------------
    if db.query(TimetableEntry).filter(TimetableEntry.section == section).count() == 0:
        days = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]
        period_times = [
            ("09:00", "09:55"), ("10:00", "10:55"), ("11:00", "11:55"),
            ("12:00", "12:55"), ("14:00", "14:55"), ("15:00", "15:55"),
        ]
        entries = []
        for day in days:
            for period in range(1, 7):
                subj = cse_subjects[(days.index(day) + period) % len(cse_subjects)]
                sa = db.query(SubjectAssignment).filter(
                    SubjectAssignment.subject_id == subj.id, SubjectAssignment.section == section
                ).first()
                if not sa:
                    continue
                room = rooms[(days.index(day) + period) % len(rooms)]
                entries.append(
                    TimetableEntry(
                        day=day,
                        period=period,
                        subject_id=subj.id,
                        faculty_id=sa.faculty_id,
                        classroom_id=room.id,
                        section=section,
                        semester_id=semester.id,
                        academic_session_id=session.id,
                        start_time=period_times[period - 1][0],
                        end_time=period_times[period - 1][1],
                    )
                )
        db.bulk_save_objects(entries)
        db.commit()
        created["timetable_entries"] = len(entries)
    else:
        created["timetable_entries"] = db.query(TimetableEntry).count()

    # ------------------------------------------------------------------
    # Announcements
    # ------------------------------------------------------------------
    if db.query(Announcement).count() == 0:
        ann_specs = [
            ("Welcome to CampusIQ - Spring Semester Begins!", "All classes for the 2025-2026 session begin Monday. Please check your timetable.", AnnouncementTarget.EVERYONE, Priority.HIGH),
            ("Mid-Semester Examinations Schedule Released", "The midterm examination schedule is now available on the academic portal.", AnnouncementTarget.DEPARTMENT, Priority.NORMAL),
            ("Section A: Database Lab Shifted to Lab-2", "Tomorrow's DBMS lab will be held in Lab-2 instead of A-102.", AnnouncementTarget.SECTION, Priority.NORMAL),
            ("Industry Guest Lecture on Cloud Computing", "Join us Friday for a guest lecture by industry experts on cloud architecture.", AnnouncementTarget.EVERYONE, Priority.NORMAL),
            ("Project Proposal Deadline Extended", "The final-year project proposal deadline has been extended by one week.", AnnouncementTarget.SEMESTER, Priority.HIGH),
            ("Library Timing Extended During Exams", "The library will remain open until 10 PM during the examination weeks.", AnnouncementTarget.EVERYONE, Priority.LOW),
        ]
        for i, (title, content, target, prio) in enumerate(ann_specs):
            db.add(
                Announcement(
                    title=title,
                    content=content,
                    target_type=str(target),
                    department_id=departments["CSE"].id if target == AnnouncementTarget.DEPARTMENT else None,
                    section=section if target == AnnouncementTarget.SECTION else None,
                    semester_id=semester.id if target == AnnouncementTarget.SEMESTER else None,
                    priority=str(prio),
                    published_by=admin.id,
                    published_at=now - timedelta(days=i),
                    is_pinned=(i == 0),
                )
            )
        db.commit()
        created["announcements"] = len(ann_specs)
    else:
        created["announcements"] = db.query(Announcement).count()

    # ------------------------------------------------------------------
    # Notifications for the demo student
    # ------------------------------------------------------------------
    adnan = db.query(Student).join(User, User.id == Student.user_id).filter(User.email == "adnan@campusiq.edu").first()
    if adnan and db.query(Notification).filter(Notification.recipient_id == adnan.user_id).count() == 0:
        notif_specs = [
            ("attendance_warning", "Attendance below threshold", "Your OS attendance is below 75%. Please attend upcoming classes."),
            ("assignment", "Assignment due soon", "DSA: Assignment 3 - Case Study Analysis is due in 3 days."),
            ("marks_published", "Marks published", "Your Internal Exam 1 results for DBMS are now available."),
            ("project_deadline", "Project milestone due", "CampusIQ milestone 'Implementation' is due soon."),
            ("announcement", "New announcement", "Mid-Semester Examinations Schedule Released"),
            ("attendance_marked", "Attendance marked", "Today's DSA attendance has been marked."),
        ]
        for i, (ntype, title, msg) in enumerate(notif_specs):
            db.add(
                Notification(
                    recipient_id=adnan.user_id,
                    type=ntype,
                    title=title,
                    message=msg,
                    is_read=i > 3,
                )
            )
        db.commit()
        created["notifications"] = len(notif_specs)
    else:
        created["notifications"] = db.query(Notification).count()

    # ------------------------------------------------------------------
    # System settings + a feedback record
    # ------------------------------------------------------------------
    if db.query(SystemSetting).count() == 0:
        from app.config import settings as cfg

        for key, val in [
            ("attendance_threshold", str(cfg.attendance_threshold)),
            ("attendance_warning_min", str(cfg.attendance_warning_min)),
            ("attendance_edit_window_hours", str(cfg.attendance_edit_window_hours)),
            ("ai_provider", cfg.ai_provider),
        ]:
            db.add(SystemSetting(key=key, value=val, category="system"))
        db.commit()

    if db.query(Feedback).count() == 0 and adnan:
        db.add(
            Feedback(
                submitted_by=adnan.user_id,
                target_type="subject",
                subject_id=cse_subjects[0].id,
                department_id=departments["CSE"].id,
                section=section,
                rating=5,
                message="The DSA classes are well structured and the assignments are relevant.",
                status="open",
            )
        )
        db.commit()

    # Audit the seed run itself (marked as system).
    db.add(
        AuditLog(
            user_name="system",
            role="admin",
            action="system.seed",
            resource="system",
            resource_id="1",
            details={"created": created},
        )
    )
    db.commit()

    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the CampusIQ demo database")
    parser.add_argument("--skip-if-populated", action="store_true",
                        help="Exit silently if users already exist")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.skip_if_populated:
            count = db.query(User).count()
            if count > 0:
                print(f"[seed] Database already has {count} user(s); skipping.")
                return 0

        print("[seed] Creating demo college data...")
        result = seed(db)
        print("[seed] Done. Summary:")
        for k, v in sorted(result.items()):
            print(f"    {k:<22}: {v}")
        print()
        print("[seed] Demo credentials:")
        for email, pwd in DEMO_PASSWORDS.items():
            print(f"    {email:<24} / {pwd}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
