# Ranking pipeline benchmark report

Generated: 2026-07-15T09:50:00.433803+00:00
Result: 7/7 scenarios passed

## [PASS] strong_candidate_ranks_first

A candidate meeting every required skill and experience threshold should rank first and be eligible.

## [PASS] missing_required_skill_is_ineligible

A candidate missing one required skill must be marked ineligible with that skill listed as missing.

## [PASS] insufficient_experience_is_ineligible

A candidate with every required skill but below the minimum years of experience must be ineligible.

## [PASS] job_hopper_flagged_not_disqualified

Frequent short stints should surface as a job_stability flag without auto-rejecting an otherwise-qualified candidate.

## [PASS] no_education_requirement_does_not_penalize_anyone

A JD whose education_required is a JD-parser placeholder like 'Not specified' must be treated the same as a genuinely empty requirement - no candidate should be scored on it, and the deterministic education summary should still show what's actually on the resume.

## [PASS] relative_score_floor_selects_expected_pool

When nobody is hard-eligible, the relative-score fallback pool (>=50/100) should include only the candidates who actually clear that floor.

## [PASS] first_pass_vs_reranked_comparison

Shows why the LLM reranking stage exists: first-pass order is deterministic-score-only, reranked order blends in LLM-judged experience relevance (60% first-pass / 40% relevance).

- First-pass order: High Score Weak Relevance > Lower Score Strong Relevance
- Reranked order: Lower Score Strong Relevance > High Score Weak Relevance
