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

## What's not covered (yet)

LLM-scored stages that require a real requirement to evaluate against - education
matching against an actual degree requirement, and the LLM experience-relevance
prompt's own judgment quality - aren't exercised here, since that would require
either live Gemini calls (costs quota, non-deterministic) or mocking the LLM
response (which only tests the parsing/blending code, not the prompt's actual
judgment). `tests/test_matcher.py` and `tests/test_shortlist_reranker.py` cover
the parsing/fallback behavior of those LLM calls with mocked responses; there's
no automated check yet on whether the LLM's actual judgments are *good*. Adding
that would mean a small set of real resume/JD pairs with a human-labeled "correct"
relevance judgment to compare the live LLM output against - worth doing before
leaning on this project's LLM-scoring quality as a portfolio claim, not required
for the deterministic-pipeline coverage this currently provides.
