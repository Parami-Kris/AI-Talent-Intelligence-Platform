"""In-memory progress tracking for the resume-parsing upload step.

Deliberately not persisted anywhere durable (unlike pipeline_review_repository's
MySQL-backed review state): this only exists so the frontend can poll "how many
resumes are done" while a single Docling/Gemini parse batch is in flight. It does
not need to survive a process restart the way an hours-long human review does.
"""

import threading
from typing import Any
from uuid import uuid4

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def create_job(total: int) -> str:
    job_id = str(uuid4())
    with _lock:
        _jobs[job_id] = {
            "status": "running",
            "total": total,
            "processed": 0,
            "current_filename": None,
            "failures": [],
            "result": None,
            "error": None,
        }
    return job_id


def update_progress(
    job_id: str,
    *,
    current_filename: str | None = None,
    processed_increment: bool = False,
) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        if current_filename is not None:
            job["current_filename"] = current_filename
        if processed_increment:
            job["processed"] += 1


def complete_job(job_id: str, result: dict[str, Any]) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job["status"] = "done"
        job["current_filename"] = None
        job["result"] = result


def fail_job(job_id: str, error: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job["status"] = "error"
        job["current_filename"] = None
        job["error"] = error


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job is not None else None
