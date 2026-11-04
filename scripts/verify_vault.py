"""Read-only Vault checks. Never initializes, unseals, or prints credentials."""
import argparse
import getpass
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--addr', default='http://127.0.0.1:8200')
    parser.add_argument('--ca-cert', help='PEM CA bundle for HTTPS validation')
    parser.add_argument('--token', action='store_true', help='prompt privately for a token')
    args = parser.parse_args()
    url = urllib.parse.urlsplit(args.addr)
    if (url.scheme not in ('http', 'https') or not url.hostname or url.username
            or url.password or url.query or url.fragment or url.path not in ('', '/')):
        parser.error('address must be a plain http(s) origin without credentials, path, query, or fragment')
    if url.scheme == 'http' and url.hostname not in ('127.0.0.1', 'localhost', '::1'):
        parser.error('HTTP is allowed only on loopback')
    context = ssl.create_default_context(cafile=args.ca_cert) if args.ca_cert else ssl.create_default_context()
    origin = args.addr.rstrip('/')
    failed = False

    def request(path, token=None):
        headers = {'X-Vault-Token': token} if token else {}
        req = urllib.request.Request(origin + path, headers=headers)
        # Do not follow redirects: credentials must not be forwarded to another host.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                             urllib.request.HTTPSHandler(context=context))
        try:
            with opener.open(req, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.load(exc)
            except (ValueError, UnicodeDecodeError):
                return exc.code, {}

    try:
        code, health = request('/v1/sys/health')
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print('FAIL API connectivity:', type(exc).__name__, str(exc))
        print('BLOCKED health, seal, version, and authentication checks')
        return 1
    print(f'PASS API connectivity: health endpoint returned HTTP {code}')
    if code not in (200, 429, 472, 473, 501, 503) or not isinstance(health, dict) or 'initialized' not in health:
        print('FAIL unexpected health response')
        return 1
    initialized, sealed = health.get('initialized'), health.get('sealed')
    print(('PASS' if initialized is True else 'FAIL') + f' initialized: {initialized}')
    print(('PASS' if sealed is False else 'FAIL') + f' unsealed: {sealed}')
    print('INFO server version:', health.get('version') or 'not reported')
    failed |= initialized is not True or sealed is not False
    try:
        status, seal = request('/v1/sys/seal-status')
        print('INFO storage:', seal.get('storage_type', 'not reported') if status == 200 else 'unavailable')
        if initialized is not True or sealed is not False:
            print('BLOCKED authentication checks: Vault must be initialized and unsealed')
        else:
            for label, token in [('unauthenticated', None), ('invalid token', 'invalid-verification-token')]:
                result, _ = request('/v1/auth/token/lookup-self', token)
                ok = result == 403
                print(('PASS' if ok else 'FAIL') + f' {label} access denied: HTTP {result}')
                failed |= not ok
            if args.token:
                token = getpass.getpass('Vault token (hidden): ')
                result, _ = request('/v1/auth/token/lookup-self', token)
                ok = result == 200
                print(('PASS' if ok else 'FAIL') + f' token accepted: HTTP {result}')
                failed |= not ok
            else:
                print('BLOCKED valid-token check: rerun with --token for a hidden prompt')
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print('FAIL verification request:', type(exc).__name__)
        return 1
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
