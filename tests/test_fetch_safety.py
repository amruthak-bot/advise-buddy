import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import discover


@pytest.mark.parametrize("url", [
    "http://[::1]/", "http://[fc00::1]/", "http://169.254.169.254/",
    "http://127.0.0.1/", "http://localhost./", "http://2130706433/",
])
def test_non_public_literal_hosts_are_blocked(url):
    assert not discover._is_fetchable(url)


def test_redirect_is_checked_before_a_second_fetch(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=302, headers={'location':'http://127.0.0.1/private'})
    monkeypatch.setattr(discover, '_request_public', get)
    assert discover.fetch_text('https://example.com/page') == ''
    assert calls == ['https://example.com/page']


@pytest.mark.parametrize('ips', [['127.0.0.1'], ['10.1.2.3'], ['93.184.216.34','192.168.1.1']])
def test_hostnames_resolving_to_private_network_are_rejected(monkeypatch, ips):
    monkeypatch.setattr(discover.socket, 'getaddrinfo', lambda *a, **kw:
                        [(2, 1, 6, '', (ip, 80)) for ip in ips])
    with pytest.raises(ValueError):
        discover._public_address('public-looking.example', 80)


def test_public_request_pins_the_validated_ip_and_keeps_host(monkeypatch):
    from email.message import Message
    headers = Message()
    headers['Content-Type'] = 'text/html; charset=utf-8'
    response = SimpleNamespace(status=200, headers=headers,
        read=lambda limit: b'<p>Public page</p>', getheaders=lambda: list(headers.items()))
    sock = SimpleNamespace(close=lambda: None)
    observed = {}
    class Connection:
        def __init__(self, host, port, timeout):
            observed['host'] = host
        def request(self, method, path, headers):
            assert self.sock is sock
            observed['path'] = path
        def getresponse(self):
            return response
        def close(self):
            pass
    monkeypatch.setattr(discover, '_public_address', lambda host, port: '93.184.216.34')
    monkeypatch.setattr(discover.http.client, 'HTTPConnection', Connection)
    def connect(target, timeout):
        observed['target'] = target
        return sock
    monkeypatch.setattr(discover.socket, 'create_connection', connect)
    assert discover._request_public('http://public.example/path?q=1').status_code == 200
    assert observed == {'host':'public.example', 'path':'/path?q=1', 'target':('93.184.216.34',80)}
