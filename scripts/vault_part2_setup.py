"""Run a Vault Part 2 phase privately; never saves or prints credentials."""
import argparse
import getpass
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:8200/v1/'
RESULTS = Path('.tmp/vault-part2-results.json')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def request(path, token=None, method='GET', data=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['X-Vault-Token'] = token
    payload = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=payload, headers=headers, method=method)
    try:
        with opener.open(req, timeout=15) as response:
            body = response.read()
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def expect(label, path, token, method='GET', data=None, codes=(200, 204)):
    status, result = request(path, token, method, data)
    if status not in codes:
        raise RuntimeError(f'{label}: unexpected HTTP {status} (expected {codes})')
    print(f'PASS {label}: HTTP {status}', flush=True)
    return result


def kv(admin):
    mounts = expect('inspect mounts', 'sys/mounts', admin)['data']
    if 'secret/' in mounts:
        raise RuntimeError('secret/ already exists; stopped to protect existing data')
    expect('enable KV v2', 'sys/mounts/secret', admin, 'POST',
           {'type': 'kv', 'options': {'version': '2'}})
    expect('set version retention', 'secret/config', admin, 'POST', {'max_versions': 5})
    mounted = expect('verify KV mount', 'sys/mounts', admin)['data']['secret/']
    if mounted['type'] != 'kv' or mounted.get('options', {}).get('version') != '2':
        raise RuntimeError('secret/ is not KV v2')
    values = {
        'service-a/database': {'username': 'demo-database-user-a'},
        'service-a/api-config': {'configuration': 'demo-service-configuration-a'},
        'service-b/database': {'username': 'demo-database-user-b'},
        'service-b/api-config': {'configuration': 'demo-service-configuration-b'},
    }
    for name, value in values.items():
        expect('write demonstration '+name, 'secret/data/application/'+name,
               admin, 'POST', {'data': value})
        read = expect('read demonstration '+name, 'secret/data/application/'+name, admin)
        if read['data']['data'] != value:
            raise RuntimeError('Unexpected demonstration value')
    path = 'application/service-a/database'
    expect('update versioned secret', 'secret/data/'+path, admin, 'POST',
           {'data': {'username': 'demo-database-user-a-v2'}})
    first = expect('read version 1', 'secret/data/'+path+'?version=1', admin)
    second = expect('read version 2', 'secret/data/'+path+'?version=2', admin)
    if first['data']['metadata']['version'] != 1 or second['data']['metadata']['version'] != 2:
        raise RuntimeError('Unexpected KV version numbers')
    expect('soft delete version 2', 'secret/delete/'+path, admin, 'POST', {'versions': [2]})
    expect('deleted version inaccessible', 'secret/data/'+path+'?version=2', admin, codes=(404,))
    expect('restore version 2', 'secret/undelete/'+path, admin, 'POST', {'versions': [2]})
    restored = expect('read restored version', 'secret/data/'+path+'?version=2', admin)
    if restored['data']['data']['username'] != 'demo-database-user-a-v2':
        raise RuntimeError('Restored value did not match')
    RESULTS.parent.mkdir(exist_ok=True)
    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    results['kv'] = {'mount': 'secret/', 'version': 2, 'max_versions': 5,
                     'four_demo_secrets': 'PASS', 'versions_1_and_2': 'PASS',
                     'soft_delete_and_recovery': 'PASS'}
    RESULTS.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('KV PHASE COMPLETE; sanitized results saved.', flush=True)


