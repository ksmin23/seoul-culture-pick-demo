import pytest


@pytest.fixture
def row():
    # 테스트 전용 가상 데이터. 운영 저장본과 섞지 않는다.
    return {
        "CODENAME": "전시/미술",
        "GUNAME": "종로구",
        "TITLE": "테스트 전시",
        "PLACE": "테스트 전시장",
        "STRTDATE": "2026-10-01 00:00:00.0",
        "END_DATE": "2026-10-10 00:00:00.0",
        "IS_FREE": "무료",
        "USE_FEE": "",
        "HMPG_ADDR": "https://example.org/test",
        "PRO_TIME": "휴관일 확인 필요",
    }
