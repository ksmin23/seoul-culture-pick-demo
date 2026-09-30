# 서울컬처픽 — Codex로 만드는 서울 전시 추천 Agent

서울시 공공데이터에서 조건에 맞는 전시를 찾아주는 교육용 데모로, Streamlit과 OpenAI Agents SDK를 활용해 구현했습니다.
**단일 Agent · 독립적인 질문·응답 · 실제 API/저장 데이터 두 모드**로 동작합니다.

## 시작하기

```bash
cd seoul-culture-pick-demo/solution
source .venv/bin/activate
streamlit run streamlit_app.py
```

브라우저에서 http://127.0.0.1:8501 을 엽니다. 서버를 종료하려면 실행한 터미널에서 Ctrl+C.
이 프로젝트에는 Python 3.12 `.venv`가 생성되어 있습니다.

다른 환경에서 재현하려면:

```bash
uv sync --frozen
uv run streamlit run streamlit_app.py
```

`pyproject.toml`과 `uv.lock`에 의존성을 고정했습니다. `uv sync`는 프로젝트를 editable 패키지로 설치하므로 Python 안전 경로 모드에서도 모듈 실행이 가능합니다.

## 설정

기존 `.env.local`은 보존했습니다. 필요한 환경변수 이름은 `.env.example`에 있습니다.

| 변수 | 용도 |
|---|---|
| OPENAI_API_KEY | 두 모드에서 실제 Agent 실행에 필요 |
| SEOUL_API_KEY | 전체 전시를 실제 API로 조회하거나 저장본을 갱신할 때 필요 |
| OPENAI_MODEL | 기본 `gpt-5.6-luna`. 다른 모델은 해당 프로젝트의 접근 권한에 따라 변경 |

서버 측에서만 키를 읽습니다. `.env.local`은 Git 제외 대상입니다. 키를 채팅·화면·로그에 출력하지 않습니다.

## 두 데이터 모드

- **저장 데이터**: 실제 공공데이터 저장본과 함께 저장한 시연 기준일을 사용합니다. 기본 제공 파일은 서울시 공식 JSON의 전시·미술 3,296건 중 최근 등록된 **1,000건**입니다. 시연 기준일은 **2026-09-28**이며, 서울 전체 결과가 아닙니다. 화면에 이 범위를 표시합니다.
- **실제 API**: `SEOUL_API_KEY`로 공식 `전시/미술` 분류의 전체 페이지를 조회하고 한국 시간의 현재 날짜를 사용합니다. 인증키가 없거나 조회가 실패하면 원인을 안내하며, 저장본으로 자동 전환하지 않습니다.
- 두 모드 모두 모델 호출에는 OpenAI API가 필요합니다. 저장 데이터 모드는 완전한 오프라인 모드가 아닙니다.
- 화면 기록은 브라우저 세션에서만 유지됩니다. 이전 질문·답변을 모델의 다음 입력에 넣지 않습니다.

## 저장 데이터 갱신

전체 데이터로 갱신 (`SEOUL_API_KEY` 필요):

```bash
python -m scripts.refresh_snapshot --reference-date 2026-09-28
```

축소된 공식 공개 샘플 5건으로 교체 (현재 1,000건 저장본을 덮어쓰므로 주의):

```bash
python -m scripts.refresh_snapshot --sample --reference-date 2026-09-28
```

`--reference-date`를 생략하면 한국 시간의 실행일을 저장합니다. 갱신은 기존 저장본을 교체합니다. 자동 갱신은 하지 않습니다. 데이터 출처·수집 시각·조회 범위도 함께 보관합니다.

공식 포털에서 내려받은 원본 JSON으로 1,000건 저장본을 재생성할 수 있습니다 (서울시 인증키 불필요):

```bash
python -m scripts.import_snapshot data/raw/seoul-cultural-events-2026-09-28.json --reference-date 2026-09-28 --limit 1000
```

원본 19,547건 중 전시·미술만 선택하고, 날짜 오류·빈 제목을 제외한 뒤 최근 등록 순으로 중복 없는 1,000건을 저장합니다. 원본 날짜는 변경하지 않으며 Unix 밀리초를 한국 시간으로 변환합니다. 출처·해시는 `data/snapshots/provenance.json`에 기록합니다.

