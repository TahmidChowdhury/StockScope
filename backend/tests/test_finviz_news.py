"""Finviz listing timestamps must not depend on the deployment's timezone."""

from datetime import datetime, timezone
from types import SimpleNamespace

from bs4 import BeautifulSoup
import pytest

from scraping.enhanced_news_scraper import EnhancedNewsScraper, parse_finviz_news


def table(*labels):
    rows = "".join(
        f'<tr><td>{label}</td><td><a href="https://publisher.example/{index}">Company story {index}</a></td></tr>'
        for index, label in enumerate(labels)
    )
    return BeautifulSoup(f'<table class="fullview-news-outer">{rows}</table>', "html.parser")


@pytest.mark.parametrize("observed,expected", [
    ("2026-10-23T03:20:00+00:00", "2026-10-22T20:30:00+00:00"),
    ("2026-01-23T04:20:00+00:00", "2026-01-22T21:30:00+00:00"),
])
def test_today_uses_new_york_date_after_utc_midnight(observed, expected):
    articles = parse_finviz_news(table("Today 04:30PM", "04:00PM"), observed_at=datetime.fromisoformat(observed))
    assert articles[0]["publishedAt"] == expected
    assert articles[1]["publishedAt"] == expected.replace(":30:", ":00:")
    assert articles[0]["source_date_label"] == "Today 04:30PM"


def test_explicit_date_midnight_and_unknown_dates_remain_distinct():
    articles = parse_finviz_news(
        table("10:00AM", "Oct-21-26 12:00AM", "11:00AM", "Unknown 10:00AM", "09:00AM"),
        observed_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
    )
    assert [article["publishedAt"] for article in articles] == [
        None, "2026-10-21T04:00:00+00:00", "2026-10-21T15:00:00+00:00", None, None,
    ]


def test_collection_parses_original_table_instead_of_host_dated_dataframe(monkeypatch):
    from finvizfinance import quote

    monkeypatch.setattr(quote, "finvizfinance", lambda ticker: SimpleNamespace(soup=table("Oct-21-26 04:30PM")))
    articles = EnhancedNewsScraper().fetch_finviz_news("GOOG")
    assert len(articles) == 1
    assert articles[0]["publishedAt"] == "2026-10-21T20:30:00+00:00"
    assert articles[0]["sentiment"]["label"] in {"positive", "neutral", "negative"}


def test_missing_table_and_result_limit():
    assert parse_finviz_news(BeautifulSoup("No news", "html.parser")) == []
    assert len(parse_finviz_news(table(*(["Oct-21-26 04:30PM"] * 12)))) == 10
