"""Offline fixtures for trustworthy research, source dates, and refresh outcomes."""

import asyncio
import importlib
import json
import time
from datetime import datetime, timezone

import pytest
from fastapi import BackgroundTasks, HTTPException

from backend.services.research import load_evidence, sentiment_metrics, source_analyses, save_records


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ADMIN_PASSWORD", "fixture-admin")
    monkeypatch.setenv("DEMO_PASSWORD", "fixture-demo")
    monkeypatch.setenv("GUEST_PASSWORD", "fixture-guest")
    monkeypatch.setenv("STOCKSCOPE_PASSWORD", "fixture-admin")
    monkeypatch.setenv("SECRET_KEY", "fixture-signing-key-not-a-password-1234567890")
    monkeypatch.setenv("STOCKSCOPE_DATA_DIR", str(tmp_path))
    module = importlib.import_module("backend.api")
    module.analysis_status.clear()
    module.cache.invalidate()
    yield module
    module.analysis_status.clear()
    module.cache.invalidate()


def test_original_dates_unknown_dates_and_legacy_sec_are_not_invented(api):
    save_records("AAPL", "comprehensive_news", [
        {"title": "Dated article", "url": "https://example.org/news", "created_utc": 1609459200, "source": "Publisher", "sentiment": {"compound": .4}},
        {"title": "Undated article", "source": "Publisher", "publishedAt": "bad date", "sentiment": {"compound": None}},
        {"title": "Social post", "source": "Stocktwits", "sentiment": {"compound": 1}},
    ])
    save_records("AAPL", "news_sentiment", [{"title": "Duplicate", "url": "https://example.org/news", "sentiment": {"compound": -.9}}])
    save_records("AAPL", "sec_sentiment", [{"form_type": "10-K", "filing_date": "2020-10-01", "url": "https://www.sec.gov/filing", "sentiment_context": "made-up boilerplate", "sentiment": {"compound": .99}}])
    save_records("AAPL", "reddit_sentiment", [{"title": "Legacy sample", "sentiment": {"compound": -1}}])
    frame = load_evidence("AAPL")
    assert len(frame) == 4  # duplicate and unsupported legacy snapshots excluded
    dated = frame[frame["title"] == "Dated article"].iloc[0]
    assert dated["original_created_utc"] == 1609459200
    assert dated["created_utc"].year == 2021
    sec = frame[frame["source"] == "SEC"].iloc[0]
    assert sec["created_utc"].year == 2020
    assert sec["filing_date"] == "2020-10-01"
    assert sentiment_metrics(frame)["avg_sentiment"] == .4
    assert sentiment_metrics(frame)["sample_size"] == 1
    publisher = next(row for row in source_analyses(frame) if row["source"] == "Publisher")
    assert publisher["freshness"] == "unknown"
    assert publisher["unknown_timestamps"] == 1
    assert publisher["latest_update"].year == 2021


def test_new_item_does_not_hide_stale_sample(api):
    save_records("AAPL", "news_sentiment", [
        {"title": "Old", "source": "Publisher", "publishedAt": "2020-01-01"},
        {"title": "New", "source": "Publisher", "publishedAt": datetime.now(timezone.utc).isoformat()},
    ])
    assert source_analyses(load_evidence("AAPL"))[0]["freshness"] == "stale"


def test_active_analysis_never_returns_predictions_or_fabricated_metrics(api):
    save_records("AAPL", "sec_sentiment", [{"form_type": "10-K", "filing_date": "2020-10-01", "url": "https://www.sec.gov/filing", "sentiment": {"compound": .99}}])
    analysis = asyncio.run(api.get_stock_analysis("AAPL", "demo")).model_dump(mode="json")
    assert analysis["sentiment_metrics"]["avg_sentiment"] is None
    assert analysis["sentiment_metrics"]["sample_size"] == 0
    assert analysis["last_updated"].startswith("2020-10-01")
    assert analysis["filings"][0]["url"] == "https://www.sec.gov/filing"
    research = asyncio.run(api.get_investment_advice("AAPL", "demo"))
    assert research["status"] == "research_only"
    for payload in (research, analysis, analysis["sentiment_metrics"]):
        assert not {"recommendation", "confidence", "confidence_score", "target_price", "data_quality_score"}.intersection(payload)
    quantitative = asyncio.run(api.get_quantitative_analysis("AAPL", "demo"))
    assert quantitative["status"] == "unavailable"
    assert quantitative["metrics"] == quantitative["signals"] == quantitative["strategies"] == {}


