import os
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command

from backend.app.pipeline.ranking_graph import (
    apply_review_decision,
    extract_interrupt_payload,
    pipeline_graph,
)
from backend.app.pipeline_review_repository import (
    get_pending_review,
    mark_review_resolved,
    save_pending_review,
)
from backend.app.candidate_job_events_repository import get_my_jobs, log_event
from backend.app.schemas.jobs import JobEventRequest, JobEventResponse, JobSearchResponse, MyJobsResponse
from backend.app.schemas.pipeline import (
    PipelineResumeRequest,
    PipelineResumeResponse,
    PipelineRunRequest,
    PipelineRunResponse,
)
from backend.app.schemas.ranking import (
    HealthResponse,
    ParseUploadJobResponse,
    ParseUploadResponse,
    ParseUploadStatusResponse,
    ProfileGapRequest,
    ProfileGapResponse,
    RankCandidatesRequest,
    RankCandidatesResponse,
    RerankShortlistRequest,
    RerankShortlistResponse,
    SaveRankingsRequest,
    SaveRankingsResponse,
    UploadRankCandidatesResponse,
)
from backend.app.services.job_search_service import log_searched_event_safely
from backend.app.services.job_search_service import search_jobs as search_jobs_service
from backend.app.services.profile_gap_service import analyze_profile_gap
from backend.app.services.ranking_service import rank_candidates_for_jd
from backend.app.services.reranking_service import rerank_shortlist_for_jd
from backend.app.services.resume_intake_service import (
    parse_jd_upload,
    parse_resumes_batch,
)
from backend.app.upload_progress import complete_job, create_job, fail_job, get_job, update_progress


app = FastAPI(
    title="AI Talent Intelligence Platform API",
    description="Backend API for recruiter ranking and job seeker qualification-gap analysis.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGIN", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "ok",
        "service": "ai-talent-intelligence-api",
    }


@app.post("/rank-candidates", response_model=RankCandidatesResponse)
def rank_candidates(request: RankCandidatesRequest):
    return rank_candidates_for_jd(
        jd=request.jd,
        candidates=request.candidates,
    )


@app.post("/rerank-shortlist", response_model=RerankShortlistResponse)
def rerank_shortlist(request: RerankShortlistRequest):
    return rerank_shortlist_for_jd(
        jd=request.jd,
        batch_rankings=request.batch_rankings,
        candidates=request.candidates,
        top_n=request.top_n,
    )


