import httpx
import pytest

from evidence_intelligence.sources.arbetsformedlingen import JobSearchClient


def test_search_uses_public_jobsearch_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        assert request.url.params["q"] == "python"
        assert request.url.params["limit"] == "25"
        assert request.url.params["offset"] == "50"
        assert request.url.params["occupation-field"] == "apaJ_2ja_LuF"
        return httpx.Response(200, json={"total": {"value": 1}, "hits": [{"id": "abc"}]})

    transport = httpx.MockTransport(handler)
    with JobSearchClient(transport=transport) as client:
        payload = client.search(
            "python",
            limit=25,
            offset=50,
            occupation_field="apaJ_2ja_LuF",
        )

    assert payload["hits"][0]["id"] == "abc"


def test_get_ad_uses_ad_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ad/abc"
        return httpx.Response(200, json={"id": "abc", "headline": "Data engineer"})

    with JobSearchClient(transport=httpx.MockTransport(handler)) as client:
        payload = client.get_ad("abc")

    assert payload["headline"] == "Data engineer"


def test_search_rejects_limit_above_api_page_limit() -> None:
    with JobSearchClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))) as client:
        with pytest.raises(ValueError, match="between 1 and 100"):
            client.search("python", limit=101)
