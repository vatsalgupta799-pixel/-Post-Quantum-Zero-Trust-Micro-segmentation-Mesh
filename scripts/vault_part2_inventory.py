"""Privately inspect Vault mounts without saving the administrative token."""
import getpass
import json
from pathlib import Path
import urllib.request
import urllib.error

base = 'http://127.0.0.1:8200/v1/'
token = getpass.getpass('Vault administrative token (hidden): ')
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
def get(path, method='GET'):
    request = urllib.request.Request(base + path, headers={'X-Vault-Token': token}, method=method)
    with opener.open(request, timeout=10) as response:
        return json.load(response)
try:
    stage = 'token lookup'
    me = get('auth/token/lookup-self')['data']
    stage = 'secrets mounts'
    mounts = get('sys/mounts')['data']
    stage = 'authentication mounts'
    methods = get('sys/auth')['data']
    stage = 'policy listing'
    policy_data = get('sys/policies/acl', method='LIST')['data']
    policies = policy_data.get('policies', policy_data.get('keys', []))
    result = {'admin_authenticated': True,
              'root_policy': 'root' in me.get('policies', []),
              'mounts': {p: {'type': v.get('type'), 'options': v.get('options')} for p, v in mounts.items()},
              'auth_methods': {p: v.get('type') for p, v in methods.items()},
              'existing_target_policies': [p for p in policies if p in ('service-a', 'service-b', 'certificate-manager', 'monitoring')]}
    Path('.tmp/vault-part2-inventory.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('PASS administrative authentication; sanitized inventory saved.')
except urllib.error.HTTPError as exc:
    print('FAIL inventory at', stage + ': HTTP', exc.code)
except (OSError, ValueError, KeyError) as exc:
    print('FAIL inventory:', type(exc).__name__)
finally:
    token = None
