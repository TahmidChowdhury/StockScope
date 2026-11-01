"""yfinance transport with a workspace-wide budget for actual HTTP requests."""
import yfinance
from curl_cffi import requests
from backend.core.resources import reserve, record_response, request_category


class BudgetSession(requests.Session):
    def request(self, method, url, *args, **kwargs):
        reserve('yahoo', category=request_category(url))
        # yfinance handles authentication internally; each call still uses a budget slot.
        kwargs['timeout'] = min(kwargs.get('timeout') or 12, 12)
        kwargs['allow_redirects'] = False
        try:
            response = super().request(method, url, *args, **kwargs)
        except Exception:
            record_response('yahoo', None, {})
            raise
        record_response('yahoo', response.status_code, response.headers)
        return response


_session = BudgetSession(impersonate='chrome')


def Ticker(symbol):
    return yfinance.Ticker(symbol, session=_session)


# Consumers use these operations instead of independent Ticker instances.
# Transport accounting still counts every SDK request, including auth/retries.
def get_info(symbol):
    from backend.core.provider_cache import fetch_snapshot
    from backend.core.resources import require_available, provider_operation
    from backend.services.research import normalized_symbol
    symbol = normalized_symbol(symbol)

    def load():
        require_available('yahoo')
        with provider_operation('profile'):
            value = Ticker(symbol).info
        if not value:
            require_available('yahoo')
            return {}
        # yfinance can return nonfinite numeric fields. Missing stays missing.
        import math
        return {key: None if isinstance(value, float) and not math.isfinite(value) else value
                for key, value in value.items()}

    return fetch_snapshot('yahoo-info-v1', symbol, load, usable=bool)


def get_history(symbol, *, allow_stale=True, include_metadata=False, **kwargs):
    from io import StringIO
    import pandas as pd
    from backend.core.provider_cache import fetch_snapshot, ProviderUnavailable
    from backend.core.resources import require_available, provider_operation
    from backend.services.research import normalized_symbol
    symbol = normalized_symbol(symbol)
    # Timeouts and SDK error handling don't change the requested observations.
    identity = {key: value for key, value in kwargs.items() if key not in ('timeout', 'raise_errors')}

    def load():
        require_available('yahoo')
        with provider_operation('history'):
            ticker = Ticker(symbol)
            frame = ticker.history(**kwargs)
            if frame.empty:
                require_available('yahoo')
                raise ProviderUnavailable('No historical price observations are available.')
            # History metadata belongs to these bars (including subunit codes such as GBp).
            # Older saved snapshots without it remain explicitly unknown.
            if include_metadata:
                metadata = ticker.history_metadata
            else:
                # The public accessor may fetch an extra intraday history just
                # to obtain tradingPeriods. Use only metadata from this request.
                raw = getattr(getattr(ticker, '_price_history', None), '_history_metadata', None)
                metadata = {'currency': raw.get('currency')} if isinstance(raw, dict) else {}
        return {'frame': frame.to_json(orient='table', date_format='iso'), 'metadata': metadata}

    saved = fetch_snapshot('yahoo-history-v1', [symbol, identity, include_metadata], load, allow_stale=allow_stale)
    frame = pd.read_json(StringIO(saved.data['frame']), orient='table')
    frame.attrs.update(retrieved_at=saved.retrieved_at, stale=saved.stale, metadata=saved.data['metadata'])
    return frame


def get_news(symbol):
    from backend.core.provider_cache import fetch_snapshot
    from backend.core.resources import require_available, provider_operation
    from backend.services.research import normalized_symbol
    symbol = normalized_symbol(symbol)

    def load():
        require_available('yahoo')
        with provider_operation('news'):
            news = Ticker(symbol).news
        if not news:
            require_available('yahoo')
        return news or []

    return fetch_snapshot('yahoo-news-v1', symbol, load, ttl=6 * 3600).data


def get_quote_batch(symbols):
    """Use the SDK's authenticated quote transport for all tape symbols at once."""
    from yfinance.data import YfData
    from backend.core.resources import require_available, provider_operation
    require_available('yahoo')
    with provider_operation('profile'):
        payload = YfData(session=_session).get_raw_json(
            'https://query1.finance.yahoo.com/v7/finance/quote',
            params={'symbols': ','.join(symbols), 'formatted': 'false'}, timeout=10,
        )
    return payload['quoteResponse']['result']


def search_companies(query):
    """Resolve beyond the local catalog using the existing budgeted Yahoo transport.

    An empty quotes array is a successful zero-match lookup; malformed responses
    and transport failures are unavailable, never cached as zero matches.
    """
    import re
    from yfinance.data import YfData
    from backend.core.provider_cache import fetch_snapshot, ProviderUnavailable
    from backend.core.resources import require_available, provider_operation

    def load():
        require_available('yahoo')
        with provider_operation('profile'):
            payload = YfData(session=_session).get_raw_json(
                'https://query2.finance.yahoo.com/v1/finance/search',
                params={'q': query, 'quotesCount': 50, 'newsCount': 0,
                        'enableFuzzyQuery': 'false', 'quotesQueryId': 'tss_match_phrase_query'}, timeout=10,
            )
        if not isinstance(payload, dict) or not isinstance(payload.get('quotes'), list):
            raise ProviderUnavailable('Company lookup returned an incomplete response.')
        matches = {}
        for quote in payload['quotes']:
            if not isinstance(quote, dict):
                raise ProviderUnavailable('Company lookup returned an invalid match.')
            symbol = quote.get('symbol') if isinstance(quote, dict) else None
            name = quote.get('longname') or quote.get('shortname') if isinstance(quote, dict) else None
            if quote.get('quoteType') == 'EQUITY' and isinstance(symbol, str) and re.fullmatch(r'[A-Z][A-Z0-9.-]{0,9}', symbol) and isinstance(name, str) and name.strip():
                matches[symbol] = {'symbol': symbol, 'name': name}
        return list(matches.values())

    return fetch_snapshot('yahoo-company-search-v1', query.casefold().strip(), load,
                          ttl=3600, allow_stale=False).data
