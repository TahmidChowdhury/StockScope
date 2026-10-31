"""PostgreSQL projects and pages disclosure JSON without transferring the full feed.

The Python congress.browse implementation remains the reference for file/SQLite
storage. This query keeps the same latest-version and manual-duplicate semantics.
"""
from sqlalchemy import text
from backend.trading import congress, disclosure_collector
from backend.services import research

# All interpolated identifiers below are fixed application constants. User filters
# are bound parameters, including search strings (literal substring, not SQL LIKE).
_OWNER = """CASE lower(btrim(data->>'owner'))
 WHEN 'self' THEN 'member' WHEN 'sp' THEN 'spouse' WHEN 'jt' THEN 'joint'
 WHEN 'dc' THEN 'dependent child' WHEN 'dependent' THEN 'dependent child'
 WHEN 'dependent_child' THEN 'dependent child' ELSE lower(btrim(data->>'owner')) END"""
_EVIDENCE_KEY = f"""jsonb_build_array(
 lower(substring(data->>'source_url' from '^https?://([^/:?#]+)')),
 rtrim(regexp_replace(regexp_replace(data->>'source_url', '^https?://[^/]+', ''), '[?#].*$', ''), '/'),
 data->>'symbol', data->>'side', data->>'transaction_date', {_OWNER},
 replace(replace(data->>'amount_range', ' ', ''), ',', ''))"""
_SUMMARY = """jsonb_build_object('total',count(*),'buys',count(*) FILTER (WHERE side='buy'),
 'sells',count(*) FILTER (WHERE side='sell'),'symbol_count',count(DISTINCT symbol),
 'member_count',count(DISTINCT member),'latest_available_date',max(available_date),
 'average_lag_days',round(avg(lag_days),2))"""
_SEARCH = ' OR '.join(f"position(:query IN lower(data->>'{column}')) > 0" for column in congress.COLUMNS)
QUERY = text(f"""
WITH manual AS MATERIALIZED (
 SELECT value::jsonb AS data FROM trading_documents,
 LATERAL json_array_elements(payload->'records')
 WHERE id='congress'
), ranked AS MATERIALIZED (
 SELECT value::jsonb AS data,
 row_number() OVER (PARTITION BY value->>'event_id' ORDER BY (value->>'version')::integer DESC) AS version_rank
 FROM trading_documents, LATERAL json_array_elements(payload->'records')
 WHERE id='congress-feed'
), automatic AS MATERIALIZED (
 SELECT data, {_EVIDENCE_KEY} AS evidence_key FROM ranked
 WHERE version_rank=1 AND coalesce(data->>'superseded_at','')=''
), manual_unique AS MATERIALIZED (
 SELECT data FROM manual WHERE {_EVIDENCE_KEY} NOT IN (SELECT evidence_key FROM automatic)
), all_records AS MATERIALIZED (
 SELECT data, data->>'member' AS member, data->>'symbol' AS symbol,
 data->>'side' AS side, data->>'available_date' AS available_date,
 (data->>'lag_days')::numeric AS lag_days
 FROM (SELECT data FROM automatic UNION ALL SELECT data FROM manual_unique) combined
), filtered AS MATERIALIZED (
 SELECT * FROM all_records WHERE (:member='' OR member=:member)
 AND (:symbol='' OR symbol=:symbol) AND (:side='' OR side=:side)
 AND (:query='' OR ({_SEARCH}))
), profiles AS (
 SELECT member, {_SUMMARY} AS stats FROM all_records GROUP BY member
)
SELECT jsonb_build_object(
 'records', coalesce((SELECT jsonb_agg(data) FROM (SELECT data FROM filtered
 ORDER BY available_date DESC, data->>'transaction_date' DESC, data->>'disclosure_id' DESC
 OFFSET :offset LIMIT :limit) page), '[]'::jsonb),
 'total', (SELECT count(*) FROM filtered), 'offset', :offset,
 'members', coalesce((SELECT jsonb_agg(member ORDER BY member) FROM profiles),'[]'::jsonb),
 'symbols', coalesce((SELECT jsonb_agg(symbol ORDER BY symbol) FROM (SELECT DISTINCT symbol FROM all_records) symbols),'[]'::jsonb),
 'summary',(SELECT {_SUMMARY} FROM all_records),
 'filtered_summary',(SELECT {_SUMMARY} FROM filtered),
 'member_profiles', coalesce((SELECT jsonb_agg(jsonb_build_object('member',member)||stats ORDER BY member) FROM profiles),'[]'::jsonb),
 'automatic_record_count',(SELECT count(*) FROM automatic),
 'manual_duplicates_hidden',(SELECT count(*) FROM manual)-(SELECT count(*) FROM manual_unique),
 'last_import',(SELECT payload->'last_import' FROM trading_documents WHERE id='congress'))
""")


def browse(member='', symbol='', side='', query='', offset=0, limit=100):
    repo = research.repository()
    if repo is None or repo.engine.dialect.name != 'postgresql':
        return congress.browse(congress.research_document(), member, symbol, side, query, offset, limit)
    symbol = research.normalized_symbol(symbol) if symbol.strip() else ''
    with repo.engine.connect() as connection:
        result = connection.scalar(QUERY, {'member': member, 'symbol': symbol, 'side': side,
                                           'query': query.strip().casefold(), 'offset': offset, 'limit': limit})
    collection = disclosure_collector.status()
    automatic = bool(result.pop('automatic_record_count'))
    duplicates = result.pop('manual_duplicates_hidden')
    result.update(mode='automatic_and_csv' if automatic else 'csv_import', collection=collection,
                  live_feed_connected=bool(collection.get('enabled') and collection.get('last_success')),
                  provenance={'source': 'mixed_disclosures' if automatic else 'user_supplied_csv',
                              'dates_verified': False, 'manual_duplicates_hidden': duplicates,
                              'limitations': congress.AUTOMATIC_LIMITATIONS if automatic else congress.PROVENANCE_LIMITATIONS})
    return result
