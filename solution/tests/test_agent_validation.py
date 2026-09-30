from datetime import date

import pytest

from app.agent import validate_answer
from app.config import Settings
from app.errors import AppError
from app.schemas import AgentAnswer, SearchRequest, Selection
from app.search import search_rows
from app.tools import ExhibitionContext


def test_hallucinated_id_blocked(row):
    state = ExhibitionContext(Settings(), "snapshot", date(2026, 9, 28))
    state.result = search_rows([row], SearchRequest(), state.reference_date)
    answer = AgentAnswer(
        status="results", message="", selections=[Selection(event_id="invented", reason="test")]
    )
    with pytest.raises(AppError, match="조회 결과"):
        validate_answer(answer, state)


def test_result_without_tool_blocked():
    state = ExhibitionContext(Settings(), "snapshot", date(2026, 9, 28))
    with pytest.raises(AppError, match="조회 없이"):
        validate_answer(AgentAnswer(status="results", message="", selections=[]), state)


def test_no_results_is_valid(row):
    state = ExhibitionContext(Settings(), "snapshot", date(2026, 9, 28))
    state.result = search_rows([], SearchRequest(), state.reference_date)
    validate_answer(AgentAnswer(status="results", message="", selections=[]), state)


def test_tool_reports_on_calling_thread(row):
    # SDK는 동기 도구를 작업 스레드에서 실행하므로 Streamlit 콜백은 비동기 도구로 유지한다.
    import asyncio
    import json
    import threading
    from datetime import datetime, timezone

    from agents.tool_context import ToolContext

    from app.schemas import Dataset, DatasetMeta
    from app.tools import search_exhibitions

    caller = threading.get_ident()
    observed = []
    dataset = Dataset(
        metadata=DatasetMeta(
            source_url="https://example.org",
            collected_at=datetime.now(timezone.utc),
            reference_date=date(2026, 9, 28),
            scope="test",
            complete=False,
            source_total=1,
            row_count=1,
        ),
        rows=[row],
    )
    state = ExhibitionContext(
        Settings(),
        "snapshot",
        date(2026, 9, 28),
        dataset=dataset,
        report=lambda label, details: observed.append(threading.get_ident()),
    )
    arguments = json.dumps({"request": SearchRequest().model_dump()})
    asyncio.run(
        search_exhibitions.on_invoke_tool(
            ToolContext(
                context=state,
                tool_name="search_exhibitions",
                tool_call_id="test",
                tool_arguments=arguments,
            ),
            arguments,
        )
    )
    assert observed and all(thread == caller for thread in observed)


def test_missing_seoul_key_does_not_call_model(monkeypatch):
    from app.agent import recommend

    async def unexpected(*args, **kwargs):
        raise AssertionError("Missing Seoul key should be checked before a model request")

    monkeypatch.setattr("app.agent.Runner.run", unexpected)
    with pytest.raises(AppError) as error:
        recommend("종로 무료 전시", "live", Settings(openai_key="test-only"))
    assert error.value.code == "seoul_key_missing"
    assert error.value.allow_snapshot


def test_sdk_wrapped_tool_error_preserves_recovery(monkeypatch):
    from agents.exceptions import UserError

    from app.agent import recommend

    async def wrapped_error(*args, **kwargs):
        try:
            raise AppError("seoul_connection", "연결 실패", allow_snapshot=True)
        except AppError as cause:
            raise UserError("wrapped") from cause

    monkeypatch.setattr("app.agent.Runner.run", wrapped_error)
    with pytest.raises(AppError) as error:
        recommend("종로 무료 전시", "snapshot", Settings(openai_key="test-only"))
    assert error.value.code == "seoul_connection"
    assert error.value.allow_snapshot
