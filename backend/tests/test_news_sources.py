"""Offline contract fixtures: provenance, dates, company identity and fetch limits."""

import json
import socket
import time

import pytest

from scraping import research_sources as sources
from scraping.enhanced_news_scraper import EnhancedNewsScraper, fetch_enhanced_news_with_results


class Response:
    def __init__(self, payload=b"", status=200, headers=None):
        self.payload = payload
        self.status_code = status
        self.headers = headers or {}
        self.closed = False

    def iter_content(self, chunk_size):
        for offset in range(0, len(self.payload), chunk_size):
            yield self.payload[offset:offset + chunk_size]

    def close(self):
        self.closed = True


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(sources.socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    monkeypatch.delenv("STOCKSCOPE_GDELT_ENABLED", raising=False)
    monkeypatch.delenv("STOCKSCOPE_IR_ENABLED", raising=False)


def gdelt_response(items):
    return Response(json.dumps({"articles": items}).encode())


def article(title="NVIDIA reports results", url="https://publisher.example/article", **kwargs):
    return {"title": title, "url": url, "seendate": "20260411T131500Z", "domain": "untrusted-name.example", **kwargs}


def test_gdelt_alias_query_and_discovery_are_not_publication_or_sentiment():
    session = Session([gdelt_response([article()])])
    adapter = sources.ResearchNewsSources(session=session)
    item = adapter.fetch_gdelt("NVDA")[0]
    params = session.calls[0][1]["params"]
    assert params["query"] == '("NVIDIA" OR "NVIDIA Corporation") sourcelang:english'
    assert params["maxrecords"] == 20
    assert item["publishedAt"] is item["publication_date_source"] is item["sentiment"] is None
    assert item["provider_seen_at"] == "2026-04-11T13:15:00+00:00"
    assert item["original_source"] == "publisher.example"  # linked host, not a claimed domain
    assert item["provider"] == "gdelt" and item["source_type"] == "news"
    assert "first_seen_at" not in item


def test_gdelt_rejects_ambiguous_symbols_and_unrelated_headlines():
    session = Session([gdelt_response([
        article("META sculpture opens at museum"), article("Metaphysical art grows"),
        article("Meta Platforms announces earnings", url="https://publisher.example/meta"),
    ])])
    adapter = sources.ResearchNewsSources(session=session)
    assert adapter.fetch_gdelt("T") == []  # no unreviewed ticker fallback
    assert len(session.calls) == 0
    records = adapter.fetch_gdelt("META")
    assert len(records) == 1 and records[0]["matched_aliases"] == ["Meta Platforms"]
    assert '"META"' not in session.calls[0][1]["params"]["query"]


def test_gdelt_canonical_duplicates_and_company_domain_classification():
    session = Session([gdelt_response([
        article(url="https://nvidianews.nvidia.com/releases/results?utm_source=x#top"),
        article(url="https://nvidianews.nvidia.com/releases/results?utm_source=y"),
        article(url="https://nvidia.com.publisher.example/article", seendate="bad date"),
        article(url="http://127.0.0.1/internal"),
    ])])
    records = sources.ResearchNewsSources(session=session).fetch_gdelt("NVDA")
    assert len(records) == 2
    assert records[0]["source_type"] == "company_release"
    assert records[0]["url"] == "https://nvidianews.nvidia.com/releases/results"
    assert records[1]["source_type"] == "news" and records[1]["provider_seen_at"] is None


def test_official_rss_preserves_explicit_dates_and_does_not_score_releases():
    payload = b'''<?xml version="1.0"?><rss version="2.0"><channel><title>NVIDIA</title>
      <item><title>Company results</title><link>https://nvidianews.nvidia.com/releases/results?utm_source=rss</link>
      <description>&lt;p&gt;Reported &lt;b&gt;results&lt;/b&gt;.&lt;/p&gt;</description><pubDate>Sat, 11 Apr 2026 09:15:00 -0400</pubDate></item>
      <item><title>Duplicate results</title><link>https://nvidianews.nvidia.com/releases/results#top</link></item>
      <item><title>Date unavailable</title><link>https://nvidianews.nvidia.com/releases/unknown</link><pubDate>2026-04-11T09:00:00</pubDate></item>
      <item><title>Updated only</title><link>https://nvidianews.nvidia.com/releases/updated</link><updated>2026-04-12T10:00:00Z</updated></item>
      </channel></rss>'''
    session = Session([Response(payload)])
    records = sources.ResearchNewsSources(session=session).fetch_company_ir("NVDA")
    assert len(records) == 3
    assert records[0]["publishedAt"] == "2026-04-11T13:15:00+00:00"
    assert records[1]["publishedAt"] is records[2]["publishedAt"] is None
    assert all(item["source_type"] == "company_release" and item["sentiment"] is None for item in records)
    assert "<" not in records[0]["description"]
    assert session.calls[0][0] == "https://nvidianews.nvidia.com/cats/press_release.xml"


@pytest.mark.parametrize("response", [Response(b"rate limited", status=429), Response(b"not json"), Response(b'{"error":"unavailable"}'), Response(b"", status=302, headers={"Location": "http://169.254.169.254/"})])
def test_bad_provider_response_is_explicit_failure_without_retry(response):
    session = Session([response])
    adapter = sources.ResearchNewsSources(session=session)
    assert adapter.fetch_gdelt("NVDA") == []
    assert adapter.last_results["gdelt"]["status"] == "failed"
    assert len(session.calls) == 1 and session.calls[0][1]["allow_redirects"] is False
    assert response.closed


def test_size_limit_checks_declared_and_streamed_bytes(monkeypatch):
    monkeypatch.setattr(sources, "MAX_RESPONSE_BYTES", 10)
    for response in [Response(b"{}", headers={"Content-Length": "11"}), Response(b" " * 11)]:
        adapter = sources.ResearchNewsSources(session=Session([response]))
        assert adapter.fetch_gdelt("NVDA") == []
        assert "size limit" in adapter.last_results["gdelt"]["reason"]
        assert response.closed


def test_private_dns_is_rejected_before_transport(monkeypatch):
    monkeypatch.setattr(sources.socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 443))])
    session = Session([])
    adapter = sources.ResearchNewsSources(session=session)
    assert adapter.fetch_company_ir("NVDA") == []
    assert adapter.last_results["company_ir_rss"]["status"] == "failed"
    assert not session.calls


