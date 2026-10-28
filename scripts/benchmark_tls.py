"""Benchmark real TLS 1.3 connection-establishment latency.

This script measures process-inclusive connection duration for either X25519
(classical) or X25519MLKEM768 (hybrid) key exchange. Every sample
uses a new TCP+TLS connection, and the script verifies the negotiated
group before starting measurements.

Usage:
    python scripts/benchmark_tls.py --mode classical \
        --host localhost --port 8443 --ca-file certs/ca.pem \
        --warmup 10 --iterations 100 --output-dir results/week2/classical

    python scripts/benchmark_tls.py --mode hybrid \
        --host localhost --port 8443 --ca-file certs/ca.pem \
        --warmup 10 --iterations 100 --output-dir results/week2/hybrid
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import ssl
import statistics
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Sequence

from verify_tls_group import verify_tls_group

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

RAW_CSV_COLUMNS = (
    "run_id",
    "timestamp_utc",
    "mode",
    "attempt",
    "success",
    "latency_ms",
    "tls_version",
    "negotiated_group",
    "certificate_verified",
    "session_reused",
    "error_type",
)


# ---------------------------------------------------------------------------
# TLS connection measurement
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TLSSample:
    """One TLS connection-establishment timing observation."""
    run_id: str
    timestamp_utc: str
    mode: str
    attempt: int
    success: bool
    latency_ms: float
    tls_version: str
    negotiated_group: str
    certificate_verified: bool
    session_reused: bool | None
    error_type: str

    def csv_row(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "timestamp_utc": self.timestamp_utc,
            "mode": self.mode,
            "attempt": str(self.attempt),
            "success": str(self.success),
            "latency_ms": f"{self.latency_ms:.6f}",
            "tls_version": self.tls_version,
            "negotiated_group": self.negotiated_group,
            "certificate_verified": str(self.certificate_verified),
            "session_reused": str(self.session_reused),
            "error_type": self.error_type,
        }


def _measure_single_connection(
    host: str,
    port: int,
    server_name: str,
    timeout: float,
    mode: str,
    attempt: int,
    run_id: str,
    ca_file: str | None,
    client_cert: str | None,
    client_key: str | None,
    openssl_path: str | None,
) -> TLSSample:
    """Measure one fresh, directly verified TLS connection.

    This deliberately runs a new ``openssl s_client`` process for every
    sample. The timing includes client process startup, TCP setup, and TLS
    handshake completion, so it is connection-establishment latency rather
    than pure in-library handshake latency. ``s_client`` is also the source
    of the per-sample, certificate-validated negotiated-group evidence.
    """
    ts = datetime.now(timezone.utc).isoformat()

    start_ns = time.perf_counter_ns()
    verification = verify_tls_group(
        mode=mode,
        host=host,
        port=port,
        server_name=server_name,
        ca_file=ca_file,
        client_cert=client_cert,
        client_key=client_key,
        timeout=timeout,
        use_openssl=True,
        openssl_path=openssl_path,
    )
    elapsed_ns = time.perf_counter_ns() - start_ns
    tls_version = str(verification.get("tls_version") or "")
    negotiated_group = str(verification.get("negotiated_group") or "")
    verified = (
        verification.get("connection_succeeded")
        and verification.get("certificate_verified")
        and verification.get("negotiated_group_verified")
        and tls_version == "TLSv1.3"
    )
    error = "" if verified else str(
        verification.get("error")
        or "VerificationError: TLS 1.3, certificate, or negotiated group was not verified"
    )
    return TLSSample(
        run_id=run_id,
        timestamp_utc=ts,
        mode=mode,
        attempt=attempt,
        success=bool(verified),
        latency_ms=elapsed_ns / 1_000_000,
        tls_version=tls_version,
        negotiated_group=negotiated_group,
        certificate_verified=bool(verification.get("certificate_verified")),
        session_reused=None,
        error_type=error,
    )


# ---------------------------------------------------------------------------
# Statistics (reuses the project's percentile approach)
# ---------------------------------------------------------------------------

def percentile_linear(values: Sequence[float], p: float) -> float:
    """Linearly interpolated percentile, same method as Day 5."""
    if not values:
        raise ValueError("empty sequence")
    if not 0 <= p <= 100:
        raise ValueError("percentile must be 0–100")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * (p / 100)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def compute_statistics(latencies_ms: Sequence[float]) -> dict:
    """Calculate summary statistics for a list of latency values in ms."""
    if not latencies_ms:
        return {
            "count": 0,
            "mean_ms": None,
            "stddev_ms": None,
            "min_ms": None,
            "max_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
        }

    values = list(latencies_ms)
    return {
        "count": len(values),
        "mean_ms": statistics.mean(values),
        "stddev_ms": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min_ms": min(values),
        "max_ms": max(values),
        "p50_ms": percentile_linear(values, 50),
        "p95_ms": percentile_linear(values, 95),
        "p99_ms": percentile_linear(values, 99),
    }


def relative_overhead(classical_ms: float, hybrid_ms: float) -> tuple[float, float | None]:
    """Return (difference_ms, percentage) or (diff, None) if baseline invalid."""
    diff = hybrid_ms - classical_ms
    if classical_ms > 0 and math.isfinite(classical_ms):
        return diff, (diff / classical_ms) * 100
    return diff, None


# ---------------------------------------------------------------------------
# Prerequisites check
# ---------------------------------------------------------------------------

def check_prerequisites(
    mode: str,
    host: str,
    port: int,
    server_name: str,
    ca_file: str | None,
    client_cert: str | None,
    client_key: str | None,
    timeout: float,
    openssl_path: str | None,
) -> tuple[list[str], dict | None]:
    """Return blocking issues and direct pre-run group-verification evidence."""
    issues: list[str] = []

    if mode not in EXPECTED_GROUPS:
        issues.append(f"Unknown mode: {mode}")
        return issues, None

    verification = verify_tls_group(
        mode=mode,
        host=host,
        port=port,
        server_name=server_name,
        ca_file=ca_file,
        client_cert=client_cert,
        client_key=client_key,
        timeout=timeout,
        use_openssl=True,
        openssl_path=openssl_path,
    )
    expected_group = EXPECTED_GROUPS[mode]
    if not verification.get("connection_succeeded"):
        issues.append(str(verification.get("error") or "TLS verification connection failed"))
    if verification.get("tls_version") != "TLSv1.3":
        issues.append(f"Expected TLSv1.3, observed {verification.get('tls_version')!r}")
    if not verification.get("certificate_verified"):
        issues.append("Certificate verification did not succeed")
    if not verification.get("negotiated_group_verified"):
        issues.append(
            f"Negotiated group was not directly verified as {expected_group}; "
            f"observed {verification.get('negotiated_group')!r}"
        )

    return issues, verification


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_tls_benchmark(
    mode: str,
    host: str,
    port: int,
    server_name: str | None = None,
    ca_file: str | None = None,
    client_cert: str | None = None,
    client_key: str | None = None,
    warmup: int = 10,
    iterations: int = 100,
    timeout: float = 10.0,
    run_id: str | None = None,
    openssl_path: str | None = None,
) -> tuple[list[TLSSample], dict]:
    """Execute the benchmark and return (samples, metadata)."""

    if mode not in EXPECTED_GROUPS:
        raise ValueError(f"mode must be one of {tuple(EXPECTED_GROUPS)}")
    if warmup < 0:
        raise ValueError("warmup must be non-negative")
    if iterations < 1:
        raise ValueError("iterations must be at least 1")

    effective_sni = server_name or host
    effective_run_id = run_id or uuid.uuid4().hex[:12]

    # --- Prerequisites ---
    issues, preflight_verification = check_prerequisites(
        mode,
        host,
        port,
        effective_sni,
        ca_file,
        client_cert,
        client_key,
        timeout,
        openssl_path,
    )
    if issues:
        raise RuntimeError(
            "Prerequisites not met. Cannot start benchmark.\n"
            + "\n".join(f"  • {issue}" for issue in issues)
        )

    # --- Warm-up (excluded from statistics, retained in metadata) ---
    print(f"[INFO] Warming up with {warmup} connections...")
    warmup_samples = []
    for i in range(warmup):
        warmup_samples.append(_measure_single_connection(
            host, port, effective_sni, timeout, mode, -(warmup - i), effective_run_id,
            ca_file, client_cert, client_key, openssl_path,
        ))

    # --- Measured connections ---
    print(f"[INFO] Measuring {iterations} connections...")
    samples: list[TLSSample] = []
    for i in range(1, iterations + 1):
        sample = _measure_single_connection(
            host, port, effective_sni, timeout, mode, i, effective_run_id,
            ca_file, client_cert, client_key, openssl_path,
        )
        samples.append(sample)
        if i % 100 == 0 or i == iterations:
            successes = sum(1 for s in samples if s.success)
            print(
                f"  [{i}/{iterations}] "
                f"success={successes}/{i} "
                f"last_latency={sample.latency_ms:.3f}ms"
            )

    # --- Build metadata ---
    successful = [s for s in samples if s.success]
    failed = [s for s in samples if not s.success]
    success_latencies = [s.latency_ms for s in successful]

    metadata = {
        "run_id": effective_run_id,
        "mode": mode,
        "expected_group": EXPECTED_GROUPS[mode],
        "host": host,
        "port": port,
        "server_name": effective_sni,
        "ca_file": ca_file or "system_default",
        "client_cert_used": bool(client_cert),
        "warmup_connections": warmup,
        "warmup_attempts": [sample.csv_row() for sample in warmup_samples],
        "session_evidence": "Unknown: fresh process, no session input and -no_ticket constrain resumption but do not independently prove it.",
        "measured_connections": iterations,
        "timeout_seconds": timeout,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "openssl_backend": ssl.OPENSSL_VERSION,
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "processor": platform.processor(),
        "successful_count": len(successful),
        "failed_count": len(failed),
        "success_rate": len(successful) / len(samples) if samples else 0,
        "statistics": compute_statistics(success_latencies),
        "tls_client": "openssl_s_client",
        "tls_server_version": "unknown; supply server provenance separately",
        "server_configuration": "unknown; supply server provenance separately",
        "network_path": "unspecified; document endpoint and network path separately",
        "openssl_path": openssl_path or "PATH:openssl",
        "connection_type": "fresh_process_tcp_tls",
        "session_resumption_policy": "new openssl process per sample; -no_ticket; no -sess_in",
        "timing_description": (
            "Connection-establishment latency: from immediately before "
            "openssl s_client starts through direct TLS 1.3 group and "
            "certificate verification and process exit. Includes client process startup, TCP setup, and shutdown."
        ),
        "group_verification_method": "openssl s_client direct per-connection output",
        "preflight_verification": preflight_verification,
    }

    try:
        client_version = subprocess.run(
            [preflight_verification["openssl_path"], "version"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        metadata["openssl_client_version"] = client_version.stdout.strip()
    except (OSError, subprocess.SubprocessError, KeyError):
        metadata["openssl_client_version"] = "unavailable"

    try:
        import subprocess as sp
        git_result = sp.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        if git_result.returncode == 0:
            metadata["git_commit"] = git_result.stdout.strip()
    except Exception:
        metadata["git_commit"] = "unavailable"

    return samples, metadata


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_results(
    samples: list[TLSSample],
    metadata: dict,
    output_dir: Path,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Save raw CSV, metadata, and verification evidence without data loss."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw.csv"
    meta_path = output_dir / "metadata.json"
    summary_path = output_dir / "summary.txt"
    verification_path = output_dir / "verification.json"
    existing = [path for path in (raw_path, meta_path, summary_path, verification_path) if path.exists()]
    if existing and not overwrite:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing benchmark artifacts ({names}) in {output_dir}. "
            "Choose a new --output-dir or pass --overwrite after preserving the run."
        )

    # Raw CSV
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_CSV_COLUMNS)
        writer.writeheader()
        for sample in samples:
            writer.writerow(sample.csv_row())

    # Metadata JSON
    meta_path.write_text(
        json.dumps(metadata, indent=2, default=str),
        encoding="utf-8",
    )

    verification_path.write_text(
        json.dumps(metadata.get("preflight_verification", {}), indent=2, default=str),
        encoding="utf-8",
    )

    # Summary text
    stats = metadata.get("statistics", {})
    lines = [
        f"TLS Benchmark Summary — {metadata.get('mode', 'unknown').upper()}",
        f"{'=' * 50}",
        f"Run ID:          {metadata.get('run_id')}",
        f"Target:          {metadata.get('host')}:{metadata.get('port')}",
        f"Expected group:  {metadata.get('expected_group')}",
        f"Warmup:          {metadata.get('warmup_connections')}",
        f"Measured:        {metadata.get('measured_connections')}",
        f"Successful:      {metadata.get('successful_count')}",
        f"Failed:          {metadata.get('failed_count')}",
        f"Success rate:    {metadata.get('success_rate', 0):.1%}",
        "",
        "Latency Statistics (ms):",
        f"  p50:   {stats.get('p50_ms', 'N/A')}",
        f"  p95:   {stats.get('p95_ms', 'N/A')}",
        f"  p99:   {stats.get('p99_ms', 'N/A')}",
        f"  mean:  {stats.get('mean_ms', 'N/A')}",
        f"  stdev: {stats.get('stddev_ms', 'N/A')}",
        f"  min:   {stats.get('min_ms', 'N/A')}",
        f"  max:   {stats.get('max_ms', 'N/A')}",
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "raw": raw_path,
        "metadata": meta_path,
        "summary": summary_path,
        "verification": verification_path,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark TLS 1.3 connection-establishment latency for "
            "classical (X25519) or hybrid (X25519MLKEM768) key exchange."
        ),
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=tuple(EXPECTED_GROUPS),
        help="'classical' for X25519, 'hybrid' for X25519MLKEM768",
    )
    parser.add_argument("--host", required=True, help="TLS server hostname or IP")
    parser.add_argument("--port", type=int, required=True, help="TLS server port")
    parser.add_argument("--server-name", default=None, help="SNI server name")
    parser.add_argument("--ca-file", default=None, help="CA certificate file")
    parser.add_argument("--client-cert", default=None, help="Client cert for mTLS")
    parser.add_argument("--client-key", default=None, help="Client key for mTLS")
    parser.add_argument("--warmup", type=int, default=10, help="Warm-up connections (default: 10)")
    parser.add_argument("--iterations", type=int, default=100, help="Measured connections (default: 100)")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-connection timeout (s)")
    parser.add_argument(
        "--openssl-path",
        default=None,
        help="Path to a compatible openssl executable (defaults to PATH lookup)",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for results")
    parser.add_argument("--run-id", default=None, help="Unique run identifier")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace artifacts in an existing output directory after preserving them",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print(f"[INFO] TLS Benchmark — {args.mode.upper()} mode")
    print(f"[INFO] Target: {args.host}:{args.port}")
    print(f"[INFO] Expected group: {EXPECTED_GROUPS[args.mode]}")
    print(f"[INFO] OpenSSL backend: {ssl.OPENSSL_VERSION}")

    try:
        samples, metadata = run_tls_benchmark(
            mode=args.mode,
            host=args.host,
            port=args.port,
            server_name=args.server_name,
            ca_file=args.ca_file,
            client_cert=args.client_cert,
            client_key=args.client_key,
            warmup=args.warmup,
            iterations=args.iterations,
            timeout=args.timeout,
            run_id=args.run_id,
            openssl_path=args.openssl_path,
        )
    except RuntimeError as exc:
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        return 1

    try:
        paths = write_results(samples, metadata, args.output_dir, overwrite=args.overwrite)
    except FileExistsError as exc:
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        return 1

    successful = sum(1 for s in samples if s.success)
    print(f"\n[DONE] {successful}/{len(samples)} connections succeeded")
    print(f"[DONE] Raw data:  {paths['raw']}")
    print(f"[DONE] Metadata:  {paths['metadata']}")
    print(f"[DONE] Verification: {paths['verification']}")
    print(f"[DONE] Summary:   {paths['summary']}")

    if successful == 0:
        print("[FAIL] No successful connections. Results are not usable.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
