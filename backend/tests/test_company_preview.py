"""Quick previews must never turn hovering into a provider request."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.core.auth import create_access_token
from backend.core.cache import clear_cache, _key
from backend.core.resources import state, read_states
from backend.routers import fundamentals


@pytest.mark.parametrize('saved', [False, True])
def test_preview_is_authenticated_cache_only_and_preserves_old_dates(monkeypatch, saved):
    monkeypatch.setenv('SECRET_KEY', 'disposable-preview-test-signing-key-2026')
    clear_cache()
    def no_provider(*args, **kwargs):
        raise AssertionError('A quick preview must not compute or refresh financials')
    monkeypatch.setattr(fundamentals, '_compute_full_cached', no_provider)
    key = _key('_compute_full_cached', ('AAPL',), {})
    original = {'ttm': {'ticker': 'AAPL', 'revenue_ttm': 0, 'fcf_ttm': -5, 'insufficient_data': False},
                'series': {'large': ['not returned']},
                'metadata': {'retrieved_at': '2024-01-01T00:00:00Z', 'source': 'Saved fixture'}}
    if saved:
        with state(key) as record:
            record.update(result=original, expires_at=0)
    app = FastAPI()
    app.include_router(fundamentals.router, prefix='/api/fundamentals')
    client = TestClient(app)
    assert client.get('/api/fundamentals/AAPL/preview').status_code == 401
    headers = {'Authorization': 'Bearer ' + create_access_token('fixture', 'viewer')}
    response = client.get('/api/fundamentals/aapl/preview', headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body['symbol'] == 'AAPL' and body['saved'] is saved
    assert 'series' not in body
    assert body['ttm'] == (original['ttm'] if saved else None)
    assert body['metadata']['retrieved_at'] == (original['metadata']['retrieved_at'] if saved else None)
    assert bool(read_states([key])) is saved
    assert client.get('/api/fundamentals/BAD!/preview', headers=headers).status_code == 422
    clear_cache()