def test_disabled_missing_config_and_expired_budget_make_no_request(monkeypatch):
    session = Session([])
    adapter = sources.ResearchNewsSources(session=session)
    assert adapter.fetch_company_ir("AAPL") == []
    assert adapter.last_results["company_ir_rss"]["status"] == "not_configured"
    assert adapter.fetch_gdelt("NVDA", deadline=time.monotonic() - 1) == []
    assert adapter.last_results["gdelt"]["status"] == "budget_exhausted"
    monkeypatch.setenv("STOCKSCOPE_GDELT_ENABLED", "false")
    assert adapter.fetch_gdelt("NVDA") == []
    assert adapter.last_results["gdelt"]["status"] == "disabled"
    assert not session.calls


def test_registry_rejects_bare_tickers_and_non_https_feeds(tmp_path):
    path = tmp_path / "feeds.json"
    for company in [{"aliases": ["AAPL"]}, {"aliases": ["Apple Inc"], "ir_feeds": [{"url": "http://example.org/feed"}]}]:
        path.write_text(json.dumps({"version": 1, "companies": {"AAPL": company}}))
        with pytest.raises(sources.SourceFetchError):
            sources.load_source_config(path)


def _stub_collectors(monkeypatch):
    for method in ["fetch_company_ir", "fetch_gdelt", "fetch_yahoo_finance_news", "fetch_gnews", "fetch_rss_feeds", "fetch_finviz_news", "fetch_stocktwits"]:
        monkeypatch.setattr(EnhancedNewsScraper, method, lambda self, ticker: [])


