from datetime import date

import pytest
from pydantic import ValidationError

from app.dates import resolve_period
from app.schemas import SearchRequest


@pytest.mark.parametrize(
    "reference,expected",
    [
        ("2026-09-28", ("2026-10-03", "2026-10-04")),
        ("2026-10-03", ("2026-10-03", "2026-10-04")),
        ("2026-10-04", ("2026-10-04", "2026-10-04")),
        ("2026-12-31", ("2027-01-02", "2027-01-03")),
    ],
)
def test_weekend_boundaries(reference, expected):
    actual = resolve_period(SearchRequest(), date.fromisoformat(reference))
    assert tuple(map(str, actual)) == expected


def test_next_weekend_from_sunday():
    assert resolve_period(SearchRequest(period="next_weekend"), date(2026, 10, 4)) == (
        date(2026, 10, 10),
        date(2026, 10, 11),
    )


@pytest.mark.parametrize(
    "data",
    [
        {"period": "explicit", "start_date": "2026-10-04", "end_date": "2026-10-03"},
        {"period": "explicit", "start_date": "2026-02-30", "end_date": "2026-03-01"},
        {"period": "this_weekend", "start_date": "2026-10-03"},
        {"districts": ["부산"]},
        {"limit": 0},
        {"limit": 11},
    ],
)
def test_invalid_conditions_rejected(data):
    with pytest.raises(ValidationError):
        SearchRequest(**data)
