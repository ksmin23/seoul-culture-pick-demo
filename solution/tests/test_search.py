from datetime import date

import pytest

from app.schemas import SearchRequest
from app.search import classify_fee, safe_url, search_rows


@pytest.mark.parametrize(
    "flag,details,expected",
    [
        ("무료", "", "free"),
        ("", "무료", "free"),
        ("", "", "unknown"),
        ("무료", "일부 유료", "unknown"),
        ("무료", "성인 10,000원", "unknown"),
        ("유료", "무료", "unknown"),
        ("유료", "10,000원", "paid"),
        ("무료", "회원 무료", "unknown"),
        ("무료", "입장료 0원", "free"),
    ],
)
def test_fee_conflicts(flag, details, expected):
    assert classify_fee(flag, details) == expected


def test_only_matching_exhibitions_no_automatic_relaxation(row):
    rows = [
        row,
        {**row, "TITLE": "유료", "IS_FREE": "유료", "USE_FEE": "10,000원"},
        {**row, "TITLE": "다른 구", "GUNAME": "마포구"},
        {**row, "TITLE": "공연", "CODENAME": "연극"},
        {**row, "TITLE": "기간 밖", "END_DATE": "2026-10-02"},
    ]
    result = search_rows(rows, SearchRequest(districts=["종로"], fee="free"), date(2026, 9, 28))
    assert [event.title for event in result.candidates] == ["테스트 전시"]
    assert result.total_matches == 1
    assert result.request.districts == ["종로구"]


def test_overlap_boundaries_sort_and_deduplicate(row):
    ending = {**row, "TITLE": "마지막 날", "END_DATE": "2026-10-03"}
    starting = {**row, "TITLE": "시작 날", "STRTDATE": "2026-10-04"}
    result = search_rows([row, ending, starting, row], SearchRequest(), date(2026, 9, 28))
    assert result.total_matches == 3
    assert result.candidates[0].title == "마지막 날"


def test_preference_is_grounded_in_text(row):
    later = {**row, "TITLE": "사진 전시", "END_DATE": "2026-12-01"}
    result = search_rows([row, later], SearchRequest(interests=["사진"]), date(2026, 9, 28))
    assert result.candidates[0].title == "사진 전시"


def test_invalid_date_skipped_unknown_fee_excluded(row):
    result = search_rows(
        [{**row, "END_DATE": "bad"}, {**row, "IS_FREE": "", "USE_FEE": ""}],
        SearchRequest(fee="free"),
        date(2026, 9, 28),
    )
    assert result.skipped_rows == 1
    assert result.total_matches == 0


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "file:///etc/passwd", "https://user:pass@example.org", "not-a-link"],
)
def test_unsafe_links_not_rendered(url):
    assert safe_url(url) == ""


def test_reason_does_not_claim_opening_or_availability(row):
    from app.search import grounded_reason, normalize

    reason = grounded_reason(normalize(row), SearchRequest())
    assert "행사 기간이 겹치는" in reason
    assert "관람할 수" not in reason
    assert "종로구" in reason
