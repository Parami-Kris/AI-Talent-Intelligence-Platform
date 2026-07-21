import os

import pytest

from benchmarks.llm_quality_scenarios import EDUCATION_SCENARIOS, EXPERIENCE_SCENARIOS
from benchmarks.run_llm_quality_eval import run_education_scenario, run_experience_scenario

pytestmark = pytest.mark.skipif(
    not (os.getenv("GOOGLE_API_KEY") and os.getenv("RUN_LLM_QUALITY_BENCHMARK")),
    reason=(
        "Makes real Gemini calls (costs quota, non-deterministic) - opt in with "
        "RUN_LLM_QUALITY_BENCHMARK=1 (and a real GOOGLE_API_KEY) to include it in a test run."
    ),
)


@pytest.mark.parametrize("scenario", EDUCATION_SCENARIOS, ids=lambda s: s.name)
def test_education_match_quality(scenario):
    _result, failures = run_education_scenario(scenario)
    assert not failures, "; ".join(failures)


@pytest.mark.parametrize("scenario", EXPERIENCE_SCENARIOS, ids=lambda s: s.name)
def test_experience_relevance_quality(scenario):
    _result, failures = run_experience_scenario(scenario)
    assert not failures, "; ".join(failures)
