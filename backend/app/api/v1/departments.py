"""Department management (admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import check_department_scope, client_ip, pagination_params, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Permission
from app.database import get_db
from app.models.academic import Department
from app.models.people import Faculty, Student
from app.models.user import User
from app.schemas import DepartmentCreate, DepartmentOut, DepartmentUpdate
from app.schemas.common import paginated
from app.services.audit_service import log_from_request

router = APIRouter(prefix="/departments", tags=["Departments"])


def _enrich(d: Department, db: Session) -> dict:
    hod_name = None
    if d.hod and d.hod.user:
        hod_name = d.hod.user.name
    return {
        "id": d.id,
        "name": d.name,
        "code": d.code,
        "description": d.description,
        "hod_id": d.hod_id,
        "hod_name": hod_name,
        "student_count": db.query(Student).filter(Student.department_id == d.id).count(),
        "faculty_count": db.query(Faculty).filter(Faculty.department_id == d.id).count(),
    }


@router.get("", response_model=dict)
def list_departments(
    db: Session = Depends(get_db),
    page_params: dict = Depends(pagination_params),
    current_user: User = Depends(require_permission(Permission.MANAGE_DEPARTMENTS)),
):
    q = db.query(Department)
    if page_params["q"]:
        q = q.filter(Department.name.ilike(f"%{page_params['q']}%") | Department.code.ilike(f"%{page_params['q']}%"))
    total = q.count()
    rows = q.order_by(Department.id).offset(page_params["offset"]).limit(page_params["page_size"]).all()
    return paginated([_enrich(d, db) for d in rows], page_params["page"], page_params["page_size"], total)


@router.get("/all", response_model=list)
def list_all_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_ANNOUNCEMENTS)),
):
    """Lightweight list for dropdowns (any authenticated user)."""
    return [{"id": d.id, "name": d.name, "code": d.code} for d in db.query(Department).order_by(Department.name).all()]


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(
    payload: DepartmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_DEPARTMENTS)),
):
    if db.query(Department).filter((Department.name == payload.name) | (Department.code == payload.code)).first():
        raise ConflictError("A department with this name or code already exists.")
    dept = Department(**payload.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    log_from_request(db, request, current_user, "department.create", "department", resource_id=dept.id)
    return _enrich(dept, db)


@router.get("/{department_id}", response_model=DepartmentOut)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_DEPARTMENTS)),
):
    dept = db.get(Department, department_id)
    if not dept:
        raise NotFoundError("Department not found.")
    return _enrich(dept, db)


@router.put("/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_DEPARTMENTS)),
):
    dept = db.get(Department, department_id)
    if not dept:
        raise NotFoundError("Department not found.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("code") and data["code"] != dept.code:
        if db.query(Department).filter(Department.code == data["code"]).first():
            raise ConflictError("Department code already in use.")
    for k, v in data.items():
        setattr(dept, k, v)
    db.commit()
    db.refresh(dept)
    log_from_request(db, request, current_user, "department.update", "department", resource_id=dept.id)
    return _enrich(dept, db)


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_DEPARTMENTS)),
):
    dept = db.get(Department, department_id)
    if not dept:
        raise NotFoundError("Department not found.")
    if db.query(Student).filter(Student.department_id == department_id).count():
        raise ConflictError("Cannot delete a department that still has students enrolled.")
    log_from_request(db, request, current_user, "department.delete", "department", resource_id=dept.id)
    db.delete(dept)
    db.commit()
    return {"success": True, "message": "Department deleted."}


@router.put("/{department_id}/hod", response_model=DepartmentOut)
def assign_hod(
    department_id: int,
    faculty_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_DEPARTMENTS)),
):
    dept = db.get(Department, department_id)
    if not dept:
        raise NotFoundError("Department not found.")
    fac = db.get(Faculty, faculty_id)
    if not fac:
        raise NotFoundError("Faculty member not found.")
    if fac.department_id != department_id:
        raise ConflictError("The HOD must belong to this department.")
    dept.hod_id = faculty_id
    fac.user.role = "hod"
    db.commit()
    db.refresh(dept)
    log_from_request(
        db, request, current_user, "department.assign_hod", "department",
        resource_id=dept.id, details={"faculty_id": faculty_id},
    )
    return _enrich(dept, db)
