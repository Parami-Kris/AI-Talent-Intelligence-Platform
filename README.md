---
title: AI Talent Intelligence Platform
emoji: 🎯
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# AI Talent Intelligence Platform

FastAPI backend for resume/JD parsing, evidence-backed candidate ranking, a LangGraph
human-in-the-loop ranking pipeline, and MySQL persistence. See `docs/PROJECT_OBJECTIVES.md`
for the full spec and status, and `web-app/` for the recruiter dashboard frontend.

## Local development with Docker

`docker-compose.yml` runs the backend alongside a local MySQL 8 instance (auto-initialized
from `backend/schema.sql`), so you don't need Docling's heavy dependency chain
(torch/transformers/docling-ibm-models) or a MySQL server installed on the host.

```bash
cp .env.example .env   # fill in GOOGLE_API_KEY at minimum; MySQL vars are overridden by compose
docker compose up --build
```

The API is then available at `http://localhost:8000` (`GET /health` to check), and MySQL
is reachable from the host at `localhost:3307` (not 3306, to avoid clashing with a MySQL
server you might already have running locally - the backend container itself talks to it
over the internal Docker network on port 3306 regardless). The build bakes Docling's models
in at image-build time (see `Dockerfile`), so the first `--build` is slow but the container
starts fast on every run after. Data persists in the `mysql_data` Docker volume across
restarts; `docker compose down -v` clears it.

This is for local reproducibility only — production runs on Hugging Face Spaces (backend)
and GitHub Pages (frontend), see `docs/PROJECT_OBJECTIVES.md`.

## Notes on resume parsing

Be careful with the phrase:

"just extract the skills from resume"

That sounds simple, but it's actually one of the hardest parts.

Consider:

Built a transformer-based chatbot using LangChain and OpenAI APIs.

The resume never explicitly says:

Skills:
- LangChain
- Prompt Engineering
- LLMs

A good system should infer those.

That's where:

LLMs
embeddings
skill ontology

become valuable.

