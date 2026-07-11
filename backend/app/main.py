import os
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
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
from backend.app.schemas.jobs import JobSearchResponse
from backend.app.schemas.pipeline import (
    PipelineResumeRequest,
    PipelineResumeResponse,
    PipelineRunRequest,
    PipelineRunResponse,
)
from backend.app.schemas.ranking import (
    HealthResponse,
    ParseUploadResponse,
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
from backend.app.services.job_search_service import search_jobs as search_jobs_service
from backend.app.services.profile_gap_service import analyze_profile_gap
from backend.app.services.ranking_service import rank_candidates_for_jd
from backend.app.services.reranking_service import rerank_shortlist_for_jd
from backend.app.services.resume_intake_service import (
    parse_jd_upload,
    parse_resumes_batch,
)


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
def search_jobs(query: str, location: str | None = None, country: str = "us", page: int = 1):
    return search_jobs_service(query=query, location=location, country=country, page=page)


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