def test_missing_timestamps_remain_null_in_endpoint(api):
    save_records("AAPL", "news_sentiment", [{"title": "Unknown date", "sentiment": {"compound": .2}}])
    result = asyncio.run(api.get_stock_analysis("AAPL", "demo"))
    assert result.last_updated is None
    assert result.source_as_of is None
    assert result.freshness == "unknown"
    assert result.sources[0].latest_update is None


def test_saved_data_does_not_fabricate_completed_job(api):
    save_records("AAPL", "news_sentiment", [{"title": "Existing"}])
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.get_analysis_status("AAPL", "demo"))
    assert error.value.status_code == 404


def _job(api, symbol="AAPL"):
    api.analysis_status[symbol] = api.AnalysisStatus(symbol=symbol, status="pending", progress=0, message="Queued", started_at=datetime.now(timezone.utc))
    return api.analysis_status[symbol]


def test_jobs_fail_when_no_provider_produces_records(api, monkeypatch):
    async def no_sec(symbol):
        return {"sec": None}
    monkeypatch.setattr(api, "run_full_pipeline_async", no_sec)
    monkeypatch.setattr(api, "_collect_news", lambda symbol: None)
    job = _job(api)
    asyncio.run(api.run_optimized_analysis("AAPL", ["sec", "news"]))
    assert job.status == "failed"
    assert all(provider["count"] == 0 for provider in job.providers.values())
    assert job.completed_at is not None


def test_jobs_report_partial_and_scraping_does_not_block_event_loop(api, monkeypatch):
    path = save_records("AAPL", "news_sentiment", [{"title": "Observed article"}])
    async def no_sec(symbol):
        return {"sec": None}
    def slow_news(symbol):
        time.sleep(.2)
        return path
    monkeypatch.setattr(api, "run_full_pipeline_async", no_sec)
    monkeypatch.setattr(api, "_collect_news", slow_news)
    job = _job(api)
    async def exercise():
        task = asyncio.create_task(api.run_optimized_analysis("AAPL", ["sec", "news"]))
        await asyncio.sleep(.01)
        assert not task.done()  # a synchronous collector would already have blocked .2s
        status = await asyncio.wait_for(api.get_analysis_status("AAPL", "demo"), .05)
        assert status.status == "processing"
        await task
    asyncio.run(exercise())
    assert job.status == "partial"
    assert job.providers["news"]["count"] == 1
    assert job.providers["sec"]["status"] == "no_data"


def test_pending_jobs_deduplicate_and_active_jobs_are_bounded(api):
    async def exercise():
        tasks = BackgroundTasks()
        await api.analyze_stock(api.StockRequest(symbol="AAPL"), tasks, "demo")
        await api.analyze_stock(api.StockRequest(symbol="AAPL"), tasks, "demo")
        assert len(tasks.tasks) == 1
        for ticker in ("MSFT", "META", "NVDA"):
            await api.analyze_stock(api.StockRequest(symbol=ticker), tasks, "demo")
        with pytest.raises(HTTPException) as error:
            await api.analyze_stock(api.StockRequest(symbol="TSLA"), tasks, "demo")
        assert error.value.status_code == 429
    asyncio.run(exercise())


def test_cache_honors_each_ttl_and_requires_admin_to_clear(api, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(api, "monotonic", lambda: clock[0])
    api.cache.set("brief", 1, ttl=10)
    api.cache.set("long", 2, ttl=600)
    clock[0] += 11
    assert api.cache.get("brief") is None
    assert api.cache.get("long") == 2
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.clear_cache(current_user="demo"))
    assert error.value.status_code == 403
    assert api.cache.get("long") == 2
    asyncio.run(api.clear_cache(current_user="admin"))
    assert api.cache.get("long") is None