def pki(admin):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    if 'pki/' in expect('inspect mounts', 'sys/mounts', admin)['data']:
        raise RuntimeError('pki/ already exists; stopped to protect existing CA material')
    expect('enable PKI', 'sys/mounts/pki', admin, 'POST', {'type': 'pki'})
    expect('set PKI maximum TTL', 'sys/mounts/pki/tune', admin, 'POST', {'max_lease_ttl': '168h'})
    root = expect('create internal demonstration CA', 'pki/root/generate/internal', admin, 'POST',
                  {'common_name': 'Local Vault Demonstration CA', 'key_type': 'ec',
                   'key_bits': 256, 'ttl': '168h'})['data']
    expect('configure CA and CRL URLs', 'pki/config/urls', admin, 'POST',
           {'issuing_certificates': ['http://127.0.0.1:8200/v1/pki/ca'],
            'crl_distribution_points': ['http://127.0.0.1:8200/v1/pki/crl']})
    expect('configure restricted certificate role', 'pki/roles/service-a-role', admin, 'POST',
           {'allowed_domains': ['service-a.mesh.test'], 'allow_bare_domains': True,
            'allow_subdomains': False, 'allow_glob_domains': False, 'allow_any_name': False,
            'allow_localhost': False, 'allow_ip_sans': False, 'allow_wildcard_certificates': False,
            'enforce_hostnames': True, 'key_type': 'ec', 'key_bits': 256,
            'ttl': '1h', 'max_ttl': '24h'})
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'service-a.mesh.test')])
    csr = (x509.CertificateSigningRequestBuilder().subject_name(name)
           .add_extension(x509.SubjectAlternativeName([x509.DNSName('service-a.mesh.test')]), False)
           .sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode())
    issued = expect('sign demonstration CSR', 'pki/sign/service-a-role', admin, 'POST',
                    {'csr': csr, 'common_name': 'service-a.mesh.test', 'ttl': '1h'})['data']
    cert = x509.load_pem_x509_certificate(issued['certificate'].encode())
    ca = x509.load_pem_x509_certificate(root['certificate'].encode())
    cert.verify_directly_issued_by(ca)
    cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    if cn != 'service-a.mesh.test' or sans != ['service-a.mesh.test']:
        raise RuntimeError('Certificate subject or SAN did not match restrictions')
    print('PASS certificate subject, SAN and CA signature', flush=True)
    expect('revoke demonstration certificate', 'pki/revoke', admin, 'POST', {'serial_number': issued['serial_number']})
    crl_pem = expect('read revocation list', 'pki/cert/crl', admin)['data']['certificate']
    crl = x509.load_pem_x509_crl(crl_pem.encode())
    ca.public_key().verify(crl.signature, crl.tbs_certlist_bytes, ec.ECDSA(crl.signature_hash_algorithm))
    if crl.get_revoked_certificate_by_serial_number(cert.serial_number) is None:
        raise RuntimeError('Revoked serial missing from the CRL')
    print('PASS revoked serial present in signed CRL', flush=True)
    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    results['pki'] = {'mount': 'pki/', 'ca': 'internal ECDSA P-256, 168h',
                      'role': 'service-a-role', 'allowed_dns': 'service-a.mesh.test',
                      'certificate_ttl': '1h', 'role_max_ttl': '24h',
                      'certificate_signature_and_san': 'PASS', 'revocation_crl': 'PASS',
                      'not_before_utc': cert.not_valid_before_utc.isoformat(),
                      'not_after_utc': cert.not_valid_after_utc.isoformat()}
    RESULTS.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('PKI PHASE COMPLETE; sanitized results saved.', flush=True)


