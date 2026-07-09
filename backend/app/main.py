from fastapi import FastAPI, File, HTTPException, UploadFile

from backend.app.schemas.ranking import (
    ProfileGapRequest,
    RankCandidatesRequest,
    RerankShortlistRequest,
    SaveRankingsRequest,
)
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


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ai-talent-intelligence-api",
    }


@app.post("/rank-candidates")
def rank_candidates(request: RankCandidatesRequest):
    return rank_candidates_for_jd(
        jd=request.jd,
        candidates=request.candidates,
    )


@app.post("/rerank-shortlist")
def rerank_shortlist(request: RerankShortlistRequest):
    return rerank_shortlist_for_jd(
        jd=request.jd,
        batch_rankings=request.batch_rankings,
        candidates=request.candidates,
        top_n=request.top_n,
    )


@app.post("/analyze-profile-gap")
def profile_gap(request: ProfileGapRequest):
    return analyze_profile_gap(
        jd=request.jd,
        candidate=request.candidate,
        target_role=request.target_role,
    )


@app.post("/save-rankings")
def save_rankings(request: SaveRankingsRequest):
    from backend.app.services.persistence_service import save_rankings_payload

    return save_rankings_payload(
        rankings=request.rankings,
        run_name=request.run_name,
        source_file=request.source_file,
    )


@app.post("/upload/rank-candidates")
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
