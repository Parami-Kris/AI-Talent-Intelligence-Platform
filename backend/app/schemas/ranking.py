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
