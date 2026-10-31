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
            metadata = ticker.history_metadata if include_metadata else {}
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
