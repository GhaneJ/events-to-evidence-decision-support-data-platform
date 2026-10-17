from datetime import datetime

import httpx
import pytest

from evidence_intelligence.sources.arbetsformedlingen import JobStreamClient


def test_jobstream_uses_v2_ndjson_and_repeatable_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stream"
        assert request.headers["accept"] == "application/jsonl"
        assert request.url.params["updated-after"] == "2026-10-17T10:00:00"
        assert request.url.params["updated-before"] == "2026-10-17T11:00:00"
        assert request.url.params.get_list("occupation-concept-id") == ["data-it", "developer"]
        return httpx.Response(
            200,
            text='{"id":"a1"}\n{"id":"a2"}\n',
            headers={"content-type": "application/jsonl"},
        )

    with JobStreamClient(transport=httpx.MockTransport(handler)) as client:
        lines = list(
            client.iter_changes(
                datetime(2026, 10, 17, 10, 0, 0),
                updated_before=datetime(2026, 10, 17, 11, 0, 0),
                occupation_concept_ids=("data-it", "developer"),
            )
        )

    assert lines == ['{"id":"a1"}', '{"id":"a2"}']


def test_jobstream_rejects_reverse_window() -> None:
    with JobStreamClient(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
        with pytest.raises(ValueError, match="later than"):
            list(
                client.iter_changes(
                    datetime(2026, 10, 17, 11, 0, 0),
                    updated_before=datetime(2026, 10, 17, 10, 0, 0),
                )
            )
