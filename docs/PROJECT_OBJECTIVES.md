# AI Talent Intelligence Platform - Objectives and Progress

## Purpose

Build an end-to-end AI recruiting and career intelligence platform that is strong enough for an MSc Advanced AI portfolio and a LinkedIn/GitHub project showcase.

The project should not be just a prompt-based resume scorer. The target is a practical web product that combines document parsing, structured extraction, deterministic checks, LLM reasoning, database persistence, explainability, and eventually a recruiter/student-facing interface.

## Positioning

Portfolio story:

> An AI Talent Intelligence Platform that parses resumes and job descriptions, ranks candidates with evidence-backed scoring, separates hard eligibility from similarity, stores screening runs in MySQL, and helps both recruiters and job seekers make better career decisions through explainable AI workflows.

This should demonstrate:

- applied LLM engineering
- information extraction
- backend/API design
- MySQL database design
- ranking and reranking pipelines
- explainable AI thinking
- end-to-end product development

## Current Tech Direction

### Frontend

Current:

- Vite + React + TypeScript (`web-app/`) for the recruiter dashboard
- TailwindCSS

Planned:

- Recharts or Chart.js for analytics, once there's an analytics view to build

### Backend

Current/planned:

- Python
- FastAPI
- REST APIs
- modular services

### AI/NLP Layer

Current:

- Docling for PDF/text extraction
- Gemini via Google Gen AI SDK (`gemini-3.1-flash-lite` — switched from `gemini-2.5-flash`, which has a much tighter 20/day free quota vs. 500/day) for structured parsing and reasoning
- deterministic skill overlap and eligibility checks
- LLM-based shortlist reranking
- Groq (`llama-3.1-8b-instant`) for job-search related-title query expansion — a separate provider from Gemini specifically so it doesn't compete for Gemini's tighter quota

Potential later additions:

- sentence-transformers for embeddings
- RAG for evidence retrieval and recruiter Q&A
- clustering for talent segmentation
- SHAP or simpler contribution explanations for explainability

### Database

Chosen:

- MySQL

Reason:

- aligns with existing user expertise
- useful for recruiter-facing product persistence
- easier to explain confidently in interviews

Hosting: Aiven (production, current HF Space secrets) — being migrated to **TiDB Cloud Starter** (MySQL-compatible, no code changes needed) because Aiven's free tier auto-powers-off after a period of inactivity, which would hard-fail the app's persistence layer (rankings, pipeline review flow) if someone opens the deployed app while the DB is asleep. Schema is already created and verified working on TiDB (`ai-screening-db`); production secrets haven't been switched over yet. TiDB's own inactivity behavior isn't fully confirmed by docs (no documented auto-delete/pause policy found for the Starter tier, unlike Aiven's explicitly documented one) — worth revisiting after a few days of real-world idle time to confirm.

Not chosen for now:

- PostgreSQL/pgvector

Reason:

- useful later for vector search, but not necessary for the current platform foundation
- MySQL is a better fit for the user's current strengths

### Deployment

Chosen:

- frontend: GitHub Pages (`web-app/`), auto-deployed via `.github/workflows/deploy-web-app.yml` on push to `main`
- backend: Hugging Face Spaces (Docker SDK) — tried Render first, but its free tier's 512MB RAM / 0.1 CPU can't reliably run Docling's dependency chain (`torch`/`transformers`/`docling-ibm-models`); HF Spaces' free CPU tier has much more headroom and doesn't require a card on file

Not chosen:

- Render for the backend — kept `render.yaml` in the repo in case a paid tier is worth it later, but not the current path
- Docker Compose for local dev — not needed yet; local dev runs backend/frontend directly, only the HF Spaces deploy is containerized

AWS is optional and not required for the first strong demo.

## Product Scope

### Product Vision

The platform should become similar in spirit to a lightweight LinkedIn Premium-style intelligence layer:

- recruiters can identify and compare suitable candidates
- job seekers can understand how their profile fits a target role
- users can see what skills, experience, projects, or credentials they still need to become qualified
- recommendations should be evidence-backed rather than generic career advice

The goal is not to clone LinkedIn. The goal is to build a focused AI career intelligence product around resume/JD understanding, qualification gaps, and explainable matching.

### Recruiter Dashboard

Planned features:

