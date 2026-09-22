"""Analytics, AI assistant, search and report schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# ---- Analytics ----
class DashboardCard(BaseModel):
    label: str
    value: Any
    sublabel: Optional[str] = None
    trend: Optional[float] = None


class ChartSeries(BaseModel):
    name: str
    data: List[Any]


class AnalyticsResponse(BaseModel):
    success: bool = True
    period: Optional[str] = None
    cards: List[DashboardCard] = []
    charts: Dict[str, Any] = {}
    tables: Dict[str, Any] = {}


# ---- AI ----
class ChatMessage(BaseModel):
    role: str = Field("user", pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: List[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatTurn(BaseModel):
    role: str
    content: str
    tools_used: Optional[List[str]] = None


class ChatResponse(BaseModel):
    success: bool = True
    reply: str
    tools_used: List[str] = []
    mode: str = "demo"
    conversation_id: Optional[str] = None


class AISuggestion(BaseModel):
    question: str
    category: str


# ---- Search ----
class SearchResultItem(BaseModel):
    type: str
    id: int
    title: str
    subtitle: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    success: bool = True
    items: List[SearchResultItem]
    pagination: dict


# ---- Settings ----
class SystemSettingOut(ORMModel):
    id: int
    key: str
    value: str
    description: Optional[str] = None
    category: str


class SystemSettingUpdate(BaseModel):
    value: str


class CRRequestCreate(BaseModel):
    request_type: str = Field(..., max_length=50)
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5)
    section: Optional[str] = None
    department_id: Optional[int] = None


class CRRequestOut(ORMModel):
    id: int
    submitted_by: int
    request_type: str
    title: str
    description: str
    status: str
    resolution_note: Optional[str] = None
    section: Optional[str] = None
    semester_id: Optional[int] = None
    department_id: Optional[int] = None
    author_name: Optional[str] = None
    created_at: str


class FeedbackCreate(BaseModel):
    target_type: str = Field(..., max_length=30)
    subject_id: Optional[int] = None
    department_id: Optional[int] = None
    section: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    message: str = Field(..., min_length=5)


class FeedbackOut(ORMModel):
    id: int
    submitted_by: int
    target_type: str
    subject_id: Optional[int] = None
    department_id: Optional[int] = None
    section: Optional[str] = None
    rating: int
    message: str
    status: str
    response: Optional[str] = None
    author_name: Optional[str] = None
    subject_name: Optional[str] = None
    created_at: str
