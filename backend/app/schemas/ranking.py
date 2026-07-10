from typing import Any

from pydantic import BaseModel, Field


class RankCandidatesRequest(BaseModel):
    jd: dict[str, Any]
    candidates: list[dict[str, Any]]


class RerankShortlistRequest(BaseModel):
    jd: dict[str, Any]
    batch_rankings: dict[str, Any]
    candidates: list[dict[str, Any]]
    top_n: int = Field(default=10, ge=1)


class ProfileGapRequest(BaseModel):
    jd: dict[str, Any]
    candidate: dict[str, Any]
    target_role: str | None = None


class SaveRankingsRequest(BaseModel):
    rankings: dict[str, Any]
    run_name: str = "API screening run"
    source_file: str = "api_payload"


class HealthResponse(BaseModel):
    status: str
    service: str


class RankCandidatesResponse(BaseModel):
    job_title: str | None
    ranking_rule: str
    summary: list[dict[str, Any]]
    results: list[dict[str, Any]]


class RerankShortlistResponse(BaseModel):
    job_title: str | None
    ranking_rule: str
    shortlist_size: int
    summary: list[dict[str, Any]]
    results: list[dict[str, Any]]


class ProfileGapResponse(BaseModel):
    target_role: str | None
    candidate_name: str
    current_fit: str
    role_readiness_score: float | int | None
    eligibility: dict[str, Any]
    qualification_gaps: dict[str, Any]
    recommended_actions: dict[str, Any]
    evidence: dict[str, Any]


class SaveRankingsResponse(BaseModel):
    run_id: int
    saved_rankings: int


class UploadRankCandidatesResponse(RankCandidatesResponse):
    parse_failures: list[dict[str, Any]] = []


class ParseUploadResponse(BaseModel):
    jd: dict[str, Any]
    candidates: list[dict[str, Any]]
    failures: list[dict[str, Any]] = []
