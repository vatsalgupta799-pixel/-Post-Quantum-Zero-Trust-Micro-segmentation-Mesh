"""Verify the TLS 1.3 negotiated key-exchange group for a given endpoint.

This script establishes a real TLS connection and inspects the negotiation
outcome. It exits 0 only when TLS 1.3 **and** the expected named group
are confirmed through reliable evidence. It never infers a group from a
configuration file alone.

Usage:
    python scripts/verify_tls_group.py --mode classical \
        --host localhost --port 8443 --ca-file certs/ca.pem

    python scripts/verify_tls_group.py --mode hybrid \
        --host localhost --port 8443 --ca-file certs/ca.pem

    python scripts/verify_tls_group.py --mode classical \
        --host localhost --port 8443 --ca-file certs/ca.pem \
        --use-openssl
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import ssl
import subprocess
import ipaddress
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_GROUPS = {
    "classical": "X25519",
    "hybrid": "X25519MLKEM768",
}

SUPPORTED_MODES = tuple(EXPECTED_GROUPS)
NEGOTIATED_GROUP_PATTERNS = (
    r"Server Temp Key:\s*(\S+)",
    r"Peer Temp Key:\s*(\S+)",
    r"Negotiated TLS1\.3 group:\s*(\S+)",
    r"Negotiated group:\s*(\S+)",
    r"Group:\s*(\S+)",
    r"group:\s*(\S+)",
)


# ---------------------------------------------------------------------------
# Python ssl verification
# ---------------------------------------------------------------------------

def _verify_with_python_ssl(
    host: str,
    port: int,
    server_name: str,
    ca_file: str | None,
    client_cert: str | None,
    client_key: str | None,
    mode: str,
    timeout: float,
) -> dict:
    """Attempt a TLS connection using Python's ssl module.

    Python's ssl.SSLContext wraps OpenSSL. On most distributions, OpenSSL 3.0.x
    does NOT expose X25519MLKEM768. This function tries to set the requested
    group and clearly fails if it cannot.
    """
    expected_group = EXPECTED_GROUPS[mode]
    result: dict = {
        "method": "python_ssl",
        "host": host,
        "port": port,
        "server_name": server_name,
        "mode": mode,
        "expected_group": expected_group,
        "tls_version": None,
        "negotiated_group": None,
        "negotiated_group_verified": False,
        "certificate_verified": False,
        "connection_succeeded": False,
        "new_handshake": None,
        "error": None,
        "openssl_backend": ssl.OPENSSL_VERSION,
    }

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3

    if ca_file:
        ctx.load_verify_locations(cafile=ca_file)
    else:
        ctx.load_default_certs()

    if client_cert and client_key:
        ctx.load_cert_chain(certfile=client_cert, keyfile=client_key)

    # Attempt to restrict the key-exchange group.
    try:
        ctx.set_ecdh_curve(expected_group)
    except Exception as exc:
        result["error"] = (
            f"Python ssl cannot set group '{expected_group}': {exc}. "
            f"The underlying OpenSSL ({ssl.OPENSSL_VERSION}) likely does "
            f"not support this group."
        )
        return result

    try:
        with socket.create_connection((host, port), timeout=timeout) as raw_sock:
            with ctx.wrap_socket(raw_sock, server_hostname=server_name) as tls_sock:
                result["connection_succeeded"] = True
                result["tls_version"] = tls_sock.version()
                result["certificate_verified"] = True  # No exception ⇒ verified.

                # Python's ssl module does not expose `get_negotiated_group()`.
                # We can only confirm TLS 1.3 was used and the context was
                # configured for that single group. We flag this limitation.
                cipher = tls_sock.cipher()
                result["cipher_suite"] = cipher[0] if cipher else None
                result["negotiated_group"] = (
                    f"CONFIGURED_ONLY:{expected_group}"
                )
                result["negotiated_group_verified"] = False
                result["limitation"] = (
                    "Python ssl module does not expose the negotiated "
                    "key-exchange group directly. The context was configured "
                    f"for {expected_group} only, but server selection cannot "
                    "be independently verified through this method."
                )
    except ssl.SSLError as exc:
        result["error"] = f"TLS error: {exc}"
    except (ConnectionRefusedError, TimeoutError, OSError) as exc:
        result["error"] = f"Connection error: {exc}"

    return result


# ---------------------------------------------------------------------------
# openssl s_client verification
# ---------------------------------------------------------------------------

def _find_openssl(openssl_path: str | None = None) -> str | None:
    """Return an explicitly supplied or PATH-resolved OpenSSL executable."""
    if openssl_path:
        candidate = Path(openssl_path)
        if not candidate.is_file():
            return None
        return str(candidate)
    return shutil.which("openssl")


def _verify_with_openssl(
    host: str,
    port: int,
    server_name: str,
    ca_file: str | None,
    client_cert: str | None,
    client_key: str | None,
    mode: str,
    timeout: float,
    openssl_path: str | None = None,
) -> dict:
    """Verify negotiated group using `openssl s_client`.

    openssl s_client -connect HOST:PORT -tls1_3 -groups GROUP -brief
    prints the negotiated group in its output, so it serves as reliable
    evidence of the server's actual selection.
    """
    expected_group = EXPECTED_GROUPS[mode]
    openssl_path = _find_openssl(openssl_path)

    result: dict = {
        "method": "openssl_s_client",
        "host": host,
        "port": port,
        "server_name": server_name,
        "mode": mode,
        "expected_group": expected_group,
        "tls_version": None,
        "negotiated_group": None,
        "negotiated_group_verified": False,
        "certificate_verified": False,
        "connection_succeeded": False,
        "new_handshake": None,
        "error": None,
        "openssl_path": openssl_path,
    }

    if openssl_path is None:
        result["error"] = (
            "openssl CLI not found on PATH. Install OpenSSL or provide "
            "--use-openssl only when it is available."
        )
        return result

    cmd = [
        openssl_path, "s_client",
        "-connect", f"{host}:{port}",
        "-tls1_3",
        "-groups", expected_group,
        "-servername", server_name,
        "-brief",
        "-no_ticket",
        "-verify_return_error",
    ]
    try:
        ipaddress.ip_address(server_name)
    except ValueError:
        cmd += ["-verify_hostname", server_name]
    else:
        cmd += ["-verify_ip", server_name]
    if ca_file:
        cmd += ["-CAfile", ca_file]
    if client_cert:
        cmd += ["-cert", client_cert]
    if client_key:
        cmd += ["-key", client_key]

    try:
        proc = subprocess.run(
            cmd,
            input="",  # send empty stdin to make s_client exit
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = proc.stdout + "\n" + proc.stderr

        # Parse TLS version
        tls_match = re.search(
            r"Protocol(?:\s+version)?\s*:\s*(TLSv[\d.]+)",
            output,
            re.IGNORECASE,
        )
        if tls_match:
            result["tls_version"] = tls_match.group(1)

        # Parse negotiated group — openssl reports as "Server Temp Key:"
        # or "Negotiated group:" depending on version
        for pattern in NEGOTIATED_GROUP_PATTERNS:
            group_match = re.search(pattern, output, re.IGNORECASE)
            if group_match:
                result["negotiated_group"] = group_match.group(1).rstrip(",")
                break

        # OpenSSL's normal and --brief formats use different success text.
        if (
            re.search(r"Verify return code:\s*0\s", output)
            or re.search(r"Verification:\s*OK", output, re.IGNORECASE)
        ):
            result["certificate_verified"] = True

        if proc.returncode == 0 and re.search(r"CONNECTION ESTABLISHED", output, re.IGNORECASE):
            result["connection_succeeded"] = True
        elif proc.returncode != 0:
            result["error"] = f"openssl s_client exited with status {proc.returncode}"

        # Verify the negotiated group matches the expected one
        if result["negotiated_group"]:
            actual_group = result["negotiated_group"]
            # Normalize — some openssl versions report differently
            if actual_group.lower() == expected_group.lower():
                result["negotiated_group_verified"] = True

        result["raw_output_snippet"] = output[:2000]

    except subprocess.TimeoutExpired:
        result["error"] = f"openssl s_client timed out after {timeout}s"
    except FileNotFoundError:
        result["error"] = "openssl binary not found"
    except Exception as exc:
        result["error"] = f"openssl verification failed: {exc}"

    return result


# ---------------------------------------------------------------------------
# Main verification logic
# ---------------------------------------------------------------------------

def verify_tls_group(
    mode: str,
    host: str,
    port: int,
    server_name: str | None = None,
    ca_file: str | None = None,
    client_cert: str | None = None,
    client_key: str | None = None,
    timeout: float = 10.0,
    use_openssl: bool = False,
    openssl_path: str | None = None,
) -> dict:
    """Run verification and return a structured result dictionary."""

    if mode not in SUPPORTED_MODES:
        raise ValueError(f"mode must be one of {SUPPORTED_MODES}, got '{mode}'")

    effective_server_name = server_name or host

    if use_openssl:
        return _verify_with_openssl(
            host, port, effective_server_name,
            ca_file, client_cert, client_key, mode, timeout, openssl_path,
        )
    else:
        return _verify_with_python_ssl(
            host, port, effective_server_name,
            ca_file, client_cert, client_key, mode, timeout,
        )


def print_verification_result(result: dict) -> None:
    """Print a human-readable verification summary."""
    mode = result.get("mode", "unknown")
    expected = result.get("expected_group", "unknown")
    method = result.get("method", "unknown")

    print(f"\n{'=' * 60}")
    print(f"TLS Group Verification — {mode.upper()} mode")
    print(f"{'=' * 60}")
    print(f"Method:             {method}")
    print(f"Target:             {result.get('host')}:{result.get('port')}")
    print(f"Expected group:     {expected}")
    print(f"TLS version:        {result.get('tls_version', 'N/A')}")
    print(f"Negotiated group:   {result.get('negotiated_group', 'N/A')}")
    print(f"Group verified:     {result.get('negotiated_group_verified', False)}")
    print(f"Certificate valid:  {result.get('certificate_verified', False)}")
    print(f"Connection OK:      {result.get('connection_succeeded', False)}")

    if result.get("limitation"):
        print(f"\n[LIMITATION] {result['limitation']}")

    if result.get("error"):
        print(f"\n[ERROR] {result['error']}")

    # Final verdict
    if result.get("negotiated_group_verified") and result.get("connection_succeeded") and result.get("certificate_verified"):
        tls_ver = result.get("tls_version", "")
        if tls_ver == "TLSv1.3":
            print(f"\n[PASS] {mode.upper()}: TLS 1.3 + {expected} VERIFIED")
        else:
            print(f"\n[WARN] Connection succeeded but TLS version is {tls_ver}, not 1.3")
    elif result.get("connection_succeeded") and not result.get("negotiated_group_verified"):
        print(
            f"\n[WARN] Connection succeeded but the negotiated group "
            f"could not be independently verified as {expected}."
        )
    else:
        print(f"\n[FAIL] {mode.upper()}: Verification FAILED")

    print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the TLS 1.3 negotiated key-exchange group for classical "
            "or hybrid mode. Exits 0 only when the expected group is verified."
        ),
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=SUPPORTED_MODES,
        help="'classical' for X25519, 'hybrid' for X25519MLKEM768",
    )
    parser.add_argument("--host", required=True, help="TLS server hostname or IP")
    parser.add_argument("--port", type=int, required=True, help="TLS server port")
    parser.add_argument("--server-name", default=None, help="SNI server name (defaults to --host)")
    parser.add_argument("--ca-file", default=None, help="CA certificate file for verification")
    parser.add_argument("--client-cert", default=None, help="Client certificate for mTLS")
    parser.add_argument("--client-key", default=None, help="Client private key for mTLS")
    parser.add_argument("--timeout", type=float, default=10.0, help="Connection timeout in seconds")
    parser.add_argument(
        "--use-openssl",
        action="store_true",
        help="Use openssl s_client instead of Python ssl (recommended for group verification)",
    )
    parser.add_argument(
        "--openssl-path",
        default=None,
        help="Path to a compatible openssl executable (defaults to PATH lookup)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional: save verification result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    result = verify_tls_group(
        mode=args.mode,
        host=args.host,
        port=args.port,
        server_name=args.server_name,
        ca_file=args.ca_file,
        client_cert=args.client_cert,
        client_key=args.client_key,
        timeout=args.timeout,
        use_openssl=args.use_openssl,
        openssl_path=args.openssl_path,
    )

    result["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    print_verification_result(result)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        # Remove raw output snippet from saved JSON to keep it small
        save_result = {k: v for k, v in result.items() if k != "raw_output_snippet"}
        args.output_json.write_text(
            json.dumps(save_result, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"Verification saved to {args.output_json}")

    # Exit 0 only if the group was independently verified
    if result.get("negotiated_group_verified") and result.get("connection_succeeded") and result.get("certificate_verified"):
        tls_ver = str(result.get("tls_version", ""))
        if tls_ver == "TLSv1.3":
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
