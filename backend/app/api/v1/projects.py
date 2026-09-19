"""Project management: projects, groups, milestones."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.datetime import as_utc, utcnow

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_student, pagination_params, require_permission
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.people import Faculty, Student
from app.models.project import (
    MilestoneStatus,
    Project,
    ProjectGroup,
    ProjectGroupMember,
    ProjectMilestone,
    ProjectStatus,
)
from app.models.user import User
from app.schemas import (
    MilestoneCreate,
    MilestoneOut,
    MilestoneSubmission,
    MilestoneUpdate,
    ProjectCreate,
    ProjectGroupCreate,
    ProjectGroupOut,
    ProjectOut,
    ProjectUpdate,
)
from app.schemas.common import paginated
from app.services import upload_service
from app.services.audit_service import log_from_request
from app.services.notification_service import notify


router = APIRouter(prefix="/projects", tags=["Projects"])


def _progress(milestones: list[ProjectMilestone]) -> float:
    if not milestones:
        return 0.0
    done = sum(1 for m in milestones if m.status == MilestoneStatus.COMPLETED)
    return round(done / len(milestones) * 100.0, 1)


def _project_out(db: Session, p: Project, viewer: User | None = None) -> dict:
    members = []
    for g in p.groups:
        for mem in g.members:
            members.append(mem.student.user.name if mem.student and mem.student.user else "?")
    my_group_id = None
    if viewer is not None and viewer.student_profile is not None:
        mem = (
            db.query(ProjectGroupMember)
            .join(ProjectGroup, ProjectGroup.id == ProjectGroupMember.group_id)
            .filter(ProjectGroup.project_id == p.id, ProjectGroupMember.student_id == viewer.student_profile.id)
            .first()
        )
        if mem:
            my_group_id = mem.group_id
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "project_code": p.project_code,
        "department_id": p.department_id,
        "semester_id": p.semester_id,
        "supervisor_id": p.supervisor_id,
        "status": p.status,
        "deadline": p.deadline,
        "max_group_size": p.max_group_size,
        "created_at": p.created_at,
        "supervisor_name": p.supervisor.user.name if p.supervisor and p.supervisor.user else None,
        "department_name": p.department.name if p.department else None,
        "group_count": len(p.groups),
        "member_names": sorted(set(members)),
        "progress_percentage": _progress(p.milestones),
        "my_group_id": my_group_id,
    }


def _assert_supervisor(db: Session, current_user: User, project: Project) -> None:
    if current_user.role == Role.ADMIN:
        return
    if current_user.faculty_profile is None:
        raise ForbiddenError("No faculty profile is linked to your account.")
    if project.supervisor_id != current_user.faculty_profile.id and current_user.role != Role.HOD:
        raise ForbiddenError("You can only manage projects you supervise.")
    if current_user.role == Role.HOD and project.department_id != current_user.faculty_profile.department_id:
        raise ForbiddenError("You can only manage projects within your department.")


@router.get("", response_model=dict)
def list_projects(
    department_id: int | None = None,
    status: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    q = db.query(Project)
    if current_user.role == Role.STUDENT and current_user.student_profile:
        q = q.filter(Project.semester_id == current_user.student_profile.semester_id)
    if current_user.role == Role.FACULTY and current_user.faculty_profile:
        if mine:
            q = q.filter(Project.supervisor_id == current_user.faculty_profile.id)
    if current_user.role == Role.HOD and current_user.faculty_profile:
        q = q.filter(Project.department_id == current_user.faculty_profile.department_id)
    if department_id:
        q = q.filter(Project.department_id == department_id)
    if status:
        q = q.filter(Project.status == status)
    if page_params["q"]:
        q = q.filter(Project.title.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = q.order_by(Project.id.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_project_out(db, p, current_user) for p in rows], page_params["page"], page_params["page_size"], total)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPERVISE_PROJECTS)),
):
    if current_user.faculty_profile is None:
        raise ForbiddenError("No faculty profile is linked to your account.")
    supervisor_id = payload.supervisor_id or current_user.faculty_profile.id
    if current_user.role == Role.FACULTY and supervisor_id != current_user.faculty_profile.id:
        raise ForbiddenError("You can only create projects you supervise.")
    if current_user.role == Role.HOD:
        target = db.get(Faculty, supervisor_id)
        if target and target.department_id != current_user.faculty_profile.department_id:
            raise ForbiddenError("Supervisor must belong to your department.")
    project = Project(**payload.model_dump(exclude_unset=True), supervisor_id=supervisor_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    log_from_request(db, request, current_user, "project.create", "project", resource_id=project.id)
    return _project_out(db, project, current_user)


@router.get("/my", response_model=dict)
def my_projects(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
    page_params: dict = Depends(pagination_params),
):
    """Projects the current student belongs to."""
    group_ids = [
        g.id
        for g in db.query(ProjectGroup)
        .join(ProjectGroupMember, ProjectGroupMember.group_id == ProjectGroup.id)
        .filter(ProjectGroupMember.student_id == student.id)
        .distinct()
        .all()
    ]
    project_ids = [g.project_id for g in db.query(ProjectGroup).filter(ProjectGroup.id.in_(group_ids)).all()] if group_ids else []
    q = db.query(Project).filter(Project.id.in_(project_ids)) if project_ids else db.query(Project).filter(False)
    total = q.count()
    rows = q.order_by(Project.id.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_project_out(db, p, student.user) for p in rows], page_params["page"], page_params["page_size"], total)


@router.get("/supervised", response_model=dict)
def supervised_projects(
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.SUPERVISE_PROJECTS)),
):
    if current_user.faculty_profile is None:
        raise ForbiddenError("No faculty profile is linked to your account.")
    q = db.query(Project).filter(Project.supervisor_id == current_user.faculty_profile.id)
    total = q.count()
    rows = q.order_by(Project.id.desc()).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_project_out(db, p, current_user) for p in rows], page_params["page"], page_params["page_size"], total)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project not found.")
    return _project_out(db, p, current_user)


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPERVISE_PROJECTS)),
):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project not found.")
    _assert_supervisor(db, current_user, p)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    log_from_request(db, request, current_user, "project.update", "project", resource_id=p.id)
    return _project_out(db, p, current_user)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPERVISE_PROJECTS)),
):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project not found.")
    _assert_supervisor(db, current_user, p)
    log_from_request(db, request, current_user, "project.delete", "project", resource_id=p.id)
    db.delete(p)
    db.commit()
    return {"success": True, "message": "Project deleted."}


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


def _group_out(db: Session, g: ProjectGroup) -> dict:
    return {
        "id": g.id,
        "project_id": g.project_id,
        "name": g.name,
        "proposal": g.proposal,
        "status": g.status,
        "approved": g.approved,
        "approved_at": g.approved_at,
        "project_title": g.project.title if g.project else None,
        "supervisor_name": g.project.supervisor.user.name if g.project and g.project.supervisor and g.project.supervisor.user else None,
        "members": [
            {"student_id": m.student_id, "name": m.student.user.name if m.student and m.student.user else None, "role": m.role}
            for m in g.members
        ],
    }


@router.get("/{project_id}/groups", response_model=list)
def list_groups(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project not found.")
    return [_group_out(db, g) for g in p.groups]


@router.post("/{project_id}/groups", response_model=ProjectGroupOut, status_code=201)
def create_group(
    project_id: int,
    payload: ProjectGroupCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOIN_PROJECTS)),
):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project not found.")

    me = current_user.student_profile
    if me is None:
        raise ForbiddenError("Only students can join project groups.")

    # Business rule: a student may belong to only one group per project.
    existing = (
        db.query(ProjectGroupMember)
        .join(ProjectGroup, ProjectGroup.id == ProjectGroupMember.group_id)
        .filter(ProjectGroup.project_id == project_id, ProjectGroupMember.student_id == me.id)
        .first()
    )
    if existing:
        raise ConflictError("You are already a member of a group for this project.")

    member_ids = list(dict.fromkeys(payload.member_ids))
    if me.id not in member_ids:
        member_ids.append(me.id)
    if len(member_ids) > p.max_group_size:
        raise BadRequestError(f"Group size cannot exceed {p.max_group_size} students.")

    # Ensure every member is a real student.
    valid = {s.id for s in db.query(Student).filter(Student.id.in_(member_ids)).all()}
    if len(valid) != len(member_ids):
        raise BadRequestError("Some group members are not registered students.")

    group = ProjectGroup(
        project_id=project_id,
        name=payload.name or f"Group {len(p.groups) + 1}",
        proposal=payload.proposal,
        status=ProjectStatus.PROPOSED,
    )
    db.add(group)
    db.flush()
    for mid in member_ids:
        role = "lead" if mid == me.id else "member"
        db.add(ProjectGroupMember(group_id=group.id, student_id=mid, role=role))
    db.commit()
    db.refresh(group)
    log_from_request(db, request, current_user, "project.group.create", "project_group", resource_id=group.id)
    return _group_out(db, group)


@router.put("/groups/{group_id}/approve", response_model=ProjectGroupOut)
def approve_group(
    group_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPERVISE_PROJECTS)),
):
    g = db.get(ProjectGroup, group_id)
    if not g:
        raise NotFoundError("Project group not found.")
    _assert_supervisor(db, current_user, g.project)
    g.approved = True
    g.approved_at = datetime.now(timezone.utc)
    g.status = ProjectStatus.APPROVED
    if g.project.status == ProjectStatus.PROPOSED:
        g.project.status = ProjectStatus.APPROVED
    db.commit()
    db.refresh(g)
    log_from_request(db, request, current_user, "project.group.approve", "project_group", resource_id=g.id)
    for m in g.members:
        notify(
            db,
            recipient_id=m.student.user_id,
            type_="project",
            title="Project group approved",
            message=f"Your group for '{g.project.title}' has been approved by the supervisor.",
            resource_type="project",
            resource_id=g.project_id,
        )
    return _group_out(db, g)


@router.put("/groups/{group_id}/reject", response_model=ProjectGroupOut)
def reject_group(
    group_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPERVISE_PROJECTS)),
):
    g = db.get(ProjectGroup, group_id)
    if not g:
        raise NotFoundError("Project group not found.")
    _assert_supervisor(db, current_user, g.project)
    g.status = ProjectStatus.REJECTED
    db.commit()
    db.refresh(g)
    log_from_request(db, request, current_user, "project.group.reject", "project_group", resource_id=g.id)
    return _group_out(db, g)


@router.delete("/groups/{group_id}")
def leave_group(
    group_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.JOIN_PROJECTS)),
):
    g = db.get(ProjectGroup, group_id)
    if not g:
        raise NotFoundError("Project group not found.")
    me = current_user.student_profile
    if me is None:
        raise ForbiddenError("Only students can leave project groups.")
    membership = db.query(ProjectGroupMember).filter(
        ProjectGroupMember.group_id == group_id, ProjectGroupMember.student_id == me.id
    ).first()
    if not membership:
        raise ForbiddenError("You are not a member of this group.")
    log_from_request(db, request, current_user, "project.group.leave", "project_group", resource_id=g.id)
    db.delete(membership)
    remaining = db.query(ProjectGroupMember).filter(ProjectGroupMember.group_id == group_id).count()
    if remaining == 0:
        db.delete(g)
    db.commit()
    return {"success": True, "message": "You left the project group."}


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------


def _milestone_out(m: ProjectMilestone) -> dict:
    overdue = m.status not in ("completed", "submitted") and m.deadline is not None and as_utc(m.deadline) < utcnow()
    return {
        "id": m.id,
        "project_id": m.project_id,
        "title": m.title,
        "description": m.description,
        "order_index": m.order_index,
        "deadline": m.deadline,
        "status": m.status,
        "submission_text": m.submission_text,
        "submitted_at": m.submitted_at,
        "feedback": m.feedback,
        "reviewed_at": m.reviewed_at,
        "project_title": m.project.title if m.project else None,
        "is_overdue": bool(overdue),
    }


@router.get("/{project_id}/milestones", response_model=list)
def list_milestones(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project not found.")
    return [_milestone_out(m) for m in sorted(p.milestones, key=lambda x: x.order_index)]


@router.post("/{project_id}/milestones", response_model=MilestoneOut, status_code=201)
def create_milestone(
    project_id: int,
    payload: MilestoneCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPERVISE_PROJECTS)),
):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project not found.")
    _assert_supervisor(db, current_user, p)
    last = max([m.order_index for m in p.milestones], default=-1)
    m = ProjectMilestone(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        order_index=last + 1,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    log_from_request(db, request, current_user, "milestone.create", "project_milestone", resource_id=m.id)
    return _milestone_out(m)


@router.put("/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone(
    milestone_id: int,
    payload: MilestoneUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SUPERVISE_PROJECTS)),
):
    m = db.get(ProjectMilestone, milestone_id)
    if not m:
        raise NotFoundError("Milestone not found.")
    _assert_supervisor(db, current_user, m.project)
    data = payload.model_dump(exclude_unset=True)
    if data.get("status"):
        try:
            MilestoneStatus(data["status"])
        except ValueError:
            raise BadRequestError("Invalid milestone status.")
    for k, v in data.items():
        setattr(m, k, v)
    if data.get("status") in ("completed", "submitted"):
        m.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    log_from_request(db, request, current_user, "milestone.update", "project_milestone", resource_id=m.id)
    return _milestone_out(m)


@router.post("/milestones/{milestone_id}/submit", response_model=MilestoneOut)
def submit_milestone(
    milestone_id: int,
    payload: MilestoneSubmission,
    request: Request,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    m = db.get(ProjectMilestone, milestone_id)
    if not m:
        raise NotFoundError("Milestone not found.")
    membership = (
        db.query(ProjectGroupMember)
        .join(ProjectGroup, ProjectGroup.id == ProjectGroupMember.group_id)
        .filter(ProjectGroup.project_id == m.project_id, ProjectGroupMember.student_id == student.id)
        .first()
    )
    if not membership:
        raise ForbiddenError("You must be a member of an approved group to submit milestones.")
    m.submission_text = payload.submission_text
    m.submitted_at = datetime.now(timezone.utc)
    m.submitted_by = student.id
    m.status = MilestoneStatus.SUBMITTED
    db.commit()
    db.refresh(m)
    log_from_request(db, request, student.user, "milestone.submit", "project_milestone", resource_id=m.id)
    return _milestone_out(m)


@router.post("/milestones/{milestone_id}/file", response_model=MilestoneOut)
def upload_milestone_file(
    milestone_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
):
    m = db.get(ProjectMilestone, milestone_id)
    if not m:
        raise NotFoundError("Milestone not found.")
    membership = (
        db.query(ProjectGroupMember)
        .join(ProjectGroup, ProjectGroup.id == ProjectGroupMember.group_id)
        .filter(ProjectGroup.project_id == m.project_id, ProjectGroupMember.student_id == student.id)
        .first()
    )
    if not membership:
        raise ForbiddenError("You must be a member of a project group to submit files.")
    path, original = upload_service.save_upload(file, subfolder="milestones")
    upload_service.delete_upload(m.submission_path)
    m.submission_path = path
    if not m.submission_text:
        m.submission_text = f"Attached: {original}"
    m.submitted_at = datetime.now(timezone.utc)
    m.submitted_by = student.id
    if m.status == MilestoneStatus.PENDING:
        m.status = MilestoneStatus.SUBMITTED
    db.commit()
    db.refresh(m)
    return _milestone_out(m)