- upload one job description
- upload multiple resumes
- choose ranking strategy
- view ranked candidate table
- inspect candidate detail page
- see matched skills, missing must-haves, experience evidence, education evidence
- compare candidates
- export results

Ranking strategy ideas:

- balanced
- skills-first
- experience-first
- education-first
- impressive-profile

### Candidate Detail Page

Should show:

- final rank
- overall score
- eligibility status
- missing must-haves
- skill evidence
- experience years
- experience relevance
- education match
- strengths
- weaknesses
- audit trail of why the candidate was ranked that way

### Student Dashboard

Also called the job seeker dashboard.

Planned features:

- upload own resume
- paste a job description
- get match score and skill gaps
- get role suggestions
- get career advisor recommendations
- compare resume skills against market demand
- see what else the profile needs to qualify for a specific role
- receive missing must-have skills
- receive missing experience signals
- receive suggested projects to prove missing skills
- receive resume improvement recommendations
- receive learning roadmap suggestions

Example target-role output:

```json
{
  "target_role": "Machine Learning Engineer",
  "current_fit": "partial",
  "qualification_gaps": {
    "missing_required_skills": ["Docker", "Model Deployment", "AWS"],
    "missing_experience_signals": ["production ML deployment", "monitoring deployed models"],
    "missing_project_evidence": ["end-to-end deployed ML project"]
  },
  "recommended_actions": [
    "Build and deploy one ML model with FastAPI and Docker",
    "Add model monitoring or evaluation metrics to a project",
    "Rewrite resume bullets to show deployment and production ownership"
  ]
}
```

This becomes a second mode of the same platform after the recruiter workflow is stable, but it should be part of the main product vision from the start.

### Profile Qualification Analyzer

This feature answers:

> What else does my profile need to have to qualify for this specific role?

Inputs:

- candidate resume/profile
- target job description
- optional target role title

Outputs:

- current fit level
- missing must-have skills
- missing preferred skills
- missing years/seniority signals
- missing project evidence
- missing domain experience
- suggested projects
- suggested resume bullet improvements
- suggested learning roadmap

This feature reuses the same matching engine, but changes the framing:

- recruiter mode ranks candidates for a job
- job seeker mode explains how one candidate can become stronger for a job

## AI Pipeline

Current and planned pipeline:

```text
Resume PDFs
  -> text extraction
  -> structured resume parsing
  -> skill normalization
  -> candidate profile JSON
  -> MySQL persistence

Job description
  -> structured JD parsing
  -> required/preferred skills
  -> responsibilities
  -> experience and education requirements

Candidate profiles + JD
  -> deterministic eligibility and score checks
  -> batch ranking
  -> shortlist selection
  -> LLM experience relevance reranking
  -> human review checkpoint (recruiter approves, edits, or rejects; can
     manually add a non-shortlisted candidate with a justification)
  -> final rankings
  -> database storage
  -> web dashboard

Candidate profile + target role/JD
  -> qualification gap analysis
  -> missing must-have detection
  -> missing evidence detection
  -> project and learning recommendations
  -> job seeker dashboard
```

## Design Principles

1. Eligibility is not similarity.

   A candidate can have many overlapping skills but still fail a hard requirement such as years of experience or required must-have skills.

2. Required skills are must-haves.

   The project currently treats `required_skills` as hard requirements.

3. Every score needs evidence.

   Scores should include matched items, missing items, and evidence from the resume/JD.

4. LLMs should be used where judgment is needed.

   Deterministic logic should handle cheap checks such as skill overlap and experience years. LLMs should handle nuanced comparison, parsing, and relevance reasoning.

5. The system should support human review.

   The platform should assist recruiters, not become an opaque automatic rejection machine.

6. Avoid decorative AI.

   RAG, embeddings, clustering, and explainability should be added only when they serve a real product purpose.

## What Is Already Done

### Resume and JD parsing

Implemented:

- `pipeline/parser.py`
- `pipeline/llm_parser.py`
- `pipeline/jd_parser.py`
- `candidate_profiles.json`
- `parsed_jd.json`

Current capabilities:

- extract resume text from PDF
- parse resume into structured JSON
- parse JD into structured JSON
- normalize skills using LLM prompt instructions

### Single candidate matching

Implemented:

- `pipeline/matcher.py`
- `match_analysis.json`

Current capabilities:

