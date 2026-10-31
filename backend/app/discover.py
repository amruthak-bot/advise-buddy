"""Web discovery: find sources for a question automatically, so the
user never has to paste URLs by hand.

Flow: question -> Tavily web search -> fetch each result page ->
extract readable text -> Source objects ready for the normal
analysis pipeline. Nothing here trusts fetched text: it goes through
the same deterministic quote verification as pasted text, and a page
that cannot be fetched becomes an empty-text source (the existing
"Not fetched" cell), never invented content.

Keys live in the environment only (TAVILY_API_KEY). Without a key,
discovery is unavailable and the paste flow still works.
"""
import html as html_lib
import ipaddress
import http.client
import os
import re
import socket
import ssl
from types import SimpleNamespace
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin

import httpx
import certifi

from .models import Source

MAX_RESULTS = 5
MAX_TEXT_CHARS = 12000
MAX_PAGE_BYTES = 2_000_000
TAVILY_URL = "https://api.tavily.com/search"
USER_AGENT = "AdviseBuddy/1.0 (evidence research; +https://example.org)"

# Host suffixes treated as official. This is a SUGGESTION only
# (typeSetBy="heuristic"): the user can change any type in the
# editor, and "official" here never proves a claim applies to the
# user's category or case.
_OFFICIAL_SUFFIXES = (".gov", ".gov.in", ".edu", ".ac.in", ".nic.in")


class DiscoverNotConfigured(Exception):
    """No TAVILY_API_KEY in the environment."""


class SearchFailed(Exception):
    """The search request or all fetches failed unexpectedly."""


def suggest_type(url: str) -> str:
    """'official' for government/education hosts, else 'third_party'."""
    host = (urlparse(url or "").hostname or "").lower()
    if host.endswith(_OFFICIAL_SUFFIXES) or host in (
            "gov.in", "edu.in"):
        return "official"
    return "third_party"


_SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside",
              "form", "noscript", "head"}


class _TextExtractor(HTMLParser):
    """Collect visible text, skipping boilerplate tags."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif not self._skip and tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "br"}:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1
        elif not self._skip and tag in {"p", "div", "li", "tr", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self._parts.append(text)

    def text(self) -> str:
        lines = " ".join(self._parts).splitlines()
        return "\n".join(re.sub(r"\s+", " ", line).strip()
                         for line in lines if line.strip())


def extract_text(html_text: str) -> str:
    """Readable text from a page, capped so one huge page cannot
    swamp the analysis. Returns "" for unparseable input."""
    if not html_text:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(html_text)
    except Exception:
        return ""
    return html_lib.unescape(parser.text())[:MAX_TEXT_CHARS]


def _is_fetchable(url: str) -> bool:
    """Reject private IP literals and local hostnames; recheck redirects."""
    try:
        parsed = urlparse(url or "")
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower().rstrip('.')
    if not host or host == "localhost" or host.endswith((".localhost", ".local")):
        return False
    try:
        address = ipaddress.ip_address(host)
        return address.is_global and not address.is_multicast
    except ValueError:
        if re.fullmatch(r"[\d.]+", host) or host.startswith('0x'):
            return False
    if host.startswith(("127.", "10.", "192.168.", "[::1]")):
        return False
    if re.match(r"172\.(1[6-9]|2[0-9]|3[0-1])\.", host):
        return False
    return True


def _public_address(host: str, port: int) -> str:
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    ips = [entry[4][0] for entry in addresses]
    if not ips or any(not ipaddress.ip_address(ip).is_global or
                      ipaddress.ip_address(ip).is_multicast for ip in ips):
        raise ValueError("Source host does not resolve exclusively to public addresses")
    return ips[0]


def _request_public(url: str):
    """Connect to a vetted IP while retaining the original Host and TLS SNI.

    Pinning this connection prevents a second DNS lookup from rebinding
    an approved hostname to a private address. Redirects are handled by
    fetch_text and get the same validation on every hop.
    """
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        raise ValueError("Source URLs must not contain credentials")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    address = _public_address(parsed.hostname, port)
    connection = http.client.HTTPConnection(parsed.hostname, port, timeout=20)
    raw_socket = socket.create_connection((address, port), timeout=20)
    try:
        connection.sock = (ssl.create_default_context(cafile=certifi.where()).wrap_socket(
            raw_socket, server_hostname=parsed.hostname)
            if parsed.scheme == "https" else raw_socket)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        connection.request("GET", path, headers={"User-Agent": USER_AGENT,
                                                "Accept-Encoding": "identity"})
        response = connection.getresponse()
        data = response.read(MAX_PAGE_BYTES + 1)
        if len(data) > MAX_PAGE_BYTES:
            raise ValueError("Source page exceeds the download limit")
        encoding = response.headers.get_content_charset() or "utf-8"
        try:
            text = data.decode(encoding, errors="replace")
        except LookupError:
            text = data.decode("utf-8", errors="replace")
        return SimpleNamespace(status_code=response.status,
                               headers={k.lower(): v for k, v in response.getheaders()},
                               text=text)
    finally:
        connection.close()
        raw_socket.close()


def tavily_search(query: str, api_key: str,
                  max_results: int = MAX_RESULTS) -> list:
    """Raw search results: [{title, url}]. Raises SearchFailed."""
    try:
        resp = httpx.post(TAVILY_URL, json={
            "api_key": api_key, "query": query,
            "max_results": max_results, "search_depth": "basic",
            "include_answer": False,
        }, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise SearchFailed(f"web search failed: {exc}") from exc
    results = []
    for item in (data.get("results") or [])[:max_results]:
        url = item.get("url") or ""
        if url:
            results.append({"title": item.get("title") or url,
                            "url": url})
    return results


def fetch_text(url: str) -> str:
    """Page text for one URL, or "" when it cannot be fetched.
    Fetch failure is an honest empty source, never invented text."""
    if not _is_fetchable(url):
        return ""
    try:
        for _ in range(4):
            if not _is_fetchable(url):
                return ""
            resp = _request_public(url)
            if resp.status_code not in (301, 302, 303, 307, 308):
                break
            location = resp.headers.get("location")
            if not location:
                return ""
            url = urljoin(url, location)
        else:
            return ""
        if resp.status_code != 200:
            return ""
        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type and "text" not in content_type:
            return ""
        return extract_text(resp.text)
    except Exception:
        return ""


def discover(question: str, api_key: str = None,
             max_results: int = MAX_RESULTS) -> dict:
    """Search + fetch. Returns {"sources": [...], "fetched": n,
    "failed": m}. Raises DiscoverNotConfigured / SearchFailed."""
    key = api_key or os.environ.get("TAVILY_API_KEY")
    if not key:
        raise DiscoverNotConfigured(
            "Web search is not configured on this server. Add a free "
            "Tavily API key as TAVILY_API_KEY, or paste source text.")
    results = tavily_search(question, key, max_results)
    sources, fetched = [], 0
    today = date.today().isoformat()
    # Fetch independently with a small fixed bound, keeping search order.
    with ThreadPoolExecutor(max_workers=MAX_RESULTS) as pool:
        texts = list(pool.map(fetch_text, [item["url"] for item in results]))
    for i, (item, text) in enumerate(zip(results, texts), start=1):
        if text:
            fetched += 1
        sources.append(Source(
            id=f"web-{i}", title=item["title"], url=item["url"],
            text=text, type=suggest_type(item["url"]),
            typeSetBy="heuristic", retrievedAt=today))
    return {"sources": sources, "fetched": fetched,
            "failed": len(sources) - fetched}
