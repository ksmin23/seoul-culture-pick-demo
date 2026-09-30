from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

DISTRICTS = "종로구 중구 용산구 성동구 광진구 동대문구 중랑구 성북구 강북구 도봉구 노원구 은평구 서대문구 마포구 양천구 강서구 구로구 금천구 영등포구 동작구 관악구 서초구 강남구 송파구 강동구".split()


class SearchRequest(BaseModel):
    period: Literal["this_weekend", "next_weekend", "today", "tomorrow", "explicit"] = (
        "this_weekend"
    )
    start_date: str | None = None
    end_date: str | None = None
    districts: list[str] = Field(default_factory=list, description="빈 목록은 서울 전체")
    fee: Literal["all", "free", "paid"] = "all"
    limit: int = Field(default=3, ge=1, le=10)
    keyword: str = Field(default="", max_length=100, description="반드시 일치해야 하는 제목 검색어")
    interests: list[str] = Field(default_factory=list, description="선정 우선순위용 관심사")

    @model_validator(mode="after")
    def validate_dates_and_districts(self):
        normalized = []
        for district in self.districts:
            district = district.strip()
            if district not in DISTRICTS and district + "구" in DISTRICTS:
                district += "구"
            if district not in DISTRICTS:
                raise ValueError("서울의 자치구 이름을 입력해 주세요.")
            if district not in normalized:
                normalized.append(district)
        self.districts = normalized
        if self.period == "explicit":
            if not self.start_date or not self.end_date:
                raise ValueError("시작일과 종료일을 함께 입력해 주세요.")
            start, end = date.fromisoformat(self.start_date), date.fromisoformat(self.end_date)
            if start > end:
                raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")
        elif self.start_date is not None or self.end_date is not None:
            raise ValueError("상대 날짜와 명시 날짜를 함께 지정할 수 없습니다.")
        return self


class Exhibition(BaseModel):
    id: str
    title: str
    district: str
    place: str
    start: date
    end: date
    fee_status: Literal["free", "paid", "unknown"]
    fee_text: str
    hours: str
    url: str
    description: str


class DatasetMeta(BaseModel):
    source_url: str
    collected_at: datetime
    reference_date: date
    scope: str
    complete: bool
    source_total: int
    row_count: int


class Dataset(BaseModel):
    metadata: DatasetMeta
    rows: list[dict]


class SearchResult(BaseModel):
    request: SearchRequest
    start: date
    end: date
    total_matches: int
    candidates: list[Exhibition]
    skipped_rows: int


class Selection(BaseModel):
    event_id: str
    reason: str = Field(description="조회된 데이터만 근거로 한 짧은 한국어 추천 이유")


class AgentAnswer(BaseModel):
    status: Literal["results", "clarification"]
    message: str = Field(
        description="clarification일 때 필요한 재입력 안내. results일 때는 빈 문자열"
    )
    selections: list[Selection]
