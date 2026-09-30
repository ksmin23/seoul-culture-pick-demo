from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.schemas import SearchRequest

SEOUL = ZoneInfo("Asia/Seoul")


def today_seoul() -> date:
    return datetime.now(SEOUL).date()


def resolve_period(request: SearchRequest, reference: date) -> tuple[date, date]:
    if request.period == "explicit":
        return date.fromisoformat(request.start_date), date.fromisoformat(request.end_date)
    if request.period == "today":
        return reference, reference
    if request.period == "tomorrow":
        day = reference + timedelta(days=1)
        return day, day
    saturday = reference + timedelta(days=5 - reference.weekday())
    if request.period == "next_weekend":
        saturday += timedelta(days=7)
        return saturday, saturday + timedelta(days=1)
    # 일요일에는 지난 토요일을 추천하지 않는다.
    return max(reference, saturday), saturday + timedelta(days=1)
