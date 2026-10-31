"""Tests for web discovery. All network calls are faked; no test
touches the real Tavily API or any real page."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest

from app import discover as disc
from app.main import discover_endpoint
from app.models import DiscoverRequest


class FakeResp:
    def __init__(self, status=200, headers=None, text="", payload=None):
        self.status_code = status
        self.headers = headers or {}
        self.text = text
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _fake_http(monkeypatch, get_map):
    def fake_post(url, json=None, timeout=None):
        assert "tavily" in url
        return FakeResp(payload={"results": [
            {"title": "Gov page", "url": "https://example.gov/page"},
            {"title": "Blog", "url": "https://blog.example.com/post"},
        ]})

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        if url in get_map:
            return get_map[url]
        raise AssertionError(f"unexpected fetch: {url}")

    monkeypatch.setattr(disc, "httpx",
                        SimpleNamespace(post=fake_post, get=fake_get))
    monkeypatch.setattr(disc, "_request_public", fake_get)


def test_suggest_type():
    assert disc.suggest_type("https://passportindia.gov.in/") == "official"
    assert disc.suggest_type("https://example.gov/page") == "official"
    assert disc.suggest_type("https://univ.edu/x") == "official"
    assert disc.suggest_type("https://blog.example.com/post") == "third_party"
    assert disc.suggest_type("https://example.org/") == "third_party"


def test_extract_text_skips_boilerplate_and_caps():
    html_doc = ("<html><head><title>T</title></head><body>"
                "<nav>Menu links</nav><script>var x = 1;</script>"
                "<article><p>Official fee is Rs 2500.</p></article>"
                "</body></html>")
    text = disc.extract_text(html_doc)
    assert "Official fee is Rs 2500." in text
    assert "Menu links" not in text and "var x" not in text
    assert len(disc.extract_text("<p>" + "word " * 5000 + "</p>")) == 12000


def test_discover_fetches_and_counts_failures(monkeypatch):
    _fake_http(monkeypatch, {
        "https://example.gov/page": FakeResp(
            headers={"content-type": "text/html"},
            text="<html><body><p>Official fee is Rs 2500.</p></body></html>"),
        "https://blog.example.com/post": FakeResp(status=404),
    })
    out = disc.discover("passport fee", api_key="test-key")
    assert out["fetched"] == 1 and out["failed"] == 1
    gov, blog = out["sources"]
    assert "Official fee is Rs 2500." in gov.text
    assert gov.type == "official" and gov.typeSetBy == "heuristic"
    assert blog.text == "" and blog.type == "third_party"


def test_discover_needs_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(disc.DiscoverNotConfigured):
        disc.discover("passport fee", api_key=None)


def test_discover_search_failure(monkeypatch):
    def boom(url, json=None, timeout=None):
        raise Exception("network down")

    monkeypatch.setattr(disc, "httpx",
                        SimpleNamespace(post=boom, get=None))
    with pytest.raises(disc.SearchFailed):
        disc.discover("passport fee", api_key="test-key")


def test_fetch_guard_blocks_private_hosts(monkeypatch):
    called = []

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        called.append(url)
        return FakeResp(text="<p>hi</p>")

    monkeypatch.setattr(disc, "httpx",
                        SimpleNamespace(post=None, get=fake_get))
    assert disc.fetch_text("http://localhost:8000/x") == ""
    assert disc.fetch_text("ftp://example.com/x") == ""
    assert called == []


def test_discover_endpoint(monkeypatch):
    # NOTE: these call the endpoint function directly instead of going
    # through TestClient. TestClient's portal hung on Windows after the
    # 6 pure-function tests in this file, while the same suite passes
    # on Linux. The app itself never uses TestClient; this only
    # removes the hanging harness. Endpoint logic (key handling,
    # fetch counts, 503) is still fully exercised.
    _fake_http(monkeypatch, {
        "https://example.gov/page": FakeResp(
            headers={"content-type": "text/html"},
            text="<html><body><p>Official fee is Rs 2500.</p></body></html>"),
        "https://blog.example.com/post": FakeResp(status=404),
    })
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    out = discover_endpoint(DiscoverRequest(question="passport fee"))
    assert len(out.sources) == 2
    assert out.fetched == 1 and out.failed == 1
    assert out.sources[0].type == "official"


def test_discover_endpoint_without_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    out = discover_endpoint(DiscoverRequest(question="passport fee"))
    assert out.status_code == 503