def test_sec_collector_emits_linked_events_without_template_scores(api, monkeypatch):
    from scraping import sec_scraper
    class Response:
        status_code = 200
        def json(self):
            return {"filings": {"recent": {"form": ["4", "25-NSE"], "filingDate": ["2024-01-02", "2024-01-03"], "accessionNumber": ["0001-24-000001", "0001-24-000002"], "primaryDocument": ["a.xml", "b.htm"]}}}
    def get(url, **kwargs):
        assert kwargs["timeout"] == (5, 10)
        assert "Host" not in kwargs["headers"]
        return Response()
    monkeypatch.setattr(sec_scraper.requests, "get", get)
    events = sec_scraper.fetch_sec_filings("AAPL")
    assert len(events) == 2
    assert not any("sentiment" in event or "sentiment_context" in event for event in events)
    assert events[0]["url"].endswith("/320193/000124000001/a.xml")
    assert "Removal" in events[1]["description"]


def test_failed_refresh_does_not_overwrite_last_saved_news(api, monkeypatch):
    from scraping.enhanced_news_scraper import EnhancedNewsScraper
    original = save_records("AAPL", "comprehensive_news", [{"title": "Previous evidence", "publishedAt": "2020-01-01"}])
    scraper = EnhancedNewsScraper()
    for name in ("fetch_company_ir", "fetch_gdelt", "fetch_yahoo_finance_news", "fetch_gnews", "fetch_rss_feeds", "fetch_finviz_news", "fetch_stocktwits"):
        monkeypatch.setattr(scraper, name, lambda *args: [])
    assert scraper.fetch_comprehensive_news("AAPL") is None
    assert json.loads(open(original).read())[0]["publishedAt"] == "2020-01-01"


def test_authenticated_http_contract_serializes_unknown_values(api, monkeypatch):
    import httpx
    from backend.core.auth import create_access_token
    save_records("AAPL", "sec_sentiment", [{"form_type": "4", "url": "https://www.sec.gov/filing"}])
    token = create_access_token("fixture", "demo")
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://fixture") as client:
            assert (await client.get("/api/stocks/AAPL?password=fixture-demo")).status_code == 401
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get("/api/stocks/AAPL", headers=headers)
            assert response.status_code == 200
            assert response.json()["last_updated"] is None
            assert response.json()["sentiment_metrics"]["avg_sentiment"] is None
            assert (await client.delete("/api/cache", headers=headers)).status_code == 403
            assert (await client.get("/api/auth/session", headers=headers)).json() == {"authenticated": True, "role": "demo"}
            assert (await client.get("/api/stocks/AAPL/quantitative", headers=headers)).json()["metrics"] == {}
    asyncio.run(exercise())


def test_rss_unknown_publication_date_stays_unknown_and_requests_are_bounded(api, monkeypatch):
    from scraping.enhanced_news_scraper import EnhancedNewsScraper
    scraper = EnhancedNewsScraper()
    class Response:
        content = b'<rss><channel><item><title>AAPL earnings report</title><link>https://example.org/news</link></item></channel></rss>'
        def raise_for_status(self):
            pass
    calls = []
    def get(url, **kwargs):
        calls.append(kwargs["timeout"])
        return Response()
    monkeypatch.setattr(scraper.session, "get", get)
    articles = scraper.fetch_gnews("AAPL") + scraper.fetch_rss_feeds("AAPL")
    assert articles
    assert all(article["publishedAt"] is None for article in articles)
    assert calls
    assert all(0 < timeout.total <= 8 and 0 < timeout.connect_timeout <= 3
               and 0 < timeout.read_timeout <= 5 for timeout in calls)


@pytest.mark.parametrize("job_status", ["pending", "processing"])
@pytest.mark.parametrize("symbol", ["aapl", " AAPL "])
def test_delete_rejects_active_refresh_without_removing_evidence_or_job(api, job_status, symbol):
    from pathlib import Path
    path = Path(save_records("AAPL", "news_sentiment", [{"title": "Preserve this evidence"}]))
    job = _job(api)
    job.status = job_status
    before = path.read_bytes()
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.delete_stock(symbol, "admin"))
    assert error.value.status_code == 409
    assert "refresh" in error.value.detail.lower()
    assert path.read_bytes() == before
    assert api.analysis_status["AAPL"] is job
    assert job.status == job_status


