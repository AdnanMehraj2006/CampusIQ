"""CampusIQ Assistant endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.permissions import Permission, Role
from app.database import get_db
from app.models.user import User
from app.schemas import ChatRequest, ChatResponse
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USE_AI_ASSISTANT)),
):
    """Permission-aware assistant. See ``app.services.ai_service`` for the
    security model (no raw SQL, per-tool authorization)."""
    result = ai_service.chat_router(db, current_user, payload.message, payload.history)
    return result


@router.get("/suggestions", response_model=list)
def suggestions(
    current_user: User = Depends(require_permission(Permission.USE_AI_ASSISTANT)),
):
    """Role-appropriate starter questions for the chat UI."""
    return [
        {"question": q, "category": "starter"}
        for q in ai_service.SUGGESTED_QUESTIONS.get(str(current_user.role), ai_service.SUGGESTED_QUESTIONS["student"])
    ]


@router.get("/capabilities", response_model=dict)
def capabilities(
    current_user: User = Depends(require_permission(Permission.USE_AI_ASSISTANT)),
):
    """Describe the tools the assistant may use for this caller (transparency)."""
    allowed = []
    role = str(current_user.role)
    for name, desc in ai_service.TOOL_DESCRIPTIONS.items():
        if name.startswith("get_my_") and role in ("student", "cr"):
            allowed.append({"name": name, "description": desc})
        elif name in ("get_class_statistics",) and role in ("faculty", "hod", "cr", "admin"):
            allowed.append({"name": name, "description": desc})
        elif name in ("get_department_statistics", "get_faculty_workload") and role in ("hod", "admin"):
            allowed.append({"name": name, "description": desc})
        elif role == "admin":
            allowed.append({"name": name, "description": desc})
    return {
        "mode": "demo" if (ai_service.settings.ai_provider == "demo" or not ai_service.settings.ai_api_key) else "openai",
        "tools": allowed,
    }
