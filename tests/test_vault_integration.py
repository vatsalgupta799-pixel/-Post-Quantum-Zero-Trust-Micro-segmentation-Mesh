"""Unit checks plus an explicitly opt-in live integration run.

Run offline checks with: python -m pytest -q tests/test_vault_integration.py
Live run (private terminal): set VAULT_RUN_LIVE=1 and use pytest -s; it prompts
for the administrator token, creates disposable credentials and a test cert.
"""
import getpass
import importlib.util
import io
import os
from pathlib import Path
import urllib.error
import urllib.request

import pytest


SPEC = importlib.util.spec_from_file_location(
    'vault_integration_demo', Path(__file__).parents[1] / 'scripts' / 'vault_integration_demo.py')
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


def test_denial_sanitizes_response_body(capsys):
    class Denied:
        def open(self, req, timeout):
            raise urllib.error.HTTPError(req.full_url, 403, 'denied', {}, io.BytesIO(b'sensitive-response'))

    client = demo.VaultHTTP()
    client.opener = Denied()
    status, body = client.call('some/path', token='sensitive-token')
    assert status == 403 and body == {}
    assert 'sensitive' not in capsys.readouterr().out


def test_network_error_is_sanitized():
    class Unavailable:
        def open(self, req, timeout):
            raise urllib.error.URLError('sensitive-diagnostic')

    client = demo.VaultHTTP()
    client.opener = Unavailable()
    with pytest.raises(demo.VaultUnavailable) as exc:
        client.call('some/path', token='sensitive-token')
    assert 'sensitive' not in str(exc.value)


def test_redirects_are_not_followed():
    handler = demo.NoRedirect()
    req = urllib.request.Request('http://127.0.0.1:8200/v1/example')
    assert handler.redirect_request(req, None, 302, '', {}, 'https://example.invalid') is None


def test_checks_distinguish_denial_from_success(capsys):
    checks = demo.Checks()
    checks.check('denied as expected', 403, (403,))
    with pytest.raises(RuntimeError):
        checks.check('unexpected access', 200, (403,))
    assert [item['status'] for item in checks.records] == ['PASS', 'FAIL']
    assert 'FAIL unexpected access' in capsys.readouterr().out


@pytest.mark.skipif(os.environ.get('VAULT_RUN_LIVE') != '1', reason='requires explicit live Vault opt-in')
def test_live_vault_integration():
    token = getpass.getpass('Vault administrative token (hidden): ')
    try:
        checks = demo.Checks()
        metadata = demo.run(token, checks=checks)
        assert checks.records and all(item['status'] == 'PASS' for item in checks.records)
        assert metadata['vault_version'] != 'not reported'
    finally:
        token = None
