from typing import Any, Literal

from pydantic import BaseModel, Field


class PipelineRunRequest(BaseModel):
    jd: dict[str, Any]
    candidates: list[dict[str, Any]]
    run_name: str = "LangGraph pipeline run"
    source_file: str = "langgraph_pipeline"
    top_n: int = Field(default=10, ge=1)
    thread_id: str | None = None


class PipelineRunResponse(BaseModel):
    thread_id: str
    status: Literal["awaiting_review", "no_eligible_candidates"]
    batch_ranking: dict[str, Any] | None = None
    review_payload: dict[str, Any] | None = None


class ManualAddition(BaseModel):
    candidate_name: str
    override_reason: str = Field(min_length=1)
    added_by: str | None = None


class PipelineResumeRequest(BaseModel):
    thread_id: str
    action: Literal["approve", "edit", "reject"]
    manual_additions: list[ManualAddition] = []
    edited_results: list[dict[str, Any]] | None = None
    reviewer: str | None = None
    notes: str | None = None


class PipelineResumeResponse(BaseModel):
    thread_id: str
    status: Literal["persisted", "rejected"]
    reranked: dict[str, Any] | None = None
    persistence_result: dict[str, Any] | None = None
