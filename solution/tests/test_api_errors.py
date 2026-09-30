import httpx
import pytest

from app.errors import AppError
from app.seoul_api import fetch_exhibitions


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_key_is_required():
    with pytest.raises(AppError) as error:
        fetch_exhibitions("")
    assert error.value.code == "seoul_key_missing"
    assert error.value.allow_snapshot


def test_pagination_collects_every_page(row):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        batch = [row] * (1000 if len(calls) == 1 else 1)
        return httpx.Response(
            200,
            json={
                "culturalEventInfo": {
                    "list_total_count": 1001,
                    "RESULT": {"CODE": "INFO-000"},
                    "row": batch,
                }
            },
        )

    with client(handler) as http:
        dataset = fetch_exhibitions("test-key", client=http)
    assert len(dataset.rows) == 1001
    assert len(calls) == 2
    assert "/1001/2000/" in calls[1]
    assert dataset.metadata.complete


def test_public_sample_is_labelled_partial(row):
    with client(
        lambda request: httpx.Response(
            200,
            json={
                "culturalEventInfo": {
                    "list_total_count": 333,
                    "RESULT": {"CODE": "INFO-000"},
                    "row": [row] * 5,
                }
            },
        )
    ) as http:
        dataset = fetch_exhibitions("sample", sample=True, client=http)
    assert not dataset.metadata.complete
    assert dataset.metadata.row_count == 5
    assert dataset.metadata.source_total == 333


def test_auth_error_never_discloses_key():
    with client(
        lambda request: httpx.Response(
            200, json={"RESULT": {"CODE": "INFO-100", "MESSAGE": "secret-test-key"}}
        )
    ) as http:
        with pytest.raises(AppError) as error:
            fetch_exhibitions("secret-test-key", client=http)
    assert error.value.code == "seoul_auth"
    assert "secret-test-key" not in str(error.value)


def test_timeout_safe_message():
    def timeout(request):
        raise httpx.ReadTimeout("URL contains secret-test-key", request=request)

    with client(timeout) as http:
        with pytest.raises(AppError) as error:
            fetch_exhibitions("secret-test-key", client=http)
    assert error.value.code == "seoul_connection"
    assert "secret-test-key" not in str(error.value)


def test_partial_page_failure_is_not_silently_successful(row):
    count = 0

    def handler(request):
        nonlocal count
        count += 1
        return httpx.Response(
            200,
            json={
                "culturalEventInfo": {
                    "list_total_count": 1001,
                    "RESULT": {"CODE": "INFO-000"},
                    "row": [row] * 1000 if count == 1 else [],
                }
            },
        )

    with client(handler) as http:
        with pytest.raises(AppError) as error:
            fetch_exhibitions("test-key", client=http)
    assert error.value.code == "seoul_incomplete"
