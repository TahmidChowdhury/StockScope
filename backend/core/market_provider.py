"""yfinance transport with a workspace-wide budget for actual HTTP requests."""
import yfinance
from curl_cffi import requests
from backend.core.resources import reserve, record_response


class BudgetSession(requests.Session):
    def request(self, method, url, *args, **kwargs):
        reserve('yahoo')
        # yfinance handles authentication internally; each call still uses a budget slot.
        kwargs.setdefault('timeout', 12)
        kwargs['allow_redirects'] = False
        response = super().request(method, url, *args, **kwargs)
        record_response('yahoo', response.status_code, response.headers)
        return response


_session = BudgetSession(impersonate='chrome')


def Ticker(symbol):
    return yfinance.Ticker(symbol, session=_session)
