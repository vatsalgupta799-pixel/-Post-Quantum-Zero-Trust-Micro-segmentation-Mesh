# Day 1 assessment evidence — 23 November 2026

This directory supports the [architecture assessment](../../docs/week4_architecture_assessment.md) and [cryptographic inventory](../../docs/cryptographic_inventory.md). It contains new read-only inspection results and offline test output, not a new deployment or live Kubernetes validation.

**Follow-up:** the user subsequently requested live Vault verification. The [live verification addendum](vault-live/README.md) supersedes the initial unavailable-Vault status: the existing instance is running/unsealed, configuration was audited privately and its default CA was confirmed expired. Initial evidence files below are preserved unchanged.

| File | Scope |
|---|---|
| [inspection.json](inspection.json) | Tool availability, explicitly located binary versions, public certificate metadata, sensitive field names only, failed unauthenticated local Vault reads, and saved benchmark CSV checks. |
| [offline-tests.txt](offline-tests.txt) | Initial combined pytest collection failure, followed by 43 passing selected cryptographic tests and 16 passing key-rotation unittest checks. No live Vault tests or certificate issuance. |
| [pcap-summary.json](pcap-summary.json) | Offline inspection of two existing Ethernet/IPv4/TCP captures. Public Hello group IDs/key-share lengths and selected version only; no application payload, private keys or decryption. |
| [validation.json](validation.json) | File-preservation, relative-link, diagram-consistency and evidence checks performed after authoring. |
| [source-sha256.json](source-sha256.json) | Before-assessment SHA-256 hashes of 297 original project files; compared again after work to confirm they were unchanged. This is a local preservation record, not an independent signature or upstream authenticity guarantee. |

The baseline excludes `.tmp`, Git metadata, Python/test caches and local Vault binary/data/recovery directories. Those Vault directories were not modified. Existing scripts that configure Vault, generate certificates, apply manifests or isolate workloads were not executed. Public certificate contents in Secret backups were decoded solely for metadata; private-key fields were not decoded or reproduced.

## Test reproduction

The verified test commands below exercise local Python code. Run the first command from the project root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m pytest -q -p no:cacheprovider tests/test_ecdh.py tests/test_mlkem.py tests/test_hybrid.py tests/test_integration.py tests/test_hybrid_key_exchange.py
```

Run the key-rotation tests with `src` as the working directory:

```powershell
python -m unittest -q Test_key_rotation
```

The current key-rotation test file imports `Key_rotation` as a top-level module. Including `src/Test_key_rotation.py` in the initial root pytest invocation caused `ModuleNotFoundError`; running its existing unittest suite from `src` succeeded. No implementation or test source was changed. This is a test-invocation limitation, not a claim that all project tests pass.

Binary checks ran `version` only against `C:\Program Files\OpenSSL-Win64\bin\openssl.exe` and `vault\bin\vault.exe`. The available Python cryptography backend is OpenSSL 4.0.3; this is different from the standalone 4.1.0 executable.

The local Vault checks were unauthenticated GETs to `http://127.0.0.1:8200/v1/sys/health` and `/v1/pki/ca`, with short timeouts and no proxy. They failed with connection-layer `URLError`; no conclusion about sealed/unsealed state is possible. No token, Secret ID or recovery share was read or requested.

## Historical evidence limitations

The November 13 integration report references these artifacts that are absent from this checkout: `inject-opa-envoy.yaml`, `evidence-hybrid-mtls-negative.txt`, `evidence-hybrid-mtls-positive.txt`, `evidence-kubernetes-classical-mtls-positive.txt`, `evidence-kubernetes-hybrid-compatibility.txt` and `evidence-opa-decision-logs.txt`. Their reported results remain historical report claims rather than directly rechecked raw outputs.

The two saved TLS CSVs each contain 200 successful observations, split equally by group. Reading their success flags is not a new certificate validation. The current Envoy certificate fingerprint differs from the one in the accompanying study notes; the report explicitly preserves that discrepancy.

The PCAP inspection reassembled the small saved TCP streams, read cleartext ClientHello/ServerHello key-share extensions and recorded packet/file sizes. This is not a general packet-analysis tool or a proof of full handshake completion. The original HNDL report supplies the experiment's context and its certificate-verification warnings.

The Mermaid source was checked against the assessment and source evidence, including separation of Kubernetes, local Vault and standalone hybrid paths. Validation records distinguish structural checks from a graphical renderer run.
