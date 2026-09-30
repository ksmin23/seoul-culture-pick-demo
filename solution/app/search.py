import hashlib
import html
import re
from datetime import date
from urllib.parse import urlsplit

from app.dates import resolve_period
from app.schemas import Exhibition, SearchRequest, SearchResult

EXHIBITION_CATEGORY = "전시/미술"


def plain(value: object) -> str:
    return re.sub(r"<[^>]*>", "", html.unescape(str(value or ""))).strip()


def safe_url(value: object) -> str:
    url = plain(value)
    try:
        parsed = urlsplit(url)
        if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username:
            return url
    except ValueError:
        pass
    return ""


def classify_fee(flag: str, details: str) -> str:
    flag, details = plain(flag), plain(details)
    positive_price = any(int(n.replace(",", "")) > 0 for n in re.findall(r"([\d,]+)\s*원", details))
    conditional = bool(re.search(r"유료|일부|별도|조건|회원|대상자|초대|할인|\d+\s*만원", details))
    says_free = "무료" in details or details.strip() in {"0", "0원"}
    if flag == "무료":
        return "unknown" if positive_price or conditional else "free"
    if flag == "유료":
        return "unknown" if says_free else "paid"
    if says_free and not positive_price and not conditional:
        return "free"
    if positive_price and not says_free:
        return "paid"
    return "unknown"


def normalize(row: dict) -> Exhibition | None:
    if plain(row.get("CODENAME")) != EXHIBITION_CATEGORY:
        return None
    title = plain(row.get("TITLE"))
    start = date.fromisoformat(plain(row.get("STRTDATE"))[:10])
    end = date.fromisoformat(plain(row.get("END_DATE"))[:10])
    if not title or start > end:
        raise ValueError("유효하지 않은 전시 정보")
    url = safe_url(row.get("HMPG_ADDR")) or safe_url(row.get("ORG_LINK"))
    identity = "|".join([title, str(start), str(end), plain(row.get("PLACE")), url])
    return Exhibition(
        id=hashlib.sha256(identity.encode()).hexdigest()[:16],
        title=title,
        district=plain(row.get("GUNAME")),
        place=plain(row.get("PLACE")),
        start=start,
        end=end,
        fee_status=classify_fee(row.get("IS_FREE"), row.get("USE_FEE")),
        fee_text=plain(row.get("USE_FEE")),
        hours=plain(row.get("PRO_TIME")),
        url=url,
        description=" ".join(plain(row.get(k)) for k in ["PROGRAM", "ETC_DESC", "PLAYER"])[:1500],
    )


def search_rows(rows: list[dict], request: SearchRequest, reference: date) -> SearchResult:
    start, end = resolve_period(request, reference)
    found, skipped = {}, 0
    for row in rows:
        try:
            exhibition = normalize(row)
        except (ValueError, TypeError):
            skipped += 1
            continue
        if exhibition is None:
            continue
        if exhibition.end < start or exhibition.start > end:
            continue
        if request.districts and exhibition.district not in request.districts:
            continue
        if request.fee != "all" and exhibition.fee_status != request.fee:
            continue
        if request.keyword and request.keyword.casefold() not in exhibition.title.casefold():
            continue
        found[exhibition.id] = exhibition

    def sort_key(event):
        corpus = (event.title + " " + event.description).casefold()
        score = sum(1 for word in request.interests if word.strip() and word.casefold() in corpus)
        return -score, event.end, event.title, event.id

    ordered = sorted(found.values(), key=sort_key)
    return SearchResult(
        request=request,
        start=start,
        end=end,
        total_matches=len(ordered),
        candidates=ordered[: request.limit],
        skipped_rows=skipped,
    )


def grounded_reason(event: Exhibition, request: SearchRequest) -> str:
    """개관 여부 등 원본에 없는 사실을 이유에 추가하지 않는다."""
    fee = {"free": "무료 전시", "paid": "유료 전시", "unknown": "전시(요금 확인 필요)"}[
        event.fee_status
    ]
    reason = f"요청 기간과 행사 기간이 겹치는 {event.district}의 {fee}입니다."
    corpus = (event.title + " " + event.description).casefold()
    matched = [word for word in request.interests if word.strip() and word.casefold() in corpus]
    if matched:
        reason += " 제목·설명에 관심사 ‘" + ", ".join(matched) + "’가 포함되어 우선 선정했습니다."
    elif not request.interests:
        reason += " 종료일이 가까운 순으로 선정했습니다."
    return reason