def test_login_preserves_configured_password_whitespace(api, monkeypatch):
    password = "  leading-and-trailing-spaces  "
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    monkeypatch.setenv("STOCKSCOPE_PASSWORD", password)
    result = asyncio.run(api.login(api.LoginRequest(password=password)))
    assert result.success is True
    assert result.role == "admin"
    assert result.access_token
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.login(api.LoginRequest(password=password.strip())))
    assert error.value.status_code == 401


def test_ticker_containing_sec_is_classified_by_snapshot_suffix(api):
    save_records("PSEC", "comprehensive_news", [{"title": "Company report", "source": "Publisher", "publishedAt": "2024-01-01", "sentiment": {"compound": .3}}])
    save_records("PSEC", "sec_sentiment", [{"form_type": "10-K", "filing_date": "2024-01-02", "sentiment": {"compound": .9}}])
    frame = load_evidence("PSEC")
    assert frame[frame["source"] == "Publisher"].iloc[0]["source_type"] == "news"
    assert frame[frame["source"] == "SEC"].iloc[0]["source_type"] == "sec"
    assert sentiment_metrics(frame)["avg_sentiment"] == .3
    result = asyncio.run(api.get_stock_analysis("PSEC", "demo"))
    assert result.sentiment_metrics.sample_size == 1
    assert len(result.filings) == 1
    assert result.filings[0]["form_type"] == "10-K"


def test_cache_concurrent_updates_reads_and_invalidation_keep_entries_consistent(api):
    from concurrent.futures import ThreadPoolExecutor
    # Widen the real publication gap between a value and its expiry so readers
    # exercise contention instead of relying on the interpreter's switch timing.
    class YieldingDict(dict):
        def __setitem__(self, key, value):
            super().__setitem__(key, value)
            time.sleep(.0001)
    cache = api.CacheManager()
    cache._cache = YieldingDict()
    def worker(worker_id):
        for index in range(100):
            key = f"entry-{index % 5}"
            cache.set(key, worker_id, ttl=30)
            observed = cache.get(key)
            assert observed is None or observed in range(6)
            if index % 3 == 0:
                cache.invalidate("entry-")
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(worker, worker_id) for worker_id in range(6)]
        for future in futures:
            future.result(timeout=5)
    assert cache._cache.keys() == cache._expires.keys()


@pytest.mark.parametrize("symbol", ["BRK-B", "bf-b", " BRK-B "])
def test_symbol_validation_accepts_share_classes_without_network(api, monkeypatch, symbol):
    import pandas as pd
    import yfinance
    seen = []
    class Ticker:
        def __init__(self, ticker):
            seen.append(ticker)
            self.info = {"symbol": ticker, "longName": "Fixture share class"}
        def history(self, **kwargs):
            assert kwargs == {"period": "5d", "timeout": 10}
            return pd.DataFrame({"Close": [1.0]})
    monkeypatch.setattr(yfinance, "Ticker", Ticker)
    valid, message = api.validate_stock_symbol(symbol)
    assert valid
    assert message == "Valid symbol: Fixture share class"
    assert seen == [symbol.strip().upper()]
    valid, message = api.validate_stock_symbol("../AAPL")
    assert not valid
    assert message == "Invalid stock symbol format"
    assert len(seen) == 1  # bad format rejected before provider access


