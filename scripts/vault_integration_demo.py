"""Exercise the existing local Vault integration using disposable AppRole credentials.

The administrator token is used only to provision one-use test credentials and
to revoke the test certificate/token. Application operations use AppRole tokens.
Never prints or stores tokens, Secret IDs, secret values, CSRs, or private keys.
"""
import datetime
import getpass
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

BASE = 'http://127.0.0.1:8200/v1/'  # local development listener only
RESULTS = Path('.tmp/vault-part3-results.json')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VaultUnavailable(Exception):
    pass


class VaultHTTP:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(self, path, *, token=None, method='GET', payload=None, raw=False):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-Vault-Token'] = token
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=10) as response:
                body = response.read()
                return response.status, body if raw else (json.loads(body) if body else {})
        except urllib.error.HTTPError as exc:
            return exc.code, b'' if raw else {}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # Do not log URLs, headers, response bodies, or exception representations.
            raise VaultUnavailable(type(exc).__name__) from None


class Checks:
    def __init__(self):
        self.records = []

    def check(self, name, actual, expected):
        ok = actual in expected
        self.records.append({'test': name, 'expected_http': list(expected),
                             'actual_http': actual, 'status': 'PASS' if ok else 'FAIL'})
        print(('PASS ' if ok else 'FAIL ') + name + ': HTTP ' + str(actual), flush=True)
        if not ok:
            raise RuntimeError('Unexpected response in ' + name)

    def condition(self, name, condition):
        self.records.append({'test': name, 'status': 'PASS' if condition else 'FAIL'})
        print(('PASS ' if condition else 'FAIL ') + name, flush=True)
        if not condition:
            raise RuntimeError('Validation failed: ' + name)


