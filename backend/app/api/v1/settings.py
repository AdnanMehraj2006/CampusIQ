"""System settings, CR requests and student feedback."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.core.deps import get_current_student, pagination_params, require_permission
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.comms import CRRequest, Feedback, SystemSetting
from app.models.people import Faculty, Student
from app.models.user import User
from app.schemas import CRRequestCreate, CRRequestOut, FeedbackCreate, FeedbackOut, SystemSettingOut, SystemSettingUpdate
from app.schemas.common import paginated
from app.services.audit_service import log_from_request
from app.services.notification_service import notify

router = APIRouter(tags=["Settings & Feedback"])

DEFAULT_SETTINGS = {
    "attendance_threshold": {
        "value": str(app_settings.attendance_threshold),
        "description": "Minimum attendance percentage required to be in the safe zone",
        "category": "attendance",
    },
    "attendance_warning_min": {
        "value": str(app_settings.attendance_warning_min),
        "description": "Percentage below which a student enters the warning zone",
        "category": "attendance",
    },
    "attendance_edit_window_hours": {
        "value": str(app_settings.attendance_edit_window_hours),
        "description": "Hours after marking during which faculty may edit attendance",
        "category": "attendance",
    },
    "max_upload_size_mb": {
        "value": str(app_settings.max_upload_size_mb),
        "description": "Maximum upload size in megabytes",
        "category": "files",
    },
    "ai_provider": {
        "value": app_settings.ai_provider,
        "description": "AI assistant backend: 'demo' (offline) or 'openai'",
        "category": "ai",
    },
}


def _get_setting(db: Session, key: str) -> SystemSetting:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        return row
    default = DEFAULT_SETTINGS.get(key)
    row = SystemSetting(
        key=key,
        value=default["value"] if default else "",
        description=default["description"] if default else None,
        category=default["category"] if default else "general",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/settings", response_model=list)
def list_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_SETTINGS)),
):
    rows = []
    for key in DEFAULT_SETTINGS:
        s = _get_setting(db, key)
        rows.append(
            {"id": s.id, "key": s.key, "value": s.value, "description": s.description, "category": s.category}
        )
    return rows


@router.put("/settings/{key}", response_model=SystemSettingOut)
def update_setting(
    key: str,
    payload: SystemSettingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_SETTINGS)),
):
    if key not in DEFAULT_SETTINGS:
        raise BadRequestError(f"Unknown setting '{key}'.")
    if key in ("attendance_threshold", "attendance_warning_min", "attendance_edit_window_hours", "max_upload_size_mb"):
        try:
            float(payload.value)
        except ValueError:
            raise BadRequestError(f"Setting '{key}' must be numeric.")
    s = _get_setting(db, key)
    s.value = payload.value
    db.commit()
    db.refresh(s)
    log_from_request(db, request, current_user, "settings.update", "system_setting", resource_id=s.id,
                     details={"key": key, "value": payload.value})
    return s


# ---------------------------------------------------------------------------
# CR requests
# ---------------------------------------------------------------------------


@router.post("/cr/requests", response_model=CRRequestOut, status_code=201)
def create_cr_request(
    payload: CRRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUBMIT_REQUESTS)),
):
    if current_user.student_profile is None:
        raise ForbiddenError("Only class representatives can raise class requests.")
    
    st = current_user.student_profile
    dept_id = payload.department_id or st.department_id
    
    # Find HOD for this department
    hod_user = None
    hod_faculty = db.query(Faculty).filter(Faculty.department_id == dept_id).first()
    if hod_faculty and hod_faculty.user:
        hod_user = hod_faculty.user
    
    req = CRRequest(
        submitted_by=current_user.id,
        semester_id=st.semester_id,
        section=payload.section or st.section,
        department_id=dept_id,
        request_type=payload.request_type,
        title=payload.title,
        description=payload.description,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    
    # Notify HOD if available
    if hod_user:
        notify(
            db,
            recipient_id=hod_user.id,
            type_="request_submitted",
            title="New class request received",
            message=f"{current_user.name} submitted a request: {req.title}",
            resource_type="cr_request",
            resource_id=req.id,
        )
    
    log_from_request(db, request, current_user, "cr.request.create", "cr_request", resource_id=req.id)
    return _cr_request_out(req, current_user)


def _cr_request_out(r: CRRequest, current_user: User) -> dict:
    return {
        "id": r.id,
        "submitted_by": r.submitted_by,
        "request_type": r.request_type,
        "title": r.title,
        "description": r.description,
        "status": r.status,
        "resolution_note": r.resolution_note,
        "section": r.section,
        "semester_id": r.semester_id,
        "department_id": r.department_id,
        "author_name": r.author.name if r.author else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/cr/requests", response_model=dict)
def list_cr_requests(
    status: str | None = None,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(CRRequest)
    
    # Role-based filtering for authorization
    if current_user.role == Role.CR:
        # CRs can only see their own requests
        q = q.filter(CRRequest.submitted_by == current_user.id)
    elif current_user.role == Role.HOD and current_user.faculty_profile:
        # HODs can only see requests from their department
        q = q.filter(CRRequest.department_id == current_user.faculty_profile.department_id)
    # Admins see all requests (no filtering)
    
    # Additional user filters
    if status:
        q = q.filter(CRRequest.status == status)
    if department_id:
        q = q.filter(CRRequest.department_id == department_id)
    
    total = q.count()
    rows = q.order_by(CRRequest.id.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_cr_request_out(r, current_user) for r in rows], page_params["page"], page_params["page_size"], total)


@router.put("/cr/requests/{request_id}/resolve", response_model=CRRequestOut)
def resolve_cr_request(
    request_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_STUDENTS)),
):
    req = db.get(CRRequest, request_id)
    if not req:
        raise NotFoundError("Request not found.")
    
    # HODs can only modify requests from their department
    if current_user.role == Role.HOD and current_user.faculty_profile:
        if req.department_id != current_user.faculty_profile.department_id:
            raise ForbiddenError("You can only manage requests from your department.")
    
    old_status = req.status
    req.status = payload.get("status", "completed")
    req.resolution_note = payload.get("resolution_note")
    db.commit()
    db.refresh(req)
    
    # Notify the CR about status change
    if req.submitted_by != current_user.id:
        notify(
            db,
            recipient_id=req.submitted_by,
            type_="request_status_update",
            title="Your class request has been updated",
            message=f"Status changed from {old_status} to {req.status}.",
            resource_type="cr_request",
            resource_id=req.id,
        )
    
    log_from_request(db, request, current_user, "cr.request.resolve", "cr_request", resource_id=req.id)
    return _cr_request_out(req, current_user)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
def create_feedback(
    payload: FeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUBMIT_FEEDBACK)),
):
    # Only students and CRs can submit feedback
    if current_user.role not in (Role.STUDENT, Role.CR):
        raise ForbiddenError("Only students and class representatives can submit feedback.")
    
    if current_user.student_profile is None:
        raise ForbiddenError("No student profile is linked to your account.")
    
    st = current_user.student_profile
    
    # Department must match the student's department
    if payload.department_id is not None and payload.department_id != st.department_id:
        raise ForbiddenError("You can only submit feedback for your own department.")
    
    fb = Feedback(
        submitted_by=st.user_id,
        target_type=payload.target_type,
        subject_id=payload.subject_id,
        department_id=payload.department_id or st.department_id,
        section=payload.section or st.section,
        rating=payload.rating,
        message=payload.message,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    
    # Notify department HOD
    hod_faculty = db.query(Faculty).filter(Faculty.department_id == st.department_id).first()
    if hod_faculty and hod_faculty.user:
        notify(
            db,
            recipient_id=hod_faculty.user.id,
            type_="feedback_submitted",
            title="New feedback received",
            message=f"{st.user.name} submitted feedback about {payload.target_type}.",
            resource_type="feedback",
            resource_id=fb.id,
        )
    
    log_from_request(db, request, current_user, "feedback.create", "feedback", resource_id=fb.id)
    return _feedback_out(fb, current_user)


def _feedback_out(f: Feedback, current_user: User) -> dict:
    return {
        "id": f.id,
        "submitted_by": f.submitted_by,
        "target_type": f.target_type,
        "subject_id": f.subject_id,
        "department_id": f.department_id,
        "section": f.section,
        "rating": f.rating,
        "message": f.message,
        "status": f.status,
        "response": f.response,
        "author_name": f.author.name if f.author else None,
        "subject_name": f.subject.name if f.subject else None,
        "created_at": f.created_at,
    }


@router.get("/feedback", response_model=dict)
def list_feedback(
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(Feedback)
    
    # Role-based filtering
    if current_user.role in (Role.STUDENT, Role.CR):
        # Students/CRs can only see their own feedback
        if current_user.student_profile:
            q = q.filter(Feedback.submitted_by == current_user.student_profile.user_id)
        else:
            q = q.filter(Feedback.submitted_by == current_user.id)
    elif current_user.role == Role.HOD and current_user.faculty_profile:
        # HODs can only see feedback from their department
        q = q.filter(Feedback.department_id == current_user.faculty_profile.department_id)
    # Admins see all feedback (no filtering)
    
    total = q.count()
    rows = q.order_by(Feedback.id.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_feedback_out(f, current_user) for f in rows], page_params["page"], page_params["page_size"], total)
