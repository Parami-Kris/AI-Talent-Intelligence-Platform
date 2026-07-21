from pipeline.scoring_utils import candidates_within_relative_floor


def test_candidates_within_relative_floor_keeps_scores_at_or_above_floor():
    results = [{"overall_score": 75}, {"overall_score": 50}, {"overall_score": 49.9}]

    kept = candidates_within_relative_floor(results)

    assert kept == [{"overall_score": 75}, {"overall_score": 50}]


def test_candidates_within_relative_floor_handles_missing_score():
    results = [{"overall_score": None}, {}]

    assert candidates_within_relative_floor(results) == []


def test_candidates_within_relative_floor_supports_custom_key_and_floor():
    results = [{"final_score": 90}, {"final_score": 61}, {"final_score": 59}]

    kept = candidates_within_relative_floor(results, score_key="final_score", floor=60)

    assert kept == [{"final_score": 90}, {"final_score": 61}]
