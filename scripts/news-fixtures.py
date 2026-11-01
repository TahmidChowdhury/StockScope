"""Generate browser fixtures through the real saved-news service, with no storage/provider reads."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.services import research

rows = [{'title': f'Article {i:02}', 'url': f'https://example.test/{i:02}',
         'source': 'Rare source' if i < 3 else 'Common source',
         'publishedAt': f'2026-10-{i // 2 + 1:02}T12:00:00Z',
         'sentiment': {'compound': .95 if i == 0 else -.95 if i == 1 else .1}}
        for i in range(46)]
research.saved_snapshots = lambda symbol, *args, **kwargs: [('news_sentiment', rows if symbol == 'AAPL' else [])]
output = {}
for symbol in ['AAPL', 'EMPTY']:
    for order in ['date-desc', 'date-asc', 'sentiment-desc', 'sentiment-asc']:
        for excluded in [[], ['Common source'], ['Rare source'], ['Common source', 'Rare source']]:
            for offset in [0, 20, 40]:
                key = '|'.join([symbol, order, str(offset), ','.join(sorted(excluded))])
                output[key] = research.query_saved_news(symbol, sort=order, offset=offset, exclude_sources=excluded)
print(json.dumps(output))
