# Ranking pipeline benchmarks

A small, hand-labeled set of synthetic JD + candidate scenarios with known-correct
outcomes, run against the *real* deterministic ranking pipeline
(`pipeline.batch_ranker`, `pipeline.scoring_utils`, `pipeline.shortlist_reranker`).
This is what backs the ranking-quality claims for this project - re-runnable
evidence rather than "I tried a few resumes and it looked right."

No Gemini calls are made (education scoring only calls the LLM when a JD has a
real requirement, and none of these scenarios do), so it's free, fast, and safe
to run in CI.

## Running it

```bash
python -m benchmarks.run_evaluation
python -m benchmarks.run_evaluation --report benchmarks/report.md  # also write a markdown report
```

Exits non-zero if any scenario fails.

These scenarios also run as part of the normal `pytest` suite
(`tests/test_benchmarks.py`), so a regression in the deterministic pipeline shows
up in ordinary test runs too, not only when this script is run explicitly.

## What's covered

- `strong_candidate_ranks_first` - a fully-qualified candidate ranks first and is eligible.
- `missing_required_skill_is_ineligible` - one missing required skill is enough to fail eligibility.
- `insufficient_experience_is_ineligible` - meeting every skill but not the years requirement still fails eligibility.
- `job_hopper_flagged_not_disqualified` - frequent short stints surface as a visible `job_stability` flag without automatically rejecting an otherwise-qualified candidate (see design principle: eligibility support, not opaque auto-rejection).
- `no_education_requirement_does_not_penalize_anyone` - a JD-parser placeholder like `"Not specified"` is treated the same as a genuinely empty education requirement, and the deterministic education summary still reflects what's actually on the resume.
- `relative_score_floor_selects_expected_pool` - when nobody is hard-eligible, the relative-score fallback pool (>=50/100) contains exactly the candidates who clear that floor.
- `first_pass_vs_reranked_comparison` - demonstrates why the LLM reranking stage exists: a candidate can win on first-pass deterministic score alone but rank lower once LLM-judged experience relevance is blended in, and vice versa.

## LLM judgment-quality benchmark

`benchmarks/llm_quality_scenarios.py` + `run_llm_quality_eval.py` check whether
the *actual judgment* of the LLM-scored stages is good, not just whether the
surrounding parsing/blending code is correct. Unlike the scenarios above, this
makes real Gemini calls, so it's kept separate and opt-in rather than part of
the default pytest run:

```bash
python -m benchmarks.run_llm_quality_eval
python -m benchmarks.run_llm_quality_eval --report benchmarks/llm_quality_report.md
```

Requires `GOOGLE_API_KEY`. Also runnable via `pytest` if you explicitly opt in
(`RUN_LLM_QUALITY_BENCHMARK=1 pytest tests/test_llm_quality_eval.py`) - skipped
by default so ordinary test runs stay free, fast, and deterministic.

Covers:

- `education_match` against 5 hand-labeled cases: exact degree match, a
  higher-than-required degree, a missing degree, a clearly unrelated field, and
  an adjacent-but-not-exact field (expects `partially_matched`)
- `rerank_experience_relevance` against 3 hand-labeled cases: highly relevant
  senior experience (expects a high score), years present but an unrelated
  domain like retail management (expects a low score despite meeting the years
  threshold), and an adjacent domain like data analytics for an ML role
  (expects a middle-band score)

Each case asserts a coarse expected bucket (status enum or score range) rather
than an exact score, since the point is checking the model lands in the right
neighborhood, not reproducing one "correct" number. `tests/test_matcher.py` and
`tests/test_shortlist_reranker.py` still separately cover the parsing/fallback
behavior of these same LLM calls with mocked responses - this benchmark is the
complement that checks judgment quality with the real model.
