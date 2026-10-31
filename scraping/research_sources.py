"""Bounded, metadata-only adapters for a reviewed company feed registry and GDELT.

Only repository configuration controls request destinations. Article URLs are
returned as links and are never fetched. Discovery time is not publication time.
"""

from backend.core.resources import guarded_get
import ipaddress
import json
import os
import re
import socket
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests
from bs4 import BeautifulSoup
from urllib3.util import Timeout

CONFIG_PATH = Path(__file__).resolve().parents[1] / "backend/data/source_feeds.json"
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_RECORDS = 20
PROVIDER_BUDGET_SECONDS = 10


class SourceFetchError(ValueError):
    pass


def canonical_url(value):
    """Keep article identity, dropping tracking fields and fragments, not all query data."""
    if not isinstance(value, str) or "\\" in value or any(ord(char) < 32 for char in value):
        return None
    try:
        parts = urlsplit(value.strip())
        host = parts.hostname
        if (parts.scheme not in {"http", "https"} or not host or parts.username
                or parts.password or parts.port not in {None, 80, 443}
                or "." not in host or host.lower().endswith((".local", ".localhost"))):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass
        query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
                 if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}]
        netloc = host.lower()
        if parts.port and parts.port != (443 if parts.scheme == "https" else 80):
            netloc += ":" + str(parts.port)
        return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", urlencode(sorted(query)), ""))
    except ValueError:
        return None