- skill match score
- education match
- experience match
- overall score
- eligibility object
- matched/missing/evidence for scores
- separation of eligibility from similarity

### Batch ranking

Implemented:

- `synthetic_candidates.json`
- `pipeline/batch_ranker.py`
- `batch_rankings.json`

Current capabilities:

- ranks multiple candidates against one JD
- deterministic skill scoring
- deterministic experience years pre-check
- batched education matching when education requirement exists
- local short-circuit when education is not specified

### Shortlist reranking

Implemented:

- `pipeline/shortlist_reranker.py`
- `final_rankings.json`

Current capabilities:

- reads first-pass batch results
- selects top N candidates
- uses one batched LLM call to judge experience relevance
- produces final rank and final score
- catches cases where years are present but domain relevance is weak

### LangGraph human-in-the-loop pipeline

Implemented:

- `backend/app/pipeline/ranking_graph.py`
- `backend/app/schemas/pipeline.py`
- `POST /pipeline/run`, `POST /pipeline/resume`

Current capabilities:

- explicit `StateGraph` orchestrating the existing rank -> rerank -> persist services (no ranking logic reimplemented)
- conditional edge that skips reranking/persistence entirely when zero candidates are eligible
- human-in-the-loop interrupt before persistence: a recruiter can `approve` the shortlist as-is, `reject` the run, or `edit` it
- editing supports `manual_additions` — flagging a candidate who wasn't LLM-shortlisted (e.g. one who interviewed well but whose resume underrepresented them) with a required `override_reason`, so the persisted record still carries evidence for the override
- `/pipeline/run` uses LangGraph's `interrupt()` to pause for review, but resume is durable: the moment the interrupt fires, the full pending state (JD, candidates, batch ranking, reranked shortlist) is persisted to a `pipeline_reviews` MySQL table (`backend/app/pipeline_review_repository.py`) *before* the response is returned. `/pipeline/resume` reads from that table — not from LangGraph's in-memory checkpoint — so approve/edit/reject works correctly whether it happens seconds or hours later, and survives a full backend process restart (verified manually: killed the process mid-review, restarted it, resumed successfully against the same `thread_id`). The decision-application logic (`apply_review_decision`) is a pure function shared between the graph's own `human_review_node` and the durable resume route, so there's one source of truth for the manual-add/edit behavior either way.
- additive: `/rank-candidates`, `/rerank-shortlist`, `/save-rankings` are unchanged

### MySQL foundation

Implemented:

- `backend/schema.sql`
- `backend/app/db.py`
- `backend/app/ranking_repository.py`
- `setup_mysql.py`
- `pipeline/save_rankings_to_mysql.py`
- `.env.example`

Current capabilities:

- create MySQL database/tables
- store screening runs
- store candidates
- store candidate rankings
- store evidence rows
- keep full ranking JSON for audit/debugging
- cache job-search query expansions (`query_expansions` table)

### FastAPI backend

Implemented:

- `backend/app/main.py`
- `backend/app/schemas/ranking.py`
- `backend/app/services/ranking_service.py`
- `backend/app/services/reranking_service.py`
- `backend/app/services/profile_gap_service.py`
- `backend/app/services/persistence_service.py`
- `backend/app/services/input_service.py`
- `backend/app/services/resume_intake_service.py`

Current capabilities:

- `GET /health`
- `POST /rank-candidates` (batch ranking over pre-parsed JSON)
- `POST /rerank-shortlist` (LLM shortlist reranking)
- `POST /analyze-profile-gap` (job seeker qualification-gap analysis)
- `POST /save-rankings` (persist a ranking payload to MySQL)
- `POST /upload/rank-candidates` (multipart upload: one JD file + multiple resume files, parses each via Docling/Gemini, ranks the batch, and reports per-resume parse failures without stopping the batch)
- `POST /pipeline/run` / `POST /pipeline/resume` (LangGraph human-in-the-loop pipeline, see above)
- `GET /jobs/search` (job seeker "search real jobs" feature — SerpApi primary, Bright Data Web Unlocker fallback, Groq-based related-title query expansion; see below)
- every route now declares a Pydantic `response_model` (`backend/app/schemas/ranking.py`, `backend/app/schemas/pipeline.py`), not plain dicts

### Job search (job seeker "search real jobs")

Implemented:

