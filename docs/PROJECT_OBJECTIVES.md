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

Planned:

- React or Next.js
- TailwindCSS
- Recharts or Chart.js for analytics

### Backend

Current/planned:

- Python
- FastAPI
- REST APIs
- modular services

### AI/NLP Layer

Current:

- Docling for PDF/text extraction
- Gemini via Google Gen AI SDK for structured parsing and reasoning
- deterministic skill overlap and eligibility checks
- LLM-based shortlist reranking

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

Not chosen for now:

- PostgreSQL/pgvector

Reason:

- useful later for vector search, but not necessary for the current platform foundation
- MySQL is a better fit for the user's current strengths

### Deployment

Planned later:

- Docker Compose for local reproducibility
- frontend deployment on Vercel/Netlify
- backend deployment on Render/Railway/Fly.io if free/affordable

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

- `parser.py`
- `llm_parser.py`
- `jd_parser.py`
- `candidate_profiles.json`
- `parsed_jd.json`

Current capabilities:

- extract resume text from PDF
- parse resume into structured JSON
- parse JD into structured JSON
- normalize skills using LLM prompt instructions

### Single candidate matching

Implemented:

- `matcher.py`
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
- `batch_ranker.py`
- `batch_rankings.json`

Current capabilities:

- ranks multiple candidates against one JD
- deterministic skill scoring
- deterministic experience years pre-check
- batched education matching when education requirement exists
- local short-circuit when education is not specified

### Shortlist reranking

Implemented:

- `shortlist_reranker.py`
- `final_rankings.json`

Current capabilities:

- reads first-pass batch results
- selects top N candidates
- uses one batched LLM call to judge experience relevance
- produces final rank and final score
- catches cases where years are present but domain relevance is weak

### MySQL foundation

Implemented:

- `backend/schema.sql`
- `backend/app/db.py`
- `backend/app/ranking_repository.py`
- `setup_mysql.py`
- `save_rankings_to_mysql.py`
- `.env.example`

Current capabilities:

- create MySQL database/tables
- store screening runs
- store candidates
- store candidate rankings
- store evidence rows
- keep full ranking JSON for audit/debugging

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

### Automated tests

Implemented:

- `tests/` (pytest) covering parser, matcher, batch ranker, shortlist reranker, input service, resume intake service, and the FastAPI `/health` and `/rank-candidates` routes
- `conftest.py` at repo root so tests can import the top-level scripts as modules

Deliberately not covered yet: functions that call the Gemini API directly (`education_match`, `experience_match`, `analyze_match`, `extract_structured_resume`, `extract_structured_jd`, batched LLM reranking) — these need mocking or recorded fixtures, not done yet.

## Current Completion Estimate

Approximate status: 35-45%.

The project has a working AI pipeline prototype, a FastAPI backend exposing that pipeline (including file upload ingestion), initial persistence, and a starter automated test suite. It is not yet a complete product.

Major missing pieces:

- actual frontend website
- a real git history (see Known Issues below)
- robust validation/error handling for malformed LLM JSON in the non-batch paths (`jd_parser.extract_structured_jd` silently returns `{}` on parse failure; `education_match`/`experience_match`/`analyze_match` in `matcher.py` do not catch `JSONDecodeError` at all)
- UI/UX
- Docker setup
- evaluation/benchmarking against a labeled dataset
- documentation and demo assets
- test coverage for LLM-calling functions (mocked or recorded)

## Known Issues

- The `.git` directory exists but is empty (no commits, no HEAD, no refs) — this is not currently a working repository. Run `git init` and make an initial commit before relying on git history, branches, or a GitHub remote for this portfolio project.

## Next Engineering Tasks

### Phase 1 - Backend foundation (done)

Goal: turn scripts into backend services without breaking current scripts.

Done:

- FastAPI app with health, ranking, reranking, profile-gap, persistence, and upload endpoints
- ranking logic in service modules
- request schemas (Pydantic)
- connected to the MySQL repository layer

Still open from the original phase:

- add error handling for malformed LLM JSON in `jd_parser.py` / `matcher.py` (currently only `llm_parser.extract_structured_resume` handles this)
- add response schemas (routes currently return plain dicts, not validated Pydantic response models)

### Phase 2 - Multi-resume ingestion (mostly done)

Goal: support real batches instead of only synthetic JSON.

Done:

- `POST /upload/rank-candidates` accepts a JD file plus multiple resume files (PDF/DOCX/TXT via Docling)
- parses each resume independently and reports failures without stopping the batch
- reuses `parser.py` / `llm_parser.py` / `jd_parser.py` for extraction

Still open:

- a CLI equivalent (`parse_resumes_folder.py`) for local/offline batch parsing of a folder of PDFs
- store parsed candidates (not just rankings) in MySQL

### Phase 3 - Web app

Goal: build a recruiter-facing interface first, then extend it into a job seeker interface.

Tasks:

- create React/Next frontend
- upload JD
- upload resumes
- run ranking
- show ranking table
- show candidate detail drawer/page
- show evidence and missing must-haves
- show final reranking result

Job seeker mode tasks:

- upload own resume
- paste target JD
- show qualification gaps
- show missing must-haves
- show suggested projects
- show resume improvement recommendations
- show role-readiness score

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

The FastAPI backend foundation (Phase 1) and file-upload ingestion (Phase 2) are done. The immediate next best step is:

> Fix the git repository (it currently has no commits), then start the Phase 3 web app so the API has a real frontend to bridge to.

Secondary priorities: response schemas for the existing endpoints, error handling for the two remaining unguarded JSON-parsing paths (`jd_parser.py`, `matcher.py`), and test coverage (mocked) for the LLM-calling functions.

## Notes for Recruiter/LinkedIn Positioning

Avoid presenting the project as:

> I used Gemini to score resumes.

Present it as:

> I built an end-to-end AI Talent Intelligence Platform with document parsing, structured resume/JD extraction, deterministic eligibility checks, evidence-backed ranking, job seeker qualification-gap analysis, LLM-based shortlist reranking, MySQL persistence, and planned recruiter/job-seeker dashboards.

Possible resume bullet:

> Built an AI-assisted talent intelligence platform using Python, Gemini, Docling, and MySQL, combining structured resume/JD parsing, deterministic eligibility checks, evidence-backed scoring, batch ranking, LLM-based shortlist reranking, and job seeker qualification-gap analysis.