def test_yahoo_and_rss_publication_times_keep_explicit_utc_offset(api, monkeypatch):
    from datetime import timedelta
    from scraping import enhanced_news_scraper
    class Ticker:
        news = [{"content": {"title": "AAPL report", "pubDate": "2026-10-14T12:30:00Z", "canonicalUrl": {"url": "https://example.org/yahoo"}}}]
    monkeypatch.setattr(enhanced_news_scraper.yf, "Ticker", lambda ticker: Ticker())
    scraper = enhanced_news_scraper.EnhancedNewsScraper()
    class Response:
        content = b'<rss><channel><item><title>AAPL report</title><link>https://example.org/rss</link><pubDate>Wed, 14 Oct 2026 09:00:00 GMT</pubDate></item></channel></rss>'
        def raise_for_status(self):
            pass
    monkeypatch.setattr(scraper.session, "get", lambda *args, **kwargs: Response())
    yahoo = scraper.fetch_yahoo_finance_news("AAPL")
    rss = scraper.fetch_rss_feeds("AAPL")
    assert yahoo and rss
    assert yahoo[0]["publishedAt"] == "2026-10-14T12:30:00+00:00"
    assert rss[0]["publishedAt"] == "2026-10-14T09:00:00+00:00"
    assert all(datetime.fromisoformat(article["publishedAt"]).utcoffset() == timedelta(0) for article in yahoo + rss)


def test_global_rss_matches_company_aliases_without_substring_matches(api, monkeypatch):
    from scraping import enhanced_news_scraper
    scraper = enhanced_news_scraper.EnhancedNewsScraper()
    monkeypatch.setattr(enhanced_news_scraper, 'RSS_FEEDS', {'NPR Business': 'https://feeds.npr.org/1006/rss.xml'})
    class Response:
        content = b'<rss><channel><item><title>Microsoft announces earnings</title><link>https://example.org/microsoft</link></item><item><title>MSFTish unrelated story</title><link>https://example.org/other</link></item></channel></rss>'
        def raise_for_status(self):
            pass
    monkeypatch.setattr(scraper.session, 'get', lambda *args, **kwargs: Response())
    articles = [row for row in scraper.fetch_rss_feeds('MSFT') if row['source'] == 'NPR Business']
    assert [row['title'] for row in articles] == ['Microsoft announces earnings']
    assert articles[0]['publishedAt'] is None


def test_google_news_summary_is_plain_text(api, monkeypatch):
    from scraping.enhanced_news_scraper import EnhancedNewsScraper
    scraper = EnhancedNewsScraper()
    class Response:
        content = b'<rss><channel><item><title>Apple earnings</title><link>https://example.org/article</link><description>&lt;a href="https://example.org/article"&gt;Apple earnings&lt;/a&gt;&amp;nbsp;&lt;font&gt;Publisher&lt;/font&gt;</description></item></channel></rss>'
        def raise_for_status(self):
            pass
    monkeypatch.setattr(scraper.session, 'get', lambda *args, **kwargs: Response())
    article = scraper.fetch_gnews('AAPL')[0]
    assert '<' not in article['description']
    assert 'Apple earnings' in article['description']
    assert article['url'] == 'https://example.org/article'


def test_article_candidates_reject_listing_and_quote_pages():
    from scraping.enhanced_news_scraper import is_article_candidate
    assert not is_article_candidate('Apple earnings report', 'https://seekingalpha.com/symbol/AAPL/news?source=feed')
    assert not is_article_candidate('Apple Stock Price, News, Quote & History - Yahoo', 'https://news.google.com/rss/articles/example')
    assert is_article_candidate('Apple earnings report', 'https://seekingalpha.com/article/123-apple-earnings')
    assert is_article_candidate('Apple earnings report', 'https://news.google.com/rss/articles/example')
    assert not is_article_candidate('Broken article', None)


def _stub_prices(monkeypatch, closes, quote, volumes=None):
    import pandas as pd
    import yfinance
    history = pd.DataFrame(
        {"Open": closes, "High": closes, "Low": closes, "Close": closes, "Volume": volumes if volumes is not None else [100] * len(closes)},
        index=pd.date_range("2024-01-02", periods=len(closes), tz="America/New_York"),
    )
    class Ticker:
        @property
        def info(self):
            if isinstance(quote, Exception):
                raise quote
            return quote
        def history(self, **kwargs):
            assert kwargs["timeout"] == 10
            return history
    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: Ticker())