def auth(admin):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    methods = expect('inspect authentication mounts', 'sys/auth', admin)['data']
    names = ('service-a', 'service-b', 'certificate-manager')
    existing = expect('inspect policies', 'sys/policies/acl', admin, 'LIST')['data']
    existing = existing.get('keys', existing.get('policies', []))
    if 'approle/' in methods or any(name in existing for name in names):
        raise RuntimeError('AppRole or a target policy already exists; stopped to avoid overwriting it')
    policies = {name: Path('vault/policies/'+name+'.hcl').read_text(encoding='utf-8') for name in names}
    expect('enable AppRole', 'sys/auth/approle', admin, 'POST', {'type': 'approle'})
    for name in names:
        expect('load policy '+name, 'sys/policies/acl/'+name, admin, 'POST', {'policy': policies[name]})
        loaded = expect('read policy '+name, 'sys/policies/acl/'+name, admin)['data']
        if loaded.get('policy', '').strip() != policies[name].strip():
            raise RuntimeError('Loaded policy differs from its file: '+name)
    for name in names:
        expect('create AppRole '+name, 'auth/approle/role/'+name, admin, 'POST',
               {'token_policies': [name], 'token_no_default_policy': True,
                'token_type': 'service', 'token_ttl': '10m', 'token_max_ttl': '15m',
                'secret_id_ttl': '10m', 'secret_id_num_uses': 1,
                'secret_id_bound_cidrs': ['127.0.0.1/32'], 'token_bound_cidrs': ['127.0.0.1/32']})
        role = expect('inspect AppRole '+name, 'auth/approle/role/'+name, admin)['data']
        if (name not in role.get('token_policies', []) or not role.get('token_no_default_policy')
                or role.get('secret_id_num_uses') != 1 or role.get('secret_id_ttl') != 600
                or role.get('token_ttl') != 600 or role.get('token_max_ttl') != 900):
            raise RuntimeError('Unexpected role policies: '+name)
    tokens = {}
    role_ids = {}
    for name in names:
        role_ids[name] = expect('read role ID '+name, 'auth/approle/role/'+name+'/role-id', admin)['data']['role_id']
        secret_id = expect('generate one-use Secret ID '+name,
                           'auth/approle/role/'+name+'/secret-id', admin, 'POST', {})['data']['secret_id']
        login = expect('AppRole login '+name, 'auth/approle/login', None, 'POST',
                       {'role_id': role_ids[name], 'secret_id': secret_id})
        tokens[name] = login['auth']['client_token']
        secret_id = None
        if name not in login['auth']['policies'] or login['auth'].get('renewable') is not True:
            raise RuntimeError('Unexpected application token properties: '+name)

    def capabilities(token, paths):
        return expect('inspect effective capabilities', 'sys/capabilities-self', token, 'POST',
                      {'paths': paths})['data']

    for name, other in [('service-a', 'service-b'), ('service-b', 'service-a')]:
        token = tokens[name]
        own = 'secret/data/application/'+name+'/database'
        other_path = 'secret/data/application/'+other+'/database'
        cap = capabilities(token, [own, other_path, 'sys/mounts'])
        if set(cap.get(own, [])) != {'read'} or cap.get(other_path) != ['deny']:
            raise RuntimeError('Unexpected KV access capabilities for '+name)
        for suffix in ('database', 'api-config'):
            expect(name+' reads own '+suffix, 'secret/data/application/'+name+'/'+suffix, token)
        expect(name+' denied other service', other_path, token, codes=(403,))
        expect(name+' denied admin paths', 'sys/mounts', token, codes=(403,))
        expect(name+' denied infrastructure secrets', 'secret/data/infrastructure/envoy/configuration', token, codes=(403,))
        expect(name+' denied modifying own secret', own, token, 'POST', {'data': {'test': 'not-written'}}, codes=(403,))

    cm = tokens['certificate-manager']
    target = 'pki/sign/service-a-role'
    forbidden = 'pki/roles/not-authorized-test'
    caps = capabilities(cm, [target, forbidden, 'secret/data/application/service-a/database'])
    if 'update' not in caps.get(target, []) or caps.get(forbidden) != ['deny']:
        raise RuntimeError('Unexpected certificate manager capabilities')
    expect('certificate manager reads CA', 'pki/cert/ca', cm)
    expect('certificate manager denied PKI role changes', forbidden, cm, 'POST',
           {'allowed_domains': ['not-authorized.invalid']}, codes=(403,))
    expect('certificate manager denied application secrets', 'secret/data/application/service-a/database', cm, codes=(403,))
    expect('certificate manager denied admin', 'sys/mounts', cm, codes=(403,))
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'service-a.mesh.test')])
    csr = (x509.CertificateSigningRequestBuilder().subject_name(name)
           .add_extension(x509.SubjectAlternativeName([x509.DNSName('service-a.mesh.test')]), False)
           .sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode())
    signed = expect('certificate manager signs approved CSR', target, cm, 'POST',
                    {'csr': csr, 'common_name': 'service-a.mesh.test', 'ttl': '1h'})['data']
    ca_data = expect('read CA for certificate verification', 'pki/cert/ca', cm)['data']
    cert = x509.load_pem_x509_certificate(signed['certificate'].encode())
    ca = x509.load_pem_x509_certificate(ca_data['certificate'].encode())
    cert.verify_directly_issued_by(ca)
    if cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value != 'service-a.mesh.test':
        raise RuntimeError('Unexpected certificate subject')
    expect('invalid AppRole credentials rejected', 'auth/approle/login', None, 'POST',
           {'role_id': role_ids['service-a'], 'secret_id': 'invalid-demo-secret-id'}, codes=(400, 403))
    expect('unauthenticated secret access denied', 'secret/data/application/service-a/database', None, codes=(403,))
    expect('invalid token denied', 'secret/data/application/service-a/database', 'invalid-demo-token', codes=(403,))
    # Revoke one test service token and verify it no longer works.
    expect('revoke test token', 'auth/token/revoke', admin, 'POST', {'token': tokens['service-b']})
    expect('revoked token denied', 'secret/data/application/service-b/database', tokens['service-b'], codes=(403,))
    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    results['access'] = {'service_a_own_and_denials': 'PASS', 'service_b_own_and_denials': 'PASS',
                         'certificate_manager_approved_sign_and_denials': 'PASS',
                         'capabilities': 'PASS', 'invalid_approle': 'PASS',
                         'missing_invalid_revoked_token': 'PASS',
                         'token_type': 'service', 'token_ttl': '10m', 'token_max_ttl': '15m',
                         'secret_id_ttl': '10m', 'secret_id_uses': 1}
    RESULTS.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('AUTH AND ACCESS PHASE COMPLETE; sanitized results saved.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['kv', 'pki', 'auth'])
    args = parser.parse_args()
    admin = getpass.getpass('Vault administrative token (hidden): ')
    try:
        identity = expect('authenticate administrator', 'auth/token/lookup-self', admin)['data']
        if 'root' not in identity.get('policies', []):
            raise RuntimeError('This setup requires the initial administrative token')
        if args.phase == 'kv':
            kv(admin)
        elif args.phase == 'pki':
            pki(admin)
        elif args.phase == 'auth':
            auth(admin)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print('STOP:', str(exc), file=sys.stderr)
        print('Do not rerun automatically; report this non-secret error for safe recovery.', file=sys.stderr)
        return 1
    finally:
        admin = None
    return 0


if __name__ == '__main__':
    sys.exit(main())
