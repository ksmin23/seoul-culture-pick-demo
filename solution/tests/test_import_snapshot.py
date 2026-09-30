from datetime import date

from scripts.import_snapshot import build_snapshot


def test_portal_timestamp_uses_korea_date_and_excludes_invalid_rows():
    row = {
        'codename': '전시/미술', 'title': '테스트 전시', 'guname': '종로구',
        'strtdate': 1790780400000, 'end_date': 1791126000000,
        'rgstdate': '2026-09-20', 'is_free': '무료',
    }
    dataset = build_snapshot({'DATA': [row, row.copy(), dict(row, end_date=0),
                                      dict(row, codename='콘서트')]}, date(2026, 9, 28))
    assert dataset.metadata.row_count == 1
    assert dataset.metadata.source_total == 3
    assert dataset.rows[0]['STRTDATE'] == '2026-10-01 00:00:00'
    assert dataset.rows[0]['END_DATE'] == '2026-10-05 00:00:00'
