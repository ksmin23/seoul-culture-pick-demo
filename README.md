# 서울컬처픽 — Codex로 만드는 서울 전시 추천 Agent

> “이번 주말 종로에서 볼 수 있는 무료 전시 3개 찾아줘.”

서울시 공공데이터와 OpenAI Agents SDK를 활용해 전시 추천 Agent를 만드는 **Codex 실습 프로젝트**입니다. 요구사항 인터뷰부터 설계, 구현, Streamlit 화면 구성, 검증까지 대화를 통해 진행합니다.

## 1. 프로젝트 목적

간단한 아이디어를 실행 가능한 Agent로 구체화하는 과정을 경험하는 것이 목표입니다. 처음부터 코드를 요청하기 전에 `grill-with-docs` 스킬로 질문을 주고받으며 다음과 같은 기준을 정합니다.

- ‘이번 주말’은 언제부터 언제까지인가?
- 무료 표시와 요금 설명이 다르면 어떻게 처리할 것인가?
- 조건에 맞는 전시가 3개보다 적으면 어떻게 답할 것인가?
- 실시간 API와 저장 데이터는 언제 사용할 것인가?

합의한 요구사항과 용어를 문서에 남기고, 이를 바탕으로 조회 도구 → Agent → 웹 화면 → 검증 순서로 구현합니다. 자연어 질문을 도구 입력으로 바꾸는 Agent의 역할과, 날짜·지역·요금 조건을 검사하는 Python 코드의 역할을 함께 살펴봅니다.

완성 예제는 **전시만 추천하는 단일 Agent**, **독립적인 질문·응답**, **실제 API/저장 데이터 두 모드**로 구성되어 있습니다.

## 2. 환경 구성

### 준비물

| 항목 | 용도 |
| --- | --- |
| Codex | 프로젝트 생성, 요구사항 인터뷰, 코드 작성·실행 |
| Git | 저장소 다운로드와 브랜치 전환 |
| Node.js / npm (`npx`) | 아래 스킬 설치 명령 실행 |
| Python 3.12 이상, uv | 완성 예제의 가상환경·의존성 구성 |
| OpenAI API 키 | Agent 실행. 저장 데이터 모드에서도 필요 |
| 서울 열린데이터광장 인증키 | 실제 API 모드 사용 시 필요 |

### 실습용 스킬 설치