def run(admin, api=None, checks=None):
    api = api or VaultHTTP()
    checks = checks or Checks()

    def call(name, path, *, expected=(200,), token=None, method='GET', payload=None, raw=False):
        status, body = api.call(path, token=token, method=method, payload=payload, raw=raw)
        checks.check(name, status, expected)
        return body

    health = call('Vault connection and health', 'sys/health')
    checks.condition('Vault initialized and unsealed', health.get('initialized') is True and health.get('sealed') is False)
    version = health.get('version', 'not reported')
    identity = call('Administrator identity for test provisioning', 'auth/token/lookup-self', token=admin)['data']
    checks.condition('Administrator token accepted', 'root' in identity.get('policies', []))

    roles, tokens = {}, {}
    for name in ('service-a', 'service-b', 'certificate-manager'):
        role = call('Read test Role ID for '+name, 'auth/approle/role/'+name+'/role-id', token=admin)
        roles[name] = role['data']['role_id']
        secret = call('Create disposable Secret ID for '+name,
                      'auth/approle/role/'+name+'/secret-id', token=admin, method='POST', payload={})
        login = call('AppRole authentication for '+name, 'auth/approle/login', method='POST',
                     payload={'role_id': roles[name], 'secret_id': secret['data']['secret_id']})
        secret = None
        tokens[name] = login['auth']['client_token']
        checks.condition('Expected policy on '+name+' token', name in login['auth'].get('policies', []))

    paths = {}
    for name, other in (('service-a', 'service-b'), ('service-b', 'service-a')):
        own = 'secret/data/application/'+name+'/database'
        forbidden = 'secret/data/application/'+other+'/database'
        caps = call('Effective KV capabilities for '+name, 'sys/capabilities-self', token=tokens[name],
                    method='POST', payload={'paths': [own, forbidden]})['data']
        checks.condition('Least-privilege KV capabilities for '+name,
                         set(caps.get(own, [])) == {'read'} and caps.get(forbidden) == ['deny'])
        own_result = call(name+' retrieves own secret', own, token=tokens[name])
        checks.condition(name+' secret response has data', isinstance(own_result.get('data', {}).get('data'), dict))
        call(name+' denied other service secret', forbidden, token=tokens[name], expected=(403,))
        paths[name] = own

    call('Unauthenticated secret access denied', paths['service-a'], expected=(403,))
    call('Invalid token denied', paths['service-a'], token='invalid-demo-token', expected=(403,))
    call('Invalid AppRole credentials rejected', 'auth/approle/login', method='POST',
         payload={'role_id': roles['service-a'], 'secret_id': 'invalid-demo-secret-id'}, expected=(400, 403))

    cm = tokens['certificate-manager']
    sign_path = 'pki/sign/service-a-role'
    cap_paths = [sign_path, 'pki/issue/service-a-role', 'pki/revoke',
                 'pki/roles/not-authorized-test', paths['service-a']]
    cap = call('Certificate manager effective capabilities', 'sys/capabilities-self', token=cm,
               method='POST', payload={'paths': cap_paths})['data']
    checks.condition('Certificate manager least privilege',
                     'update' in cap.get(sign_path, []) and
                     all(cap.get(path) == ['deny'] for path in cap_paths[1:]))
    call('Certificate manager denied application secret', paths['service-a'], token=cm, expected=(403,))
    call('Certificate manager denied PKI role administration', 'pki/roles/not-authorized-test', token=cm, expected=(403,))
    call('Certificate manager denied issue endpoint', 'pki/issue/service-a-role', token=cm,
         method='POST', payload={}, expected=(403,))
    call('Invalid PKI role denied', 'pki/sign/not-authorized-test', token=cm,
         method='POST', payload={}, expected=(403,))

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'service-a.mesh.test')])
    csr = (x509.CertificateSigningRequestBuilder().subject_name(subject)
           .add_extension(x509.SubjectAlternativeName([x509.DNSName('service-a.mesh.test')]), False)
           .sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode('ascii'))
    payload = {'csr': csr, 'common_name': 'service-a.mesh.test', 'ttl': '1h'}
    call('Service A denied certificate signing', sign_path, token=tokens['service-a'],
         method='POST', payload=payload, expected=(403,))
    signed = call('Certificate manager signs approved CSR', sign_path, token=cm,
                  method='POST', payload=payload)['data']
    cert = x509.load_pem_x509_certificate(signed['certificate'].encode())
    ca_body = call('Retrieve CA certificate', 'pki/cert/ca', token=cm)['data']
    ca = x509.load_pem_x509_certificate(ca_body['certificate'].encode())
    cert.verify_directly_issued_by(ca)
    now = datetime.datetime.now(datetime.timezone.utc)
    cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    checks.condition('Certificate subject, SAN and validity',
                     cn == 'service-a.mesh.test' and sans == ['service-a.mesh.test'] and
                     cert.not_valid_before_utc <= now < cert.not_valid_after_utc)
    checks.condition('Certificate signed by retrieved CA', cert.issuer == ca.subject)
    chain = call('Retrieve CA chain', 'pki/ca_chain', token=cm, raw=True)
    chain_certs = x509.load_pem_x509_certificates(chain)
    checks.condition('Retrieved CA is in chain', any(c.fingerprint(hashes.SHA256()) == ca.fingerprint(hashes.SHA256()) for c in chain_certs))
    stored = call('Retrieve disposable certificate', 'pki/cert/'+signed['serial_number'], token=cm)['data']
    checks.condition('Retrieved certificate matches issued certificate',
                     x509.load_pem_x509_certificate(stored['certificate'].encode()).fingerprint(hashes.SHA256()) == cert.fingerprint(hashes.SHA256()))
    call('Revoke only disposable test certificate', 'pki/revoke', token=admin, method='POST',
         payload={'serial_number': signed['serial_number']})
    crl_data = call('Retrieve CRL', 'pki/cert/crl', token=cm)['data']
    crl = x509.load_pem_x509_crl(crl_data['certificate'].encode())
    ca.public_key().verify(crl.signature, crl.tbs_certlist_bytes, ec.ECDSA(crl.signature_hash_algorithm))
    checks.condition('Disposable certificate appears in signed CRL',
                     crl.get_revoked_certificate_by_serial_number(cert.serial_number) is not None)
    call('Revoke disposable Service B token', 'auth/token/revoke', token=admin, method='POST',
         payload={'token': tokens['service-b']}, expected=(200, 204))
    call('Revoked service token denied', paths['service-b'], token=tokens['service-b'], expected=(403,))
    return {'vault_version': version, 'certificate_algorithm_tested': 'ECDSA P-256',
            'certificate_not_before_utc': cert.not_valid_before_utc.isoformat(),
            'certificate_not_after_utc': cert.not_valid_after_utc.isoformat()}


def main():
    checks = Checks()
    admin = getpass.getpass('Vault administrative token (hidden): ')
    metadata = {}
    overall = 'INCOMPLETE'
    try:
        metadata = run(admin, checks=checks)
        overall = 'PASS'
    except Exception as exc:
        print('BLOCKED or FAIL:', type(exc).__name__, flush=True)
        overall = 'INCOMPLETE'
    finally:
        admin = None
        RESULTS.parent.mkdir(exist_ok=True)
        RESULTS.write_text(json.dumps({'overall': overall, 'metadata': metadata,
                                       'checks': checks.records}, indent=2), encoding='utf-8')
    print('Overall:', overall, '; sanitized results saved to', RESULTS, flush=True)
    return 0 if overall == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
