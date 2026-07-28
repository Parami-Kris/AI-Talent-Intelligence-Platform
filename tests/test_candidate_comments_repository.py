from datetime import datetime

from backend.app.candidate_comments_repository import _shape_comment_rows


def test_shape_comment_rows_maps_dict_rows_and_formats_timestamp():
    rows = [
        {"id": 1, "comment_text": "Strong candidate.", "is_caution": 0, "created_at": datetime(2026, 7, 20, 10, 0, 0)},
        {"id": 2, "comment_text": "Withdrew after offer.", "is_caution": 1, "created_at": datetime(2026, 7, 21, 9, 0, 0)},
    ]

    shaped = _shape_comment_rows(rows)

    assert shaped == [
        {"id": 1, "comment_text": "Strong candidate.", "is_caution": False, "created_at": "2026-07-20T10:00:00"},
        {"id": 2, "comment_text": "Withdrew after offer.", "is_caution": True, "created_at": "2026-07-21T09:00:00"},
    ]


def test_shape_comment_rows_handles_empty_list():
    assert _shape_comment_rows([]) == []