def test_collector_keeps_source_contract_deduplicates_links_and_reports_outcomes(monkeypatch):
    _stub_collectors(monkeypatch)
    monkeypatch.setattr(EnhancedNewsScraper, "fetch_company_ir", lambda self, ticker: [{
        "title": "NVIDIA company results", "url": "https://nvidianews.nvidia.com/results?utm_medium=rss",
        "source": "NVIDIA", "source_type": "company_release", "sentiment": None, "publishedAt": None}])
    monkeypatch.setattr(EnhancedNewsScraper, "fetch_yahoo_finance_news", lambda self, ticker: [{
        "title": "Same release, different title", "url": "https://nvidianews.nvidia.com/results", "source": "Yahoo Finance", "sentiment": {"compound": .8}}])
    captured = []
    monkeypatch.setattr("scraping.enhanced_news_scraper.save_records", lambda ticker, suffix, records: captured.extend(records) or "fixture-reference")
    result = fetch_enhanced_news_with_results("NVDA")
    assert result["reference"] == "fixture-reference" and len(captured) == 1
    assert captured[0]["source_type"] == "company_release" and captured[0]["sentiment"] is None
    assert captured[0]["publishedAt"] is None
    assert result["providers"]["company_ir_rss"] == {"status": "ok", "count": 1}


def test_failed_provider_does_not_drop_successful_provider_records(monkeypatch):
    _stub_collectors(monkeypatch)
    def failure(self, ticker):
        raise TimeoutError("fixture timeout")
    monkeypatch.setattr(EnhancedNewsScraper, "fetch_gdelt", failure)
    monkeypatch.setattr(EnhancedNewsScraper, "fetch_yahoo_finance_news", lambda self, ticker: [{"title": "Observed story", "url": "https://publisher.example/story", "source": "Publisher"}])
    captured = []
    monkeypatch.setattr("scraping.enhanced_news_scraper.save_records", lambda ticker, suffix, records: captured.extend(records) or "fixture-reference")
    result = fetch_enhanced_news_with_results("NVDA")
    assert len(captured) == 1 and result["providers"]["gdelt"]["status"] == "failed"


def test_empty_collection_preserves_saved_snapshot(monkeypatch):
    _stub_collectors(monkeypatch)
    monkeypatch.setattr("scraping.enhanced_news_scraper.save_records", lambda *args: pytest.fail("Empty collection must not overwrite evidence"))
    assert fetch_enhanced_news_with_results("NVDA")["reference"] is None


def test_collection_budget_prevents_starting_later_providers(monkeypatch):
    _stub_collectors(monkeypatch)
    current_time = [100.0]
    monkeypatch.setattr("scraping.enhanced_news_scraper.time.monotonic", lambda: current_time[0])
    def consume_budget(self, ticker):
        current_time[0] += 60
        return []
    monkeypatch.setattr(EnhancedNewsScraper, "fetch_company_ir", consume_budget)
    monkeypatch.setattr(EnhancedNewsScraper, "fetch_gdelt", lambda *args: pytest.fail("Expired budget must not start another provider"))
    result = fetch_enhanced_news_with_results("NVDA")
    assert result["reference"] is None
    assert result["providers"]["gdelt"]["status"] == "budget_exhausted"
    assert result["providers"]["yahoo_finance"]["status"] == "budget_exhausted"


def test_deadline_exhausted_during_download_closes_response(monkeypatch):
    current_time = [100.0]
    monkeypatch.setattr(sources.time, "monotonic", lambda: current_time[0])
    class SlowResponse(Response):
        def iter_content(self, chunk_size):
            current_time[0] += 11
            yield b'{"articles":[]}'
    response = SlowResponse()
    adapter = sources.ResearchNewsSources(session=Session([response]))
    assert adapter.fetch_gdelt("NVDA") == []
    assert "budget exhausted" in adapter.last_results["gdelt"]["reason"]
    assert response.closed