- `backend/app/services/job_search_service.py`
- `backend/app/query_expansion_repository.py`
- `backend/app/schemas/jobs.py`
- `web-app/src/features/job-seeker/JobSearchResultsPage.tsx` (Indeed-style list/detail page), `JobFitCheck.tsx` (per-job "analyze your fit" using only a resume, no JD upload needed since the job's own description is used)

Current capabilities:

- searches SerpApi's Google Jobs engine first (full descriptions, direct apply links); automatically falls back to Bright Data (Web Unlocker product, HTML-parsed) if SerpApi fails or its free-tier quota (250/month) is exhausted — Bright Data also returns full descriptions once you know the right target (`udm=8` jobs-vertical param, not the deprecated `ibp=htl;jobs`)
- Groq generates up to 3 related job titles per query (e.g. "ML Engineer" also searches "Applied Scientist") and fans out the search across all of them, merging/deduping results; expansions are cached in a MySQL `query_expansions` table so repeat searches don't re-call Groq
- rejected sources, documented so they aren't re-investigated: Adzuna/Jooble (hard ~300-500 char description truncation, no API-level fix), Remotive (full descriptions but remote-jobs-only, dropped for narrower coverage), LinkedIn scraping including Bright Data's own LinkedIn dataset product (declined — ToS/legal risk), JobsPipe (worse free tier than SerpApi, requires a card)

### Malformed LLM JSON handling

Implemented:

- `backend/app/utils/llm_json.py::parse_llm_json` — shared strip-fences + try/except + `{"error", "raw_response"}` pattern (previously only `llm_parser.extract_structured_resume` had this)
- `jd_parser.extract_structured_jd` now returns `{"error": ..., "raw_response": ...}` on failure instead of a bare `{}`, and `resume_intake_service.parse_jd_upload` surfaces that error the same way the resume path already did
- `matcher.education_match` / `experience_match` / `analyze_match` no longer raise an uncaught `JSONDecodeError` on malformed output
- `batch_ranker.batch_education_match` and `shortlist_reranker.rerank_experience_relevance` — the two functions actually on the live `/rank-candidates` and `/rerank-shortlist` paths — degrade gracefully on a parse failure (fall back to "not evaluated" stubs / first-pass score carried forward) instead of 500ing the whole request

### Automated tests

Implemented:

- `tests/` (pytest) covering parser, matcher, batch ranker, shortlist reranker, input service, resume intake service, the LangGraph pipeline, and every FastAPI route (including response-model validation)
- `conftest.py` at repo root so tests can import the top-level scripts as modules
- `tests/_fakes.py` — a small fake Gemini client/response pair (no new mocking dependency) used to test the Gemini-calling functions without hitting the real API
- Gemini-calling functions now have success + malformed-JSON test coverage: `education_match`, `experience_match`, `analyze_match`, `extract_structured_jd`, `batch_education_match`, `rerank_experience_relevance`

## Current Completion Estimate

Approximate status: 60-70%.

The project has a working AI pipeline prototype (including a LangGraph-orchestrated, human-in-the-loop pipeline), a FastAPI backend with typed request/response schemas, malformed-LLM-JSON handling, initial persistence, a test suite that now covers the Gemini-calling code paths, and the recruiter dashboard, job seeker qualification-gap dashboard, and job seeker "search real jobs" feature all live in `web-app/` (deployed to GitHub Pages, backend on Hugging Face Spaces). It is not yet a complete product.

Major missing pieces:

- candidate comparison view and result export (recruiter dashboard)
- further UI/UX polish
- evaluation/benchmarking against a labeled dataset
- documentation and demo assets
- MySQL production hosting migration from Aiven to TiDB Cloud (schema ready, HF secrets not yet switched)

## Known Issues

- (Resolved) The repo previously had no commits. It now has an initial commit and is pushed to `https://github.com/Parami-Kris/AI-Talent-Intelligence-Platform`.
- (Resolved) The LangGraph pipeline's resume step used to depend on an in-memory checkpointer that wouldn't survive a process restart. Fixed via a durable `pipeline_reviews` MySQL table — see the LangGraph section above.
- (Resolved) Render's free tier couldn't run the backend — Docling's dependency chain (`torch`/`transformers`/`docling-ibm-models`) is too heavy for its 512MB RAM / 0.1 CPU, causing either OOM kills or startup timeouts. Moved backend hosting to Hugging Face Spaces (Docker SDK), which has much more headroom on its free CPU tier.
- (In progress) Aiven's free-tier MySQL auto-powers-off after inactivity, which would hard-fail the app's core persistence (not just the job-search cache, which degrades gracefully) if hit while asleep. Migrating to TiDB Cloud Starter — schema verified working there, production secrets not yet switched.

## Next Engineering Tasks

### Phase 1 - Backend foundation (done)

Goal: turn scripts into backend services without breaking current scripts.

Done:

- FastAPI app with health, ranking, reranking, profile-gap, persistence, upload, and LangGraph pipeline endpoints
- ranking logic in service modules
- request and response schemas (Pydantic)
- connected to the MySQL repository layer
- shared malformed-LLM-JSON error handling (`pipeline/jd_parser.py`, `pipeline/matcher.py`, `pipeline/batch_ranker.py`, `pipeline/shortlist_reranker.py`)
- mocked test coverage for the Gemini-calling functions

### Phase 2 - Multi-resume ingestion (mostly done)

Goal: support real batches instead of only synthetic JSON.

Done:

- `POST /upload/rank-candidates` accepts a JD file plus multiple resume files (PDF/DOCX/TXT via Docling)
- parses each resume independently and reports failures without stopping the batch
- reuses `pipeline/parser.py` / `pipeline/llm_parser.py` / `pipeline/jd_parser.py` for extraction

Still open:

- a CLI equivalent (`parse_resumes_folder.py`) for local/offline batch parsing of a folder of PDFs
- store parsed candidates (not just rankings) in MySQL

### Phase 3 - Web app (done)

Goal: build a recruiter-facing interface first, then extend it into a job seeker interface.

Done:

- React (Vite + TypeScript) frontend, deployed to GitHub Pages
- upload JD / upload resumes / run ranking / show ranking table (card and table views)
- candidate detail drawer, evidence and missing must-haves
- final reranking result and human review flow

Job seeker mode (done):

- upload own resume, with a paste-text-or-upload-file toggle for the JD
- qualification gaps, missing must-haves, suggested projects, resume improvement recommendations, role-readiness score
- route at `/job-seeker`, reachable from the main nav

### Phase 4 - Explainability and evaluation

Goal: make it credible as an Advanced AI project.

Tasks:

- create synthetic benchmark scenarios
- compare first-pass ranking vs reranked output
- document failure cases
- add score contribution view
- add fairness/human-review limitations
- optionally add clustering visualization

### Phase 5 - RAG and embeddings, only if useful

Potential useful RAG features:

- retrieve exact resume evidence chunks behind a score
- recruiter Q&A over candidates
- job seeker Q&A over profile gaps
- skill ontology retrieval instead of hardcoded aliases

Avoid adding RAG only for buzzwords.

### Phase 6 - Docker and deployment

Goal: make the project reproducible and demo-friendly.

Tasks:

- Dockerfile for backend
- Docker Compose for backend + MySQL
- frontend Docker or Vercel deployment
- optional hosted backend if free/affordable

## Near-Term Priority

Phases 1-3 are done: the FastAPI backend foundation, file-upload ingestion, and the web app (recruiter dashboard plus job seeker qualification-gap dashboard, both deployed live). The immediate next best step is:

> Phase 4 - explainability and evaluation: build a small labeled benchmark set and compare first-pass vs. reranked output, to make the ranking quality claims credible rather than anecdotal.

## Notes for Recruiter/LinkedIn Positioning

Avoid presenting the project as:

> I used Gemini to score resumes.

Present it as:

> I built an end-to-end AI Talent Intelligence Platform with document parsing, structured resume/JD extraction, deterministic eligibility checks, evidence-backed ranking, a LangGraph-orchestrated ranking pipeline with a human-in-the-loop review checkpoint, job seeker qualification-gap analysis, LLM-based shortlist reranking, MySQL persistence, and planned recruiter/job-seeker dashboards.

Possible resume bullet:

> Built an AI-assisted talent intelligence platform using Python, Gemini, LangGraph, Docling, and MySQL, combining structured resume/JD parsing, deterministic eligibility checks, evidence-backed scoring, batch ranking, LLM-based shortlist reranking, a stateful human-in-the-loop review pipeline, and job seeker qualification-gap analysis.
