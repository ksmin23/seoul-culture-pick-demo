from datetime import datetime
from urllib.parse import quote

import httpx

from app.config import SOURCE_URL
from app.dates import SEOUL, today_seoul
from app.errors import AppError
from app.schemas import Dataset, DatasetMeta
from app.search import EXHIBITION_CATEGORY

# 서울시 공식 명세의 HTTP 엔드포인트. 예외에 들어 있는 인증 URL은 외부로 노출하지 않는다.
BASE_URL = "http://openapi.seoul.go.kr:8088"


def fetch_exhibitions(key: str, *, sample: bool = False, client=None) -> Dataset:
    if not key or key == "sample" and not sample:
        raise AppError(
            "seoul_key_missing",
            "실제 API 모드에는 SEOUL_API_KEY가 필요합니다.",
            allow_snapshot=True,
        )
    if sample and key != "sample":
        raise ValueError("공개 샘플 요청은 sample 키만 사용합니다.")
    own_client = client is None
    client = client or httpx.Client(timeout=25.0, follow_redirects=False)
    rows, total = [], None
    page_size = 5 if sample else 1000
    try:
        for start in range(1, 10001, page_size):
            url = f"{BASE_URL}/{quote(key, safe='')}/json/culturalEventInfo/{start}/{start + page_size - 1}/{quote(EXHIBITION_CATEGORY, safe='')}"
            try:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as exc:
                code = (
                    "seoul_auth" if exc.response.status_code in (401, 403) else "seoul_connection"
                )
                raise AppError(
                    code,
                    "서울시 API 요청이 거절되었습니다. 인증 또는 서비스 상태를 확인해 주세요.",
                    allow_snapshot=True,
                ) from None
            except httpx.HTTPError:
                raise AppError(
                    "seoul_connection",
                    "서울시 API에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
                    allow_snapshot=True,
                ) from None
            except ValueError:
                raise AppError(
                    "seoul_format",
                    "서울시 API 응답 형식을 확인할 수 없습니다.",
                    allow_snapshot=True,
                ) from None
            if not isinstance(payload, dict):
                raise AppError(
                    "seoul_format", "서울시 API 응답 형식이 올바르지 않습니다.", allow_snapshot=True
                )
            body = payload.get("culturalEventInfo", {})
            result = body.get("RESULT", payload.get("RESULT", {}))
            code = result.get("CODE", "")
            if code == "INFO-200":
                if rows:
                    raise AppError(
                        "seoul_incomplete",
                        "조회 중 데이터가 변경되어 전체 조회를 완료하지 못했습니다.",
                        allow_snapshot=True,
                    )
                total = 0
                break
            if code != "INFO-000":
                auth = code in {"INFO-100", "ERROR-100", "ERROR-300", "ERROR-331", "ERROR-332"}
                raise AppError(
                    "seoul_auth" if auth else "seoul_service",
                    "서울시 인증키·이용 권한을 확인해 주세요."
                    if auth
                    else "서울시 API가 요청을 처리하지 못했습니다.",
                    allow_snapshot=True,
                )
            try:
                page_total = int(body["list_total_count"])
                batch = body["row"]
                if not isinstance(batch, list) or any(not isinstance(row, dict) for row in batch):
                    raise ValueError()
            except (KeyError, TypeError, ValueError):
                raise AppError(
                    "seoul_format",
                    "서울시 API 데이터 형식이 올바르지 않습니다.",
                    allow_snapshot=True,
                ) from None
            if total is not None and total != page_total:
                raise AppError(
                    "seoul_incomplete",
                    "조회 중 전체 건수가 변경되었습니다. 다시 조회해 주세요.",
                    allow_snapshot=True,
                )
            total = page_total
            rows.extend(batch)
            if sample or len(rows) >= total:
                break
            if not batch:
                raise AppError(
                    "seoul_incomplete",
                    "일부 페이지를 받지 못해 전체 검색을 완료할 수 없습니다.",
                    allow_snapshot=True,
                )
        if not sample and len(rows) != total:
            raise AppError(
                "seoul_incomplete", "전체 데이터 조회가 완료되지 않았습니다.", allow_snapshot=True
            )
        return Dataset(
            metadata=DatasetMeta(
                source_url=SOURCE_URL,
                collected_at=datetime.now(SEOUL),
                reference_date=today_seoul(),
                scope="공식 공개 샘플 5건 — 서울 전체 검색이 아닙니다"
                if sample
                else "서울시 공식 전시/미술 분류 전체",
                complete=not sample,
                source_total=total or 0,
                row_count=len(rows),
            ),
            rows=rows,
        )
    finally:
        if own_client:
            client.close()
