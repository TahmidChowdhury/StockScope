"""Postgres parity tests use a transaction-local temporary table, never real data."""
import os
import pytest
from sqlalchemy import text
from backend.trading import congress
from backend.trading.disclosure_browser import QUERY
from backend.db.engine import create_database_engine


def assert_projection(connection):
    import json
    connection.execute(text('CREATE TEMPORARY TABLE trading_documents (id text PRIMARY KEY, payload json) ON COMMIT DROP'))
    def row(id, **changes):
        return {'disclosure_id': id, 'member': 'Example Member', 'owner': 'spouse', 'symbol': 'AAPL', 'side': 'buy',
                'transaction_date': '2026-01-01', 'available_date': '2026-01-03', 'lag_days': 2,
                'amount_range': '$1,001 - $15,000', 'asset_type': 'stock',
                'source_url': 'https://example.test/evidence/', **changes}
    original = row('auto-v1', event_id='event-1', version=1, superseded_at='2026-02-01')
    latest = row('auto-v2', event_id='event-1', version=2, superseded_at=None)
    retired = row('retired', event_id='event-2', version=1, superseded_at='2026-02-01')
    duplicate = row('csv-duplicate', owner='SP', source_url='https://example.test/evidence?download=1')
    other = row('csv-unique', symbol='MSFT', side='sell', member="Another O'Brien", owner='self', available_date='2026-01-04', lag_days=3)
    for id, rows in [('congress-feed', [original, latest, retired]), ('congress', [duplicate, other])]:
        connection.execute(text('INSERT INTO trading_documents VALUES (:id, CAST(:payload AS json))'),
                           {'id': id, 'payload': json.dumps({'records': rows})})
    expected_doc = {'records': [latest, other], 'automatic_record_count': 1, 'manual_duplicates_hidden': 1}
    for filters in [{}, {'member': "Another O'Brien"}, {'symbol': 'AAPL'}, {'side': 'sell'}, {'query': '%'}, {'query': 'aapl'}, {'offset': 1, 'limit': 1}]:
        params = {'member': '', 'symbol': '', 'side': '', 'query': '', 'offset': 0, 'limit': 100, **filters}
        observed = connection.scalar(QUERY, params)
        expected = congress.browse(expected_doc, **params)
        for key in ['records', 'total', 'offset', 'members', 'symbols', 'summary', 'filtered_summary', 'member_profiles']:
            assert observed[key] == expected[key], (filters, key)
        assert observed['manual_duplicates_hidden'] == 1
        assert observed['automatic_record_count'] == 1


def test_postgres_projection_matches_python_reference():
    url = os.getenv('STOCKSCOPE_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set STOCKSCOPE_TEST_DATABASE_URL for the Postgres projection check')
    engine = create_database_engine(url)
    try:
        with engine.begin() as connection:
            assert_projection(connection)
    finally:
        engine.dispose()
