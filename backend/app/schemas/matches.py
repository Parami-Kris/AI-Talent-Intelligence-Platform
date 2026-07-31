from typing import Any

from pydantic import BaseModel


class JobMatchResult(BaseModel):
    source: str
    id: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    url: str | None = None
    posted_at: str | None = None
    match_percentage: int | None = None
    match_reason: str | None = None


class JobMatchesResponse(BaseModel):
    results: list[JobMatchResult]
    quota_remaining_today: int


class TailorResumeRequest(BaseModel):
    jd: dict[str, Any]
    candidate: dict[str, Any]
    target_role: str | None = None


class TailorResumeResponse(BaseModel):
    tailored_resume_text: str | None = None
    summary_of_changes: list[str] = []
