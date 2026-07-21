import pytest

from benchmarks.run_evaluation import run_first_pass_vs_reranked_comparison, run_scenario
from benchmarks.scenarios import SCENARIOS


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.name for s in SCENARIOS])
def test_benchmark_scenario(scenario):
    _ranked, failures = run_scenario(scenario)
    assert not failures, "; ".join(failures)


def test_first_pass_vs_reranked_comparison():
    _first_pass_order, _reranked_order, failures = run_first_pass_vs_reranked_comparison()
    assert not failures, "; ".join(failures)
