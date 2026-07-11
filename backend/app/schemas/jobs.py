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
