import streamlit as st

from app.agent import recommend
from app.config import SOURCE_URL, load_settings
from app.dates import today_seoul
from app.errors import AppError
from app.snapshots import load_snapshot

st.set_page_config(page_title="서울컬처픽 · 전시 추천", page_icon="🎨", layout="centered")
settings = load_settings()


def retry_from_snapshot():
    failure = st.session_state.get("failure")
    if failure:
        st.session_state.data_mode = "snapshot"
        st.session_state.retry_question = failure["question"]
        st.session_state.pop("failure", None)


def render_result(record):
    with st.chat_message("user"):
        st.write(record["question"])
    with st.chat_message("assistant", avatar="🎨"):
        label = "저장 데이터" if record["mode"] == "snapshot" else "실제 API"
        st.caption(f"{label} · 시연/검색 기준일 {record['reference_date']}")
        meta = record.get("metadata")
        if meta:
            st.caption(f"수집: {meta['collected_at']} · 조회 범위 {meta['row_count']}건")
            if not meta["complete"]:
                st.warning(meta["scope"] + " — 아래 결과는 저장된 범위 안에서만 검색한 결과입니다.")
        answer = record["answer"]
        if answer["status"] == "clarification":
            st.info(answer["message"])
        else:
            result = record["search"]
            request = result["request"]
            fee = {"all": "유무료 전체", "free": "무료", "paid": "유료"}[request["fee"]]
            districts = ", ".join(request["districts"]) or "서울 전체"
            st.markdown(f"**{result['start']} ~ {result['end']} · {districts} · {fee}**")
            st.caption(
                f"적용 조건: 전시/미술 · 요청 {request['limit']}개. 생략된 날짜·지역·요금·개수에는 기본값을 적용합니다."
            )
            st.write(f"조회 범위 안에서 조건에 맞는 전시 {result['total_matches']}개를 찾았습니다.")
            reasons = {pick["event_id"]: pick["reason"] for pick in answer["selections"]}
            for event in result["candidates"]:
                with st.container(border=True):
                    st.subheader(event["title"], anchor=False)
                    st.caption(f"{event['district']} · {event['start']} ~ {event['end']}")
                    st.write("장소: " + (event["place"] or "정보 없음"))
                    status = {"free": "무료", "paid": "유료", "unknown": "확인 필요"}[
                        event["fee_status"]
                    ]
                    st.write(
                        "요금: " + status + (" · " + event["fee_text"] if event["fee_text"] else "")
                    )
                    if event["hours"]:
                        st.write("운영 안내: " + event["hours"])
                    st.write(reasons[event["id"]])
                    if event["url"]:
                        st.link_button("전시 원문 보기 ↗", event["url"])
                    else:
                        st.caption("원문 링크가 제공되지 않았습니다.")
            if len(result["candidates"]) < request["limit"]:
                st.info(
                    "조건을 자동으로 바꾸지 않았습니다. 다른 날짜·지역·요금 조건으로 새 질문을 입력해 보세요."
                )
            st.caption(
                "행사 기간 기준 후보입니다. 실제 개관·휴관 및 예약 여부는 원문에서 확인해 주세요."
            )
            if result["skipped_rows"]:
                st.caption(
                    f"날짜 등 필수 정보가 불완전한 {result['skipped_rows']}건은 제외했습니다."
                )
        with st.expander("도구 실행 과정 보기"):
            for event in record["events"]:
                st.write(event["stage"])
                st.json(event["details"])


with st.sidebar:
    st.markdown("### SEOUL CULTURE PICK")
    st.caption("공공데이터로 고르는 이번 주말 전시")
    st.radio(
        "데이터 모드",
        ["snapshot", "live"],
        key="data_mode",
        format_func=lambda mode: "저장 데이터" if mode == "snapshot" else "실제 API",
    )
    mode = st.session_state.data_mode
    if mode == "snapshot":
        try:
            meta = load_snapshot(settings.snapshot_path).metadata
            st.write(f"시연 기준일: {meta.reference_date}")
            st.caption(f"수집 시각: {meta.collected_at.isoformat()}")
            st.caption(meta.scope)
        except AppError as error:
            st.warning(error.message)
    else:
        st.write(f"검색 기준일: {today_seoul()}")
        if not settings.seoul_key:
            st.warning("전체 데이터 조회에는 SEOUL_API_KEY가 필요합니다.")
    st.caption("두 모드 모두 OpenAI API로 Agent를 실행합니다.")
    if not settings.openai_key:
        st.warning("OPENAI_API_KEY 설정이 필요합니다.")
    st.divider()
    st.caption("이전 대화는 화면에만 남습니다. 새 질문은 독립적으로 처리합니다.")
    if st.button("화면 기록 지우기", use_container_width=True):
        st.session_state.records = []
        st.session_state.pop("failure", None)
        st.rerun()
    st.link_button("서울시 데이터 출처 ↗", SOURCE_URL)
    st.caption("서울특별시 · 공공누리 제1유형 출처표시")

st.title("서울컬처픽")
st.markdown("### 이번 주말, 어떤 전시를 볼까요?")
st.caption("날짜·지역·요금을 말해 주세요. 조회한 전시만 골라 드립니다.")
with st.expander("이렇게 질문해 보세요", expanded=not st.session_state.get("records")):
    st.code("이번 주말 종로에서 볼 수 있는 무료 전시 3개 찾아줘.", language=None)
    st.code("이번 주말 서울 무료 전시 3개 추천해줘.", language=None)
    st.caption("조건을 생략하면 이번 주말 · 서울 전체 · 유무료 전체 · 3개로 검색합니다.")

if "records" not in st.session_state:
    st.session_state.records = []
for record in st.session_state.records:
    render_result(record)

question = st.chat_input(
    "예: 이번 주말 종로 무료 전시 3개", max_chars=2000
) or st.session_state.pop("retry_question", None)
run_mode = mode
failure = st.session_state.get("failure")
if failure and not question:
    st.error(failure["message"])
    with st.expander("실패한 요청의 실행 과정"):
        st.write(failure["question"])
        st.json(failure["events"])
    if failure["allow_snapshot"]:
        st.button("저장 데이터로 다시 실행", type="primary", on_click=retry_from_snapshot)

if question:
    st.session_state.pop("failure", None)
    observed = []
    with st.status("조건을 해석하고 전시를 찾고 있습니다…", expanded=True) as status:

        def report(label, details):
            observed.append({"stage": label, "details": details})
            st.write(label)
            st.json(details)

        try:
            record = recommend(question, run_mode, settings, report=report)
            st.session_state.records.append(record)
            status.update(label="추천 완료", state="complete", expanded=False)
        except AppError as error:
            st.session_state.failure = {
                "question": question,
                "message": error.message,
                "allow_snapshot": error.allow_snapshot,
                "events": observed,
            }
            status.update(label="요청을 완료하지 못했습니다", state="error")
    st.rerun()