실습할 프로젝트 폴더에서 다음 명령을 실행합니다. [Matt Pocock 스킬 저장소의 Codex 설치 안내](https://github.com/mattpocock/skills#installation-30-second-setup)를 따릅니다.

```bash
npx skills@latest add mattpocock/skills
```

설치 대상 Agent로 **Codex**를 선택하고 다음 스킬을 포함합니다.

| 스킬 | 실습에서의 용도 |
| --- | --- |
| `grill-with-docs` | 요구사항을 질문으로 구체화하고 설계 결정을 문서화 |
| `grilling`, `domain-modeling` | `grill-with-docs`가 사용하는 인터뷰·도메인 정리 스킬 |
| `setup-matt-pocock-skills` | 프로젝트의 문서 저장 위치 등 초기 설정 |
| `to-questionnaire` | 실습 대화를 질문·응답 기록으로 정리할 때 사용. 기존 기록을 따라 하기만 할 때는 선택 사항 |

설치 후 Codex에서 스킬이 보이는지 확인하고, `setup-matt-pocock-skills`를 실행해 문서 저장 위치 등을 설정합니다. 이미 같은 스킬을 플러그인으로 설치했다면 중복 설치 없이 기존 스킬을 사용합니다.

대화 기록은 당시 설치된 스킬 이름과 경로를 담고 있습니다. 로컬 캐시 경로를 그대로 복사하지 말고, 자신의 Codex에 설치된 스킬을 선택하세요. 스킬 버전에 따라 질문 순서나 생성 문서 이름이 달라질 수 있습니다. 이 실습의 요구사항은 `requirements.md`, 용어는 `CONTEXT.md`에 기록하도록 요청하면 비교하기 쉽습니다.

## 3. 실행 방법 — Codex에서 직접 만들어 보기

### 새 실습 프로젝트 만들기

1. Codex에서 새 로컬 프로젝트를 만들고, 비어 있는 실습 폴더를 연결합니다. 예: `seoul-culture-pick-practice`.
2. 해당 폴더에 위 스킬을 설치하고 새 대화를 시작합니다.
3. 이 저장소의 [to-questionnaire-seoul-culture-pick.md](./to-questionnaire-seoul-culture-pick.md)를 별도로 열어 둡니다.
4. 문서의 **‘사용자 프롬프트’만 한 번에 하나씩** Codex에 입력합니다. 각 응답을 읽고 다음 단계로 진행합니다. ‘Assistant 답변’은 비교용 기록입니다.

직접 구현하는 흐름을 경험하려면 완성 코드가 있는 `solution/`과 별도의 폴더에서 시작하세요.

### 프롬프트 진행 순서

| 순서 | 기록의 단계 | 실습 내용 |
| --- | --- | --- |
| 1 | 요구사항 인터뷰 시작 | `grill-with-docs`를 선택하고 서울 문화행사 추천 Agent와 대표 질문 제시 |
| 2 | 화면·범위·대화·데이터 모드 선택 | 웹 채팅, 전시만, 단일 질문, 두 데이터 모드 선택 |
| 3 | 추천 규칙 확정 | 주말·무료·추천 순서·결과 부족 처리 등 결정 |
| 4 | 시연·데이터 동작 확정 | 기준일, 카드 구성, 오류 처리 등 결정 |
| 5 | 최종 합의와 구조 논의 | 요구사항 확정 후 프로젝트 폴더 구조 검토 |
| 6 | Streamlit 구성 논의 | 웹 화면 구성과 Agent 연결 방식 결정 |
| 7 | 구현 요청 | 자신의 프로젝트 경로를 지정하고 virtualenv 구성·구현 요청 |
| 8 | API 키 사용 방식 확정 | 실제로 `.env.local`에 키를 저장한 뒤 기존 키 사용 안내 |

첫 프롬프트는 다음처럼 입력할 수 있습니다. Codex에서 설치된 `grill-with-docs` 스킬을 함께 선택합니다.

```text
grill-with-docs 스킬을 사용해서 요구사항을 구체화해줘.
OpenAI Agents SDK를 사용해 ‘서울 문화행사 추천 Agent’를 만들고 싶어.
대표 질문은 “이번 주말 종로에서 볼 수 있는 무료 전시 3개 찾아줘.”야.
합의한 요구사항은 requirements.md에, 용어는 CONTEXT.md에 기록해줘.
```

기록의 `1-C`, `5~10 모두 추천대로` 같은 답변은 **당시 질문 번호와 추천안**에 대응합니다. 현재 Codex가 제시한 질문과 다르면 원하는 조건을 문장으로 답하세요. 구현 경로도 자신의 실습 폴더로 바꿉니다.

API 키는 채팅에 붙여넣지 않고, 생성된 앱이 읽는 위치의 `.env.local`에 저장합니다. 키를 저장하기 전에는 기록의 마지막 프롬프트를 그대로 보내지 마세요. Codex 사용 권한과 앱의 OpenAI API 사용은 별도이며, 앱 실행에는 API 사용량이 발생합니다.

기록은 기존 키 사용을 확정하는 프롬프트에서 끝납니다. 이후 Codex가 구현을 완료하면 앱을 실행하고 대표 질문과 경계 사례를 확인합니다. 완성 예제에 들어 있는 전시 1,000건은 이 기록 이후 추가한 데이터이므로, 같은 구성을 원하면 다음 요청을 이어서 입력합니다.

```text
서울시 공식 공개 데이터에서 전시 데이터를 1,000건 정도 내려받아
저장 데이터 모드에서 사용할 수 있게 해줘.
실제 원본을 사용하고, 출처·수집 시각·시연 기준일·선정 범위를 기록해줘.
```

## 4. 결과물 확인 방법

완성 예제는 [**`solution` 브랜치의 `solution/` 폴더**](https://github.com/ksmin23/seoul-culture-pick-demo/tree/solution/solution)에서 확인합니다. 자신의 결과와 코드가 완전히 같을 필요는 없습니다. [요구사항](./requirements.md)의 동작과 완료 기준을 기준으로 비교하세요.

```text
저장소 루트/
├── README.md                              # 실습 안내
├── CONTEXT.md                             # 용어와 공통 기준
├── requirements.md                        # 요구사항과 완료 기준
├── to-questionnaire-seoul-culture-pick.md  # 프롬프트·답변 기록
└── solution/                              # solution 브랜치의 완성 예제
    ├── README.md                          # 앱 설정·실행 상세 안내
    ├── streamlit_app.py                   # 웹 화면
    ├── app/                               # Agent·조회 도구·조건 검사
    ├── data/                              # 원본과 전시 1,000건 저장본
    ├── scripts/                           # 데이터 갱신·가져오기·실행 검증
    ├── tests/                             # 자동화 테스트
    └── docs/                              # 시연 대본·검증 기록
```

### 완성 예제 실행

실습 폴더와 별도의 위치에 저장소를 내려받습니다.

```bash
git clone --branch solution https://github.com/ksmin23/seoul-culture-pick-demo.git
cd seoul-culture-pick-demo/solution
uv sync --frozen
```

`solution/.env.example`을 참고해 `solution/.env.local`을 만들고 `OPENAI_API_KEY`를 설정합니다. 실제 API 모드에는 `SEOUL_API_KEY`도 설정합니다. 기존 `.env.local`이 있다면 덮어쓰지 않습니다.

```bash
uv run streamlit run streamlit_app.py
```

브라우저에서 `http://localhost:8501`을 열고 **저장 데이터** 모드로 대표 질문을 입력합니다. 저장본의 시연 기준일은 **2026-09-28**이며, 서울시 공식 데이터에서 선정한 전시 1,000건을 사용합니다. 저장 모드도 모델 호출을 위해 인터넷과 OpenAI API 키가 필요합니다.

다음 항목을 확인합니다.

- 대표 질문에서 날짜·종로구·무료 조건과 추천 카드의 원문 링크가 표시되는가?
- 펼쳐 보는 실행 과정에서 도구 입력, 조회 건수, 검증 결과를 확인할 수 있는가?
- 결과가 없는 조건에서 가짜 전시를 추가하지 않는가?
- 실제 API 조회가 실패했을 때 명시적으로 오류를 안내하는가?

자동화 테스트는 `solution/`에서 `uv run pytest -q`로 실행합니다. 자세한 설정과 저장본 갱신 방법은 [완성 예제 README](https://github.com/ksmin23/seoul-culture-pick-demo/blob/solution/solution/README.md), 단계별 시연은 [시연 대본](https://github.com/ksmin23/seoul-culture-pick-demo/blob/solution/solution/docs/demo-script.md)을 참고하세요.

## 5. 참고 자료

### 실습용 스킬 GitHub

- [mattpocock/skills — 전체 스킬과 설치 방법](https://github.com/mattpocock/skills)
- [grill-with-docs — 요구사항 인터뷰와 문서화](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs)
- [grilling — 요구사항 인터뷰](https://github.com/mattpocock/skills/tree/main/skills/productivity/grilling)
- [domain-modeling — 도메인 용어와 모델 정리](https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling)
- [to-questionnaire — 질문·응답 기록 정리](https://github.com/mattpocock/skills/tree/main/skills/productivity/to-questionnaire)

### 구현과 공공데이터

- [OpenAI Agents SDK Python](https://github.com/openai/openai-agents-python)
- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [서울 열린데이터광장 — 서울시 문화행사 정보](https://data.seoul.go.kr/dataList/OA-15486/S/1/datasetView.do)

공공데이터 출처는 서울특별시이며, 공공누리 제1유형에 따라 출처를 표시합니다. 행사 기간과 실제 개관일·예약 가능 여부는 다를 수 있으므로 추천 카드의 원문도 함께 확인합니다.