@pytest.mark.parametrize("quote, expected", [
    ({}, (None, None, None)),
    ({"currentPrice": float("nan"), "regularMarketPrice": float("inf"), "regularMarketChange": float("-inf"), "regularMarketChangePercent": float("nan")}, (None, None, None)),
    ({"regularMarketPrice": 0, "regularMarketChange": 0, "regularMarketChangePercent": 0, "regularMarketTime": 1704240000}, (0, 0, 0)),
    ({"currentPrice": 25, "regularMarketChange": .5, "regularMarketChangePercent": 2, "regularMarketTime": "bad timestamp"}, (25, .5, 2)),
    (RuntimeError("Fixture quote failure"), (None, None, None)),
])
def test_price_history_distinguishes_missing_quote_from_zero_and_historical_close(api, monkeypatch, quote, expected):
    _stub_prices(monkeypatch, [10, 12], quote)
    result = api.get_price_history("AAPL", current_user="demo")
    assert (result["currentPrice"], result["priceChange"], result["priceChangePercent"]) == expected
    assert result["lastHistoricalClose"] == 12
    assert result["lastHistoricalCloseDate"] == "2024-01-03"
    assert result["data"][-1]["close"] == 12
    if isinstance(quote, dict) and quote.get("regularMarketTime") == 1704240000:
        assert result["quote_as_of"] == "2024-01-03T00:00:00+00:00"
    else:
        assert result["quote_as_of"] is None
    json.dumps(result, allow_nan=False)


def test_price_history_filters_nonfinite_bars_before_json_serialization(api, monkeypatch):
    _stub_prices(monkeypatch, [10, float('nan'), 12, float('inf')], {})
    result = api.get_price_history('META', current_user='demo')
    assert [row['close'] for row in result['data']] == [10, 12]
    assert result['lastHistoricalClose'] == 12
    assert result['lastHistoricalCloseDate'] == '2024-01-04'
    from starlette.responses import JSONResponse
    JSONResponse(result)  # Serialization happens after the endpoint returns.


def test_price_history_without_valid_bars_returns_404(api, monkeypatch):
    _stub_prices(monkeypatch, [float('nan'), float('inf')], {})
    with pytest.raises(HTTPException) as error:
        api.get_price_history('META', current_user='demo')
    assert error.value.status_code == 404


def test_price_history_missing_volume_keeps_prices_and_observed_zero(api, monkeypatch):
    _stub_prices(monkeypatch, [10, 11, 12, 13], {}, volumes=[float('nan'), float('inf'), -1, 0])
    result = api.get_price_history('META', current_user='demo')
    assert [row['volume'] for row in result['data']] == [None, None, None, 0]
    assert len(result['data']) == 4
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("closes, expected", [
    ([12], (12, None, None)),
    ([0, 12], (12, None, None)),
    ([float("nan"), 12], (12, None, None)),
    ([12, float("inf")], (None, None, None)),
    ([12, 12], (12, 0, 0)),
    ([12, 0], (0, -12, -100)),
])
def test_watchlist_does_not_invent_change_without_comparable_closes(api, monkeypatch, closes, expected):
    _stub_prices(monkeypatch, closes, {"longName": "Fixture"})
    monkeypatch.setattr(api, "get_available_tickers", lambda: ["AAPL"])
    result = api.get_available_stocks("demo")["stocks"][0]
    assert (result["currentPrice"], result["priceChange"], result["priceChangePercent"]) == expected
    assert result["price_basis"] == "latest_daily_close"
    if expected[0] is None:
        assert result["price_as_of"] is None
    else:
        assert result["price_as_of"].startswith("2024-01-")
    json.dumps(result, allow_nan=False)


def test_saved_news_excludes_legacy_social_posts_but_keeps_company_releases(api):
    from backend.services.research import saved_news
    save_records("NVDA", "comprehensive_news", [
        {"title": "Editorial report", "source": "Publisher"},
        {"title": "Social opinion", "source": "Stocktwits", "sentiment": {"compound": 1}},
        {"title": "Explicit social", "source": "Other", "source_type": "social", "sentiment": {"compound": 1}},
        {"title": "Provider social", "provider": "reddit", "sentiment": {"compound": 1}},
        {"title": "Company statement", "source_type": "company_release"},
    ])
    assert {row["title"] for row in saved_news("NVDA")} == {"Editorial report", "Company statement"}
    assert sentiment_metrics(load_evidence("NVDA"))["sample_size"] == 0
