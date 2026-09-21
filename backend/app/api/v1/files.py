"""Secure file download endpoint with authentication and authorization."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.database import get_db
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.comms import Announcement
from app.models.user import User

router = APIRouter(tags=["Files"])


def _validate_file_path(stored_path: str) -> Path:
    """Validate that the stored path is safe and return the absolute path.

    Prevents:
    - Path traversal (../)
    - Access outside upload directory
    - Absolute paths
    """
    # Reject any path with traversal components
    if ".." in stored_path or stored_path.startswith("/"):
        raise HTTPException(status_code=403, detail="Invalid file path.")

    # Normalize and resolve
    upload_root = settings.upload_path.resolve()
    requested = upload_root / stored_path

    # Ensure resolved path stays within upload root
    try:
        resolved = requested.resolve()
    except (ValueError, OSError):
        raise HTTPException(status_code=403, detail="Invalid file path.")

    if not str(resolved).startswith(str(upload_root)):
        raise HTTPException(status_code=403, detail="Access denied.")

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found.")

    return resolved


def _can_access_file(
    current_user: User,
    file_type: str,
    resource_id: int | None = None,
    student_id: int | None = None,
    db: Session | None = None,
) -> bool:
    """Check if the user can access this file.

    file_type: 'assignment', 'submission', 'announcement'
    """
    if current_user.role == "admin":
        return True

    if file_type == "announcement":
        # Only published announcement access
        if db is None:
            return False
        ann = db.query(Announcement).filter(Announcement.id == resource_id).first()
        if ann is None:
            return False
        # Check if user can view this announcement (visibility check)
        from app.services import announcement_service
        try:
            announcement_service.visible_announcements_query(db, current_user).filter(
                Announcement.id == resource_id
            ).first()
            return True
        except Exception:
            return False

    elif file_type == "assignment":
        # Assignment attachments: faculty who created it, admin, or students in the class
        if db is None or resource_id is None:
            return False
        assignment = db.query(Assignment).filter(Assignment.id == resource_id).first()
        if assignment is None:
            return False
        if assignment.faculty_id == current_user.id:
            return True
        # Students in the assignment's section or semester can access
        if current_user.student_profile:
            if assignment.subject:
                if assignment.subject.semester_id == current_user.student_profile.semester_id:
                    return True
        return False

    elif file_type == "submission":
        # Submissions: the student who submitted, their faculty, or admin
        if db is None or resource_id is None:
            return False
        submission = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == resource_id).first()
        if submission is None:
            return False
        if submission.student_id == student_id and current_user.student_profile:
            return True
        if current_user.role == "faculty":
            # Check if faculty teaches this assignment
            if submission.assignment:
                if submission.assignment.faculty_id == current_user.id:
                    return True
        return False

    return False


@router.get("/files/{file_type}/{resource_id}/{filename}")
async def download_file(
    file_type: str,
    resource_id: int,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a file with authorization checks.

    file_type: 'announcement', 'assignment', 'submission'
    """
    # Validate filename - no path traversal
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=403, detail="Invalid filename.")

    # Determine storage path based on file type
    if file_type == "announcement":
        stored_path = f"announcements/{filename}"
        if not _can_access_file(current_user, "announcement", resource_id, db=db):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to download this file."
            )

    elif file_type == "assignment":
        stored_path = f"assignments/{filename}"
        if not _can_access_file(current_user, "assignment", resource_id, db=db):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to download this file."
            )

    elif file_type == "submission":
        stored_path = f"submissions/{filename}"
        # Need student_id for submission access check
        student_id = current_user.student_profile.id if current_user.student_profile else None
        if not _can_access_file(current_user, "submission", resource_id, student_id, db=db):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to download this file."
            )

    else:
        raise HTTPException(status_code=404, detail="Unknown file type.")

    # Resolve and validate file path
    file_path = _validate_file_path(stored_path)

    # Determine content type
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content_types = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "txt": "text/plain",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "zip": "application/zip",
    }
    content_type = content_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=content_type,
    )
