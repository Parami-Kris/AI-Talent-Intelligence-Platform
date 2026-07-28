from typing import Any

from pydantic import BaseModel


class SaveResumeRequest(BaseModel):
    resume_filename: str
    parsed_resume: dict[str, Any]


class ResumeResponse(BaseModel):
    resume_filename: str | None = None
    parsed_resume: dict[str, Any] | None = None
    updated_at: str | None = None
