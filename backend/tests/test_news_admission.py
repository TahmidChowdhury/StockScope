"""Captured provider candidates exercise admission, without network or live storage."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scraping.enhanced_news_scraper import EnhancedNewsScraper, is_article_candidate
from backend.services.research import query_saved_news, save_records

CAPTURED = json.loads((Path(__file__).parent / 'fixtures/vodafone_quote_pages.json').read_text())['items']
LEGITIMATE = [
    "Will Satellite Spectrum Bid Change Vodafone's (LSE:VOD) Narrative - Yahoo Finance",
    'Vodafone and BT Group report contrasting broadband investment plans',
    'Vodafone explores options for its network business, executives say',
    'BT Group shares rise after analysts quote stronger Vodafone forecasts',
    'Yahoo reports how options traders responded to Vodafone earnings',
    'Vodafone reviews its stock price after earnings; analysts quote history of investment',
]
LEGACY = {**CAPTURED[0], 'title': 'BT Group stock price, news, quote & history - Yahoo Finance',
          'url': 'https://example.org/legacy-quote'}


def scraper_with_candidates(monkeypatch, items):
    # No provider constructor, credentials, sentiment download, or network is needed.
    scraper = EnhancedNewsScraper.__new__(EnhancedNewsScraper)
    scraper.research_sources = SimpleNamespace(last_results={})
    for method in ('fetch_company_ir', 'fetch_gdelt', 'fetch_yahoo_finance_news',
                   'fetch_rss_feeds', 'fetch_finviz_news', 'fetch_stocktwits'):
        monkeypatch.setattr(scraper, method, lambda ticker: [])
    monkeypatch.setattr(scraper, 'fetch_gnews', lambda ticker: copy.deepcopy(items))
    return scraper


@pytest.mark.parametrize('item', CAPTURED, ids=lambda item: item['title'])
def test_captured_quote_pages_rejected_by_helper_and_collection(monkeypatch, item):
    assert not is_article_candidate(item['title'], item['url'])
    scraper = scraper_with_candidates(monkeypatch, [item])
    monkeypatch.setattr('scraping.enhanced_news_scraper.save_records',
                        lambda *args: pytest.fail('Rejected candidate must never reach persistence'))
    assert scraper.fetch_comprehensive_news('VOD.L') is None


@pytest.mark.parametrize('separator', [' & ', ' and ', ' AND ', '\tAnd  '])
def test_specific_template_retains_case_and_whitespace_normalization(separator):
    assert not is_article_candidate(f'  BT Group Stock Price, News, Quote{separator}History - Yahoo  ', LEGACY['url'])


@pytest.mark.parametrize('title', LEGITIMATE)
def test_ordinary_and_cross_company_reporting_remains_eligible(title):
    assert is_article_candidate(title, 'https://example.org/report')


def test_mixed_collection_persists_reporting_not_quote_pages(monkeypatch):
    reporting = [dict(title=title, url=f'https://example.org/report/{index}',
                      description='Provider reporting summary', source='Yahoo Finance',
                      provider='google_news', original_source='Yahoo Finance', source_type='news',
                      publishedAt='2026-10-31T12:00:00+00:00')
                 for index, title in enumerate(LEGITIMATE)]
    scraper = scraper_with_candidates(monkeypatch, CAPTURED + [LEGACY] + reporting)
    reference = scraper.fetch_comprehensive_news('VOD.L')
    persisted = json.loads(Path(reference).read_text())
    assert {item['url'] for item in persisted} == {item['url'] for item in reporting}
    assert {item['title'] for item in persisted} == set(LEGITIMATE)
    assert all(item['provider'] == 'google_news' and item['original_source'] == 'Yahoo Finance' for item in persisted)
    # Provider candidates and admitted records are intentionally separate counts.
    assert scraper.last_provider_results['google_news']['count'] == len(CAPTURED) + 1 + len(reporting)


def test_rejected_only_refresh_preserves_saved_evidence_and_news_presentation(monkeypatch):
    reference = Path(save_records('VOD.L', 'comprehensive_news', CAPTURED))
    original = reference.read_bytes()
    scraper = scraper_with_candidates(monkeypatch, CAPTURED + [LEGACY])
    assert scraper.fetch_comprehensive_news('VOD.L') is None
    assert reference.read_bytes() == original
    page = query_saved_news('VOD.L', limit=100)
    assert page['saved_total'] == 5
    assert {item['url'] for item in page['articles']} == {item['url'] for item in CAPTURED}
