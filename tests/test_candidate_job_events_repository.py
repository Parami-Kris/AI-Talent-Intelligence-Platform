from backend.app.candidate_job_events_repository import pick_best_title


def test_pick_best_title_prefers_liked_over_applied_over_viewed():
    rows = [
        ("Backend Engineer", "viewed", 2),
        ("ML Engineer", "liked", 1),
    ]

    # A single "like" (weight 3) outweighs two mere "views" (weight 1 each = 2).
    assert pick_best_title(rows) == "ML Engineer"


def test_pick_best_title_sums_weighted_counts_per_title():
    rows = [
        ("Backend Engineer", "viewed", 3),
        ("Backend Engineer", "applied", 1),
        ("Data Scientist", "viewed", 2),
    ]

    # Backend Engineer: 3*1 + 1*2 = 5. Data Scientist: 2*1 = 2.
    assert pick_best_title(rows) == "Backend Engineer"


def test_pick_best_title_ignores_zero_weight_event_types():
    rows = [("Anything", "searched", 100)]

    assert pick_best_title(rows) is None


def test_pick_best_title_returns_none_for_no_rows():
    assert pick_best_title([]) is None
