"""Read existing Vault configuration privately and save non-secret audit results."""
import getpass
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

from cryptography import x509

BASE = 'http://127.0.0.1:8200/v1/'
DEST = Path('.tmp/vault-part3-audit.json')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def get(path, token, method='GET'):
    req = urllib.request.Request(BASE + path, headers={'X-Vault-Token': token}, method=method)
    with opener.open(req, timeout=10) as response:
        return json.load(response)['data']


def main():
    admin = getpass.getpass('Vault administrative token (hidden): ')
    stage = 'authentication'
    try:
        identity = get('auth/token/lookup-self', admin)
        if 'root' not in identity.get('policies', []):
            raise RuntimeError('Expected the initial administrator identity')
        stage = 'mounts'
        mounts = get('sys/mounts', admin)
        auths = get('sys/auth', admin)
        stage = 'roles and policies'
        roles, policies = {}, {}
        for name in ('service-a', 'service-b', 'certificate-manager'):
            role = get('auth/approle/role/' + name, admin)
            roles[name] = {key: role.get(key) for key in (
                'token_policies', 'token_ttl', 'token_max_ttl', 'token_type',
                'token_no_default_policy', 'secret_id_ttl', 'secret_id_num_uses',
                'secret_id_bound_cidrs', 'token_bound_cidrs')}
            policy = get('sys/policies/acl/' + name, admin).get('policy', '')
            file_policy = Path('vault/policies/' + name + '.hcl').read_text(encoding='utf-8')
            policies[name] = {'matches_project_file': policy.strip() == file_policy.strip()}
        stage = 'PKI configuration'
        pki = get('pki/roles/service-a-role', admin)
        pki_fields = {key: pki.get(key) for key in (
            'allowed_domains', 'allow_bare_domains', 'allow_subdomains',
            'allow_glob_domains', 'allow_any_name', 'allow_ip_sans',
            'allow_wildcard_certificates', 'key_type', 'key_bits', 'ttl', 'max_ttl')}
        cert = x509.load_pem_x509_certificate(get('pki/cert/ca', admin)['certificate'].encode())
        audit = {'administrator_authenticated': True,
                 'mounts': {name: {'type': mounts.get(name, {}).get('type'),
                                   'options': mounts.get(name, {}).get('options')}
                            for name in ('secret/', 'pki/')},
                 'approle_type': auths.get('approle/', {}).get('type'),
                 'roles': roles, 'policies': policies, 'pki_role': pki_fields,
                 'ca_not_before_utc': cert.not_valid_before_utc.isoformat(),
                 'ca_not_after_utc': cert.not_valid_after_utc.isoformat(),
                 'ca_public_key_type': type(cert.public_key()).__name__}
        DEST.parent.mkdir(exist_ok=True)
        DEST.write_text(json.dumps(audit, indent=2), encoding='utf-8')
        print('PASS: read-only audit saved; no credentials saved')
        return 0
    except urllib.error.HTTPError as exc:
        print('FAIL:', stage, 'HTTP', exc.code, file=sys.stderr)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print('FAIL:', stage, type(exc).__name__, file=sys.stderr)
    finally:
        admin = None
    return 1


if __name__ == '__main__':
    sys.exit(main())
