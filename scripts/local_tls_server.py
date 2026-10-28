"""Local TLS 1.3 test server for benchmarking.

Generates an ephemeral self-signed certificate and runs a minimal
TLS 1.3 server on localhost. This lets the benchmark harness run
locally against a real TLS endpoint.

The server uses Python's ssl module wrapping OpenSSL. On the current
system (OpenSSL 3.0.18), only X25519 is available — X25519MLKEM768
is NOT supported. The hybrid experiment therefore cannot run locally
and is honestly documented as blocked.

Usage:
    python scripts/local_tls_server.py --port 18443 --group X25519
    python scripts/local_tls_server.py --port 18444 --group X25519MLKEM768
"""

from __future__ import annotations

import argparse
import os
import socket
import ssl
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CERT_DIR = PROJECT_ROOT / ".tmp" / "tls-test"


def generate_self_signed_cert(cert_dir: Path) -> tuple[Path, Path]:
    """Generate an ephemeral self-signed cert for localhost."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(hours=2))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "cert.pem"
    key_path = cert_dir / "key.pem"

    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    return cert_path, key_path


def run_server(
    port: int,
    group: str,
    cert_path: Path,
    key_path: Path,
    max_connections: int = 0,
    timeout: float = 0,
) -> None:
    """Run a minimal TLS 1.3 server."""

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(str(cert_path), str(key_path))

    try:
        ctx.set_ecdh_curve(group)
    except Exception as exc:
        print(f"[FAIL] Cannot set group '{group}': {exc}", file=sys.stderr)
        print(f"       OpenSSL backend: {ssl.OPENSSL_VERSION}", file=sys.stderr)
        raise SystemExit(1)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(128)

        if timeout > 0:
            sock.settimeout(timeout)

        print(f"[INFO] TLS 1.3 server listening on 127.0.0.1:{port}")
        print(f"[INFO] Group: {group}")
        print(f"[INFO] Cert: {cert_path}")
        print(f"[INFO] OpenSSL: {ssl.OPENSSL_VERSION}")
        if max_connections > 0:
            print(f"[INFO] Will accept {max_connections} connections then stop.")
        else:
            print("[INFO] Running until interrupted (Ctrl+C).")
        print()

        connections_served = 0
        try:
            while True:
                if max_connections > 0 and connections_served >= max_connections:
                    print(f"\n[INFO] Reached {max_connections} connections. Stopping.")
                    break

                try:
                    conn, addr = sock.accept()
                except socket.timeout:
                    print(f"\n[INFO] Timeout reached. Stopping.")
                    break

                try:
                    with ctx.wrap_socket(conn, server_side=True) as tls_conn:
                        tls_conn.sendall(b"OK")
                        connections_served += 1
                        if connections_served % 100 == 0:
                            print(f"  [{connections_served} connections served]")
                except ssl.SSLError:
                    connections_served += 1  # Count failed attempts too
                except Exception:
                    connections_served += 1
        except KeyboardInterrupt:
            pass

    print(f"\n[DONE] Served {connections_served} connections total.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a local TLS 1.3 test server for benchmarking.",
    )
    parser.add_argument(
        "--port", type=int, default=18443,
        help="Port to listen on (default: 18443)",
    )
    parser.add_argument(
        "--group", default="X25519",
        help="TLS key-exchange group (default: X25519)",
    )
    parser.add_argument(
        "--cert-dir", type=Path, default=CERT_DIR,
        help="Directory for generated certificate files",
    )
    parser.add_argument(
        "--max-connections", type=int, default=0,
        help="Stop after N connections (0 = unlimited)",
    )
    parser.add_argument(
        "--timeout", type=float, default=0,
        help="Server socket timeout in seconds (0 = no timeout)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print("[INFO] Generating self-signed certificate...")
    cert_path, key_path = generate_self_signed_cert(args.cert_dir)
    print(f"[INFO] Certificate: {cert_path}")
    print(f"[INFO] Key: {key_path}")
    print()

    try:
        run_server(
            port=args.port,
            group=args.group,
            cert_path=cert_path,
            key_path=key_path,
            max_connections=args.max_connections,
            timeout=args.timeout,
        )
    except SystemExit:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