@app.get("/jobs/search", response_model=JobSearchResponse)
def search_jobs(
    background_tasks: BackgroundTasks,
    query: str = "",
    location: str | None = None,
    country: str = "us",
    candidate_id: str | None = None,
):
    try:
        result = search_jobs_service(query=query, location=location, country=country, candidate_id=candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if candidate_id:
        # Deferred until after the response is sent - a synchronous DB write here
        # previously added a real remote-DB round trip to every search request.
        background_tasks.add_task(log_searched_event_safely, candidate_id, result["used_query"])

    return result


@app.post("/jobs/events", response_model=JobEventResponse)
def log_job_event(request: JobEventRequest):
    log_event(
        request.candidate_id,
        request.event_type,
        job_source=request.job_source,
        job_external_id=request.job_external_id,
        job_title=request.job_title,
        company=request.company,
        location=request.location,
        job_url=request.job_url,
    )
    return JobEventResponse()


@app.get("/jobs/my-jobs", response_model=MyJobsResponse)
def my_jobs(candidate_id: str):
    return get_my_jobs(candidate_id)


@app.post("/analyze-profile-gap", response_model=ProfileGapResponse)
def profile_gap(request: ProfileGapRequest):
    return analyze_profile_gap(
        jd=request.jd,
        candidate=request.candidate,
        target_role=request.target_role,
    )


@app.post("/save-rankings", response_model=SaveRankingsResponse)
def save_rankings(request: SaveRankingsRequest):
    from backend.app.services.persistence_service import save_rankings_payload

    return save_rankings_payload(
        rankings=request.rankings,
        run_name=request.run_name,
        source_file=request.source_file,
    )


@app.post("/upload/rank-candidates", response_model=UploadRankCandidatesResponse)
async def upload_rank_candidates(
    jd_file: UploadFile = File(...),
    resume_files: list[UploadFile] = File(...),
):
    jd_content = await jd_file.read()
    try:
        jd = parse_jd_upload(jd_content, jd_file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    files = [(await resume_file.read(), resume_file.filename) for resume_file in resume_files]
    batch = parse_resumes_batch(files)

    if not batch["candidates"]:
        raise HTTPException(
            status_code=422,
            detail={"message": "No resumes could be parsed.", "failures": batch["failures"]},
        )

    ranking = rank_candidates_for_jd(jd=jd, candidates=batch["candidates"])
    ranking["parse_failures"] = batch["failures"]
    return ranking


@app.post("/upload/parse", response_model=ParseUploadResponse)
async def upload_parse(
    jd_file: UploadFile = File(...),
    resume_files: list[UploadFile] = File(...),
):
    jd_content = await jd_file.read()
    try:
        jd = parse_jd_upload(jd_content, jd_file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    files = [(await resume_file.read(), resume_file.filename) for resume_file in resume_files]
    batch = parse_resumes_batch(files)

    if not batch["candidates"]:
        raise HTTPException(
            status_code=422,
            detail={"message": "No resumes could be parsed.", "failures": batch["failures"]},
        )

    return {"jd": jd, "candidates": batch["candidates"], "failures": batch["failures"]}


@app.post("/upload/parse/start", response_model=ParseUploadJobResponse)
async def start_upload_parse(
    background_tasks: BackgroundTasks,
    jd_file: UploadFile = File(...),
    resume_files: list[UploadFile] = File(...),
):
    jd_content = await jd_file.read()
    jd_filename = jd_file.filename
    files = [(await resume_file.read(), resume_file.filename) for resume_file in resume_files]

    job_id = create_job(total=len(files))

    def run_job():
        try:
            jd = parse_jd_upload(jd_content, jd_filename)
        except ValueError as exc:
            fail_job(job_id, str(exc))
            return

        batch = parse_resumes_batch(
            files,
            on_progress=lambda **kwargs: update_progress(job_id, **kwargs),
        )

        if not batch["candidates"]:
            fail_job(job_id, "No resumes could be parsed.")
            return

        complete_job(job_id, {"jd": jd, "candidates": batch["candidates"], "failures": batch["failures"]})

    # Starlette runs sync background callables in a worker thread, so this heavy
    # Docling/Gemini work no longer blocks the event loop the way the original
    # synchronous /upload/parse route did - /upload/parse/status stays responsive
    # while it runs.
    background_tasks.add_task(run_job)
    return ParseUploadJobResponse(job_id=job_id, total=len(files))


@app.get("/upload/parse/status/{job_id}", response_model=ParseUploadStatusResponse)
def get_upload_parse_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No upload job found for '{job_id}'.")

    result = job.get("result") or {}
    return ParseUploadStatusResponse(
        status=job["status"],
        total=job["total"],
        processed=job["processed"],
        current_filename=job["current_filename"],
        failures=result.get("failures", []),
        error=job.get("error"),
        jd=result.get("jd"),
        candidates=result.get("candidates"),
    )


@app.post("/pipeline/run", response_model=PipelineRunResponse)
def run_pipeline(request: PipelineRunRequest):
    thread_id = request.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = pipeline_graph.invoke(
        {
            "jd": request.jd,
            "candidates": request.candidates,
            "run_name": request.run_name,
            "source_file": request.source_file,
            "top_n": request.top_n,
        },
        config=config,
    )

    review_payload = extract_interrupt_payload(result)
    if review_payload is not None:
        # Persisted *before* returning to the caller, so approve/reject/edit
        # works whether it happens 10 seconds or 10 hours later - resume reads
        # this row, not the in-memory LangGraph checkpoint (which won't survive
        # a process restart/redeploy).
        save_pending_review(
            thread_id=thread_id,
            jd=request.jd,
            candidates=request.candidates,
            batch_ranking=result.get("batch_ranking"),
            reranked=result.get("reranked"),
            run_name=request.run_name,
            source_file=request.source_file,
            top_n=request.top_n,
        )
        return PipelineRunResponse(
            thread_id=thread_id,
            status="awaiting_review",
            batch_ranking=result.get("batch_ranking"),
            review_payload=review_payload,
        )

    return PipelineRunResponse(
        thread_id=thread_id,
        status=result.get("status", "no_eligible_candidates"),
        batch_ranking=result.get("batch_ranking"),
    )


@app.post("/pipeline/resume", response_model=PipelineResumeResponse)
def resume_pipeline(request: PipelineResumeRequest):
    from backend.app.services.persistence_service import save_rankings_payload

    config = {"configurable": {"thread_id": request.thread_id}}
    decision = {
        "action": request.action,
        "manual_additions": [addition.model_dump() for addition in request.manual_additions],
        "edited_results": request.edited_results,
        "reviewer": request.reviewer,
        "notes": request.notes,
    }

    # Fast path: the in-memory LangGraph checkpoint is still alive (no process
    # restart/redeploy since /pipeline/run) - resume through the graph directly
    # and skip the MySQL read entirely. get_state() is a non-destructive check;
    # a non-empty `next` means this thread is genuinely paused at the interrupt.
    if pipeline_graph.get_state(config).next:
        result = pipeline_graph.invoke(Command(resume=decision), config=config)
        status = result.get("status", "rejected")
        mark_review_resolved(request.thread_id, status)
        return PipelineResumeResponse(
            thread_id=request.thread_id,
            status=status,
            reranked=result.get("reranked"),
            persistence_result=result.get("persistence_result"),
        )

    # Durable fallback: the checkpoint is gone (process restart/redeploy, or
    # this thread was already resolved) - read the pending state persisted to
    # MySQL at /pipeline/run time instead.
    pending = get_pending_review(request.thread_id)
    if pending is None:
        raise HTTPException(status_code=404, detail=f"No pending review found for thread_id '{request.thread_id}'.")
    if pending["status"] != "awaiting_review":
        raise HTTPException(
            status_code=409,
            detail=f"Review for thread_id '{request.thread_id}' was already resolved as '{pending['status']}'.",
        )

    if request.action not in ("approve", "edit"):
        mark_review_resolved(request.thread_id, "rejected")
        return PipelineResumeResponse(thread_id=request.thread_id, status="rejected", reranked=None, persistence_result=None)

    reranked = apply_review_decision(pending["reranked"], pending["batch_ranking"], decision)
    persistence_result = save_rankings_payload(
        rankings=reranked,
        run_name=pending["run_name"] or "LangGraph pipeline run",
        source_file=pending["source_file"] or "langgraph_pipeline",
    )
    mark_review_resolved(request.thread_id, "persisted")

    return PipelineResumeResponse(
        thread_id=request.thread_id,
        status="persisted",
        reranked=reranked,
        persistence_result=persistence_result,
    )
