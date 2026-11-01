"""Saved-news ordering and API contract regressions; no provider access."""
import asyncio
import json
import random

import pytest
from fastapi.testclient import TestClient
from backend.tests.test_research import api
from backend.services.research import query_saved_news, save_records


def news_fixture():
    return [{'title': f'Article {i:02}', 'url': f'https://example.test/{i:02}',
             'source': 'Rare source' if i < 3 else 'Common source',
             'publishedAt': f'2026-10-{i // 2 + 1:02}T12:00:00Z',
             'sentiment': {'compound': .95 if i == 0 else -.95 if i == 1 else .1}}
            for i in range(46)]


def test_complete_saved_collection_is_filtered_sorted_then_paginated(api):
    rows = news_fixture()
    save_records('AAPL', 'news_sentiment', rows)
    newest = query_saved_news('AAPL')
    assert newest['saved_total'] == newest['total'] == 46
    assert newest['count'] == 20 and newest['has_more']
    assert rows[0]['url'] not in {row['url'] for row in newest['articles']}
    assert query_saved_news('AAPL', sort='date-asc')['articles'][0]['url'] == rows[0]['url']
    assert query_saved_news('AAPL', sort='sentiment-desc')['articles'][0]['url'] == rows[0]['url']
    assert query_saved_news('AAPL', sort='sentiment-asc')['articles'][0]['url'] == rows[1]['url']
    rare = query_saved_news('AAPL', exclude_sources=['Common source'], offset=40)
    assert rare['offset'] == 0 and rare['total'] == 3 and rare['saved_total'] == 46
    assert rare['sources'] == ['Common source', 'Rare source']
    assert {row['source'] for row in rare['articles']} == {'Rare source'}
    empty = query_saved_news('AAPL', exclude_sources=rare['sources'])
    assert empty['total'] == 0 and empty['saved_total'] == 46 and empty['articles'] == []


@pytest.mark.parametrize('sort', ['date-desc', 'date-asc', 'sentiment-desc', 'sentiment-asc'])
def test_equal_values_have_stable_order_and_no_page_overlap(api, sort):
    rows = news_fixture()
    save_records('AAPL', 'news_sentiment', rows)
    def pages():
        return [row['url'] for offset in [0, 20, 40]
                for row in query_saved_news('AAPL', sort=sort, offset=offset)['articles']]
    first = pages()
    random.Random(42).shuffle(rows)
    save_records('AAPL', 'news_sentiment', rows)
    assert pages() == first
    assert len(first) == len(set(first)) == 46


def test_unknown_dates_and_unscored_items_sort_last_and_duplicates_stay_deduplicated(api):
    rows = [{'title': 'Known', 'publishedAt': '2026-10-01', 'sentiment': {'compound': 0}},
            {'title': 'Missing', 'publishedAt': None, 'sentiment': {'compound': None}},
            {'title': 'Release', 'source_type': 'company_release', 'sentiment': {'compound': 1}},
            {'title': 'Invalid', 'sentiment': {'compound': True}},
            {'title': 'Social', 'source_type': 'social'}]
    save_records('AAPL', 'news_sentiment', rows)
    save_records('AAPL', 'comprehensive_news', [rows[0]])
    for order in ['date-desc', 'date-asc', 'sentiment-desc', 'sentiment-asc']:
        page = query_saved_news('AAPL', sort=order)
        assert page['articles'][0]['title'] == 'Known'
        assert page['saved_total'] == 4


@pytest.mark.parametrize('role,capable', [('admin', True), ('member', True), ('viewer', False), ('guest', False), ('demo', False)])
def test_news_capability_uses_collection_authorization_rule(api, role, capable):
    api.app.dependency_overrides[api.verify_password_with_role] = lambda: role
    try:
        client = TestClient(api.app)
        response = client.get('/api/stocks/AAPL/news')
        assert response.status_code == 200
        assert response.json()['can_collect'] is capable
        assert response.json()['saved_total'] == 0
        if not capable:
            assert client.post('/api/stocks/analyze', json={'symbol': 'AAPL', 'sources': ['news']}).status_code == 403
        assert client.get('/api/stocks/AAPL/news?offset=-1').status_code == 422
        assert client.get('/api/stocks/AAPL/news?sort=invalid').status_code == 422
    finally:
        api.app.dependency_overrides.clear()


def test_broken_snapshot_is_a_request_failure_not_empty_news(api, tmp_path):
    from backend.services.research import data_directory
    (data_directory() / 'AAPL_news_sentiment.json').write_text('{broken')
    api.app.dependency_overrides[api.verify_password_with_role] = lambda: 'member'
    try:
        response = TestClient(api.app).get('/api/stocks/AAPL/news')
        assert response.status_code == 503
        assert 'articles' not in response.json()
    finally:
        api.app.dependency_overrides.clear()


def test_news_http_query_preserves_filter_sort_and_page_contract(api):
    save_records('AAPL', 'news_sentiment', news_fixture())
    api.app.dependency_overrides[api.verify_password_with_role] = lambda: 'member'
    try:
        client = TestClient(api.app)
        response = client.get('/api/stocks/AAPL/news?sort=sentiment-asc&exclude_source=Common%20source&offset=40&limit=20')
        assert response.status_code == 200
        page = response.json()
        assert page['articles'][0]['title'] == 'Article 01'
        assert (page['offset'], page['count'], page['total'], page['saved_total'], page['has_more']) == (0, 3, 3, 46, False)
        assert client.get('/api/stocks/AAPL/news?exclude_source=Common%20source&exclude_source=Rare%20source').json()['total'] == 0
    finally:
        api.app.dependency_overrides.clear()
