from typing import Literal

from pydantic import BaseModel


class JobSearchResult(BaseModel):
    source: str
    id: str
    title: str | None
    company: str | None
    location: str | None
    description: str | None
    url: str | None
    posted_at: str | None


class JobSearchResponse(BaseModel):
    count: int
    results: list[JobSearchResult]
    expanded_titles: list[str] = []
    used_query: str = ""
    recommended: bool = False


class JobEventRequest(BaseModel):
    candidate_id: str
    event_type: Literal["viewed", "applied", "liked"]
    job_source: str | None = None
    job_external_id: str | None = None
    job_title: str | None = None
    company: str | None = None
    location: str | None = None
    job_url: str | None = None


class JobEventResponse(BaseModel):
    status: str = "ok"


class MyJobEntry(BaseModel):
    source: str | None
    id: str | None
    title: str | None
    company: str | None
    location: str | None
    url: str | None
    created_at: str | None


class MyJobsResponse(BaseModel):
    liked: list[MyJobEntry]
    applied: list[MyJobEntry]