## 실행 흐름

```text
streamlit_app.py  질문·모드 입력, 카드·실행 과정 표시
  → app/agent.py  Agent + Runner.run, 현재 질문만 전달
  → app/tools.py search_exhibitions function tool
  → seoul_api.py 또는 snapshots.py
  → dates.py + search.py 조건 검증·날짜 계산·필터·정렬
  → Agent의 반환 ID를 후보 목록과 대조
  → 원본 데이터로 카드와 추천 이유 표시
```

Agent는 자연어를 도구 인자로 바꾸고 결과를 반환합니다. 날짜·지역·요금 필터와 정렬은 Python이 담당합니다. Agent가 반환한 ID·순서·개수를 실제 도구 후보와 비교합니다. 카드의 이름·날짜·요금·링크와 추천 이유는 원본 및 적용 조건으로 구성하여 모델이 개관 여부 등을 단정하지 않도록 합니다.

실행 과정은 앱 내부에서 수집하는 도구 입력·조회 건수·검증 결과입니다. 모델의 내부 추론은 표시하지 않습니다. 이 데모는 `RunConfig(tracing_disabled=True)`로 별도의 Platform Traces 전송을 끄고 화면 실행 기록만 제공합니다.

## 추천 규칙

- 한국 시간 기준 이번 주말: 평일·토요일은 해당 토·일, 일요일은 당일만.
- 요청 기간과 행사 기간이 하루라도 겹치면 후보. 실제 개관 여부는 보장하지 않습니다.
- 무료 표시와 요금 설명이 충돌하거나 유료·조건부 요금 단서가 있으면 무료 추천에서 제외합니다. 요금 설명이 비어 있어도 공식 무료 표시가 있고 충돌이 없으면 무료로 분류합니다.
- 관심사가 있으면 제목·설명의 일치 여부를 우선 반영합니다. 같은 점수는 종료일·제목·ID 순입니다. 의미 기반 유사도 검색은 구현하지 않았습니다.
- 기본값: 이번 주말 · 서울 전체 · 유무료 전체 · 3개. 최대 10개까지 지원합니다.
- 결과가 적으면 있는 결과만 표시합니다. 모호·충돌·지원 범위 밖의 조건은 재입력을 안내합니다.
- 공식 분류가 전시/미술이면 전시 해설 등도 포함될 수 있습니다. 제목을 보고 임의 재분류하지 않습니다.

## 검증

```bash
python -m pytest -q
ruff check .
python -m scripts.smoke
python -m scripts.smoke --mode live
```

테스트는 모델/API 호출 없이 실행합니다. `scripts.smoke`는 **실제 모델 호출**을 실행하며 API 사용량이 발생합니다. live 모드는 서울시 인증키도 필요합니다.

- `tests/`의 가상 데이터는 테스트 전용이며 운영 저장본에 포함하지 않습니다.
- [검증 기록](docs/verification.md)
- [시연 대본](docs/demo-script.md)
- [요구사항](../requirements.md) · [용어집](../CONTEXT.md)

## 데이터 출처와 한계

[서울시 문화행사 정보](https://data.seoul.go.kr/dataList/OA-15486/A/1/datasetView.do) · 서울특별시 · 공공누리 제1유형 출처표시.

공식 명세의 HTTP `openapi.seoul.go.kr:8088` 엔드포인트를 사용합니다. 네트워크에서 이 주소의 접속이 가능해야 합니다. 인증 URL과 원본 HTTP 오류는 로그·사용자 메시지로 노출하지 않습니다.

기본 저장본은 최근 등록 전시 1,000건으로 한정되므로 지역·기간에 따라 결과가 없을 수 있습니다. 행사 기간·요금 정보가 실제 운영 상황과 다를 수 있고 휴관·예약·잔여석은 별도 확인이 필요합니다. 모델의 자연어 조건 해석에는 오류 가능성이 있으며, 화면의 적용 조건과 도구 인자를 확인할 수 있습니다.
