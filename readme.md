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