def explicit_timestamp(value):
    """Only accept a timestamp with a known timezone; never guess a missing date/zone."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


def _plain_text(value, limit):
    return BeautifulSoup(str(value or "")[:10000], "html.parser").get_text(" ", strip=True)[:limit]


def _matches_alias(title, aliases):
    return [alias for alias in aliases if re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", title, re.IGNORECASE)]


def load_source_config(path=CONFIG_PATH):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config.get("version") != 1 or not isinstance(config.get("companies"), dict):
        raise SourceFetchError("Unsupported source feed configuration")
    for symbol, company in config["companies"].items():
        aliases = company.get("aliases")
        if (not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", symbol) or not isinstance(aliases, list)
                or not aliases or len(aliases) > 8
                or any(not isinstance(alias, str) or len(alias) < 4 or len(alias) > 80
                       or not re.fullmatch(r"[\w .,&'-]+", alias) or alias.upper() == symbol for alias in aliases)):
            raise SourceFetchError("Company aliases must be explicit names, not bare tickers")
        if len(company.get("ir_feeds", [])) > 2:
            raise SourceFetchError("At most two reviewed feeds per company")
        for feed in company.get("ir_feeds", []):
            url = feed.get("url", "")
            parts = urlsplit(url)
            if not canonical_url(url) or parts.scheme != "https" or parts.port not in {None, 443}:
                raise SourceFetchError("Company feeds must use public HTTPS URLs")
    return config


class ResearchNewsSources:
    def __init__(self, session=None, config_path=CONFIG_PATH):
        self.session = session or requests.Session()
        self.config = load_source_config(config_path)
        self.last_results = {}

    def _read(self, url, deadline, params=None):
        """No redirects, local destinations, unbounded bodies, or retry loops."""
        parts = urlsplit(url)
        if parts.scheme != "https" or not canonical_url(url) or parts.port not in {None, 443}:
            raise SourceFetchError("Only reviewed HTTPS endpoints are supported")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Provider collection budget exhausted")
        # Configuration is reviewed code, not request input. Reject hosts resolving
        # locally as defense in depth; redirects are disabled below.
        addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
            raise SourceFetchError("Source host must resolve to public addresses")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Provider collection budget exhausted")
        response = guarded_get(session=self.session, url=
            url, params=params, stream=True, allow_redirects=False,
            timeout=Timeout(total=remaining, connect=min(3, remaining), read=min(7, remaining)),
            headers={"Accept": "application/json, application/rss+xml, application/xml, text/xml"},
        )
        try:
            if response.status_code != 200:
                raise SourceFetchError("Provider returned HTTP " + str(response.status_code))
            declared_length = response.headers.get("Content-Length")
            if declared_length and int(declared_length) > MAX_RESPONSE_BYTES:
                raise SourceFetchError("Provider response exceeds size limit")
            body = bytearray()
            for chunk in response.iter_content(chunk_size=4096):
                if time.monotonic() >= deadline:
                    raise TimeoutError("Provider collection budget exhausted")
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise SourceFetchError("Provider response exceeds size limit")
            return bytes(body)
        finally:
            response.close()

    def _prepare(self, symbol, provider, deadline):
        self.last_results[provider] = {"status": "no_data", "count": 0}
        flag = "STOCKSCOPE_IR_ENABLED" if provider == "company_ir_rss" else "STOCKSCOPE_GDELT_ENABLED"
        if os.getenv(flag, "true").strip().lower() in {"0", "false", "no", "off"}:
            self.last_results[provider]["status"] = "disabled"
            return None
        company = self.config["companies"].get(symbol.strip().upper())
        if not company or (provider == "company_ir_rss" and not company.get("ir_feeds")):
            self.last_results[provider]["status"] = "not_configured"
            return None
        if deadline <= time.monotonic():
            self.last_results[provider]["status"] = "budget_exhausted"
            return None
        return company

    def _finish(self, provider, records, error=None):
        self.last_results[provider] = {"status": "failed" if error else "ok" if records else "no_data", "count": len(records)}
        if error:
            self.last_results[provider]["reason"] = str(error)[:160]
        return records

    def fetch_company_ir(self, symbol, deadline=None):
        provider = "company_ir_rss"
        deadline = min(deadline if deadline is not None else float("inf"), time.monotonic() + PROVIDER_BUDGET_SECONDS)
        company = self._prepare(symbol, provider, deadline)
        if not company:
            return []
        records, seen, error = [], set(), None
        for feed_config in company["ir_feeds"]:
            try:
                feed = feedparser.parse(self._read(feed_config["url"], deadline))
                if not feed.get("version") or (feed.get("bozo") and not feed.entries):
                    raise SourceFetchError("Provider did not return a readable RSS or Atom feed")
                for entry in feed.entries[:MAX_RECORDS]:
                    title = _plain_text(entry.get("title"), 500)
                    url = canonical_url(entry.get("link"))
                    if not title or not url or url in seen:
                        continue
                    seen.add(url)
                    published = explicit_timestamp(entry.get("published"))
                    records.append({
                        "title": title, "description": _plain_text(entry.get("summary"), 500), "url": url,
                        "source": feed_config["name"], "original_source": feed_config["name"],
                        "source_type": "company_release", "provider": provider,
                        "publishedAt": published, "publication_date_source": "publisher_rss" if published else None,
                        "provider_seen_at": None, "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "sentiment": None,
                    })
            except (requests.RequestException, ValueError, OSError, TimeoutError) as exc:
                error = exc
        return self._finish(provider, records, error)

    def fetch_gdelt(self, symbol, deadline=None):
        provider = "gdelt"
        deadline = min(deadline if deadline is not None else float("inf"), time.monotonic() + PROVIDER_BUDGET_SECONDS)
        company = self._prepare(symbol, provider, deadline)
        if not company:
            return []
        aliases = company["aliases"]
        phrase_query = " OR ".join('"' + alias + '"' for alias in aliases)
        query = ("(" + phrase_query + ")" if len(aliases) > 1 else phrase_query) + " sourcelang:english"
        try:
            data = json.loads(self._read(GDELT_URL, deadline, params={
                "query": query, "mode": "ArtList", "format": "json", "maxrecords": MAX_RECORDS,
                "timespan": "7d", "sort": "DateDesc",
            }))
            if not isinstance(data, dict) or not isinstance(data.get("articles"), list):
                raise SourceFetchError("Provider did not return an article list")
            records, seen = [], set()
            for item in data["articles"][:MAX_RECORDS]:
                if not isinstance(item, dict):
                    continue
                title = _plain_text(item.get("title"), 500)
                matches = _matches_alias(title, aliases)
                url = canonical_url(item.get("url"))
                if not title or not matches or not url or url in seen:
                    continue
                seen.add(url)
                domain = urlsplit(url).hostname
                official = any(domain == host or domain.endswith("." + host) for host in company.get("official_domains", []))
                try:
                    discovered = datetime.strptime(item.get("seendate", ""), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()
                except (ValueError, TypeError):
                    discovered = None
                records.append({
                    "title": title, "description": "", "url": url,
                    "source": domain, "original_source": domain, "provider": provider,
                    "source_type": "company_release" if official else "news", "publishedAt": None,
                    "publication_date_source": None, "provider_seen_at": discovered,
                    "fetched_at": datetime.now(timezone.utc).isoformat(), "sentiment": None,
                    "matched_aliases": matches, "match_basis": "headline",
                })
            return self._finish(provider, records)
        except (requests.RequestException, ValueError, OSError, TimeoutError) as exc:
            return self._finish(provider, [], exc)
