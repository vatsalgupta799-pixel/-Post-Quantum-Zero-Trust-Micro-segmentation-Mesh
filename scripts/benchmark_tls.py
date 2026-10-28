#!/usr/bin/env python3
"""Repeatable classical-versus-hybrid TLS connection benchmark.

Measures wall-clock time for an openssl s_client process to establish TLS.
This includes process startup and must not be interpreted as pure TLS
handshake latency. Every accepted sample must contain expected group evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "tls-benchmark"

MODES = {
    "classical": {
        "group": "X25519",
        "evidence": re.compile(r"Peer Temp Key:\s*X25519\b"),
    },
    "hybrid": {
        "group": "X25519MLKEM768",
        "evidence": re.compile(
            r"Negotiated TLS1\.3 group:\s*X25519MLKEM768\b"
        ),
    },
}

FIELDS = [
    "mode", "iteration", "expected_group", "observed_group_evidence",
    "elapsed_ms", "return_code", "success", "error",
]


def run_handshake(
    mode: str, host: str, port: int, timeout: float
) -> dict[str, object]:
    expected = MODES[mode]["group"]
    command = [
        "openssl", "s_client",
        "-connect", f"{host}:{port}",
        "-tls1_3",
        "-groups", expected,
        "-servername", "localhost",
        "-brief",
    ]

    started = time.perf_counter_ns()
    try:
        result = subprocess.run(
            command,
            input="",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        output = result.stdout or ""
        match = MODES[mode]["evidence"].search(output)
        connected = "CONNECTION ESTABLISHED" in output
        tls13 = "Protocol version: TLSv1.3" in output
        success = result.returncode == 0 and connected and tls13 and match is not None

        if match:
            evidence = match.group(0)
        else:
            evidence = ""

        problems = []
        if result.returncode != 0:
            problems.append(f"openssl_exit_{result.returncode}")
        if not connected:
            problems.append("connection_not_established")
        if not tls13:
            problems.append("TLS1.3_not_confirmed")
        if match is None:
            problems.append("expected_group_evidence_missing")

        return {
            "elapsed_ms": f"{elapsed_ms:.6f}",
            "return_code": result.returncode,
            "success": success,
            "observed_group_evidence": evidence,
            "error": ";".join(problems),
        }
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        return {
            "elapsed_ms": f"{elapsed_ms:.6f}",
            "return_code": "",
            "success": False,
            "observed_group_evidence": "",
            "error": "timeout",
        }
    except OSError as exc:
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        return {
            "elapsed_ms": f"{elapsed_ms:.6f}",
            "return_code": "",
            "success": False,
            "observed_group_evidence": "",
            "error": f"os_error:{exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark classical and hybrid TLS connections using OpenSSL."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8444)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if args.port < 1 or args.port > 65535:
        parser.error("--port must be between 1 and 65535")
    if args.warmup < 0 or args.iterations < 1:
        parser.error("--warmup must be >= 0 and --iterations must be >= 1")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be positive and finite")

    openssl = shutil.which("openssl")
    if not openssl:
        print("[FAIL] openssl executable not found", file=sys.stderr)
        return 1

    # Each run gets its own timestamped directory; prior results are preserved.
    run_dir = args.output_dir / datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        print(f"[FAIL] Cannot create output directory: {exc}", file=sys.stderr)
        return 1

    rows: list[dict[str, object]] = []
    failures = 0

    # Warm up both modes. Warm-up samples are intentionally not included in CSV.
    for mode in MODES:
        for _ in range(args.warmup):
            sample = run_handshake(mode, args.host, args.port, args.timeout)
            if not sample["success"]:
                print(
                    f"[FAIL] {mode} warm-up did not verify: {sample['error']}",
                    file=sys.stderr,
                )
                return 1

    # Alternate order to reduce consistent ordering bias.
    for iteration in range(1, args.iterations + 1):
        modes = ("classical", "hybrid") if iteration % 2 else ("hybrid", "classical")
        for mode in modes:
            sample = run_handshake(mode, args.host, args.port, args.timeout)
            row = {
                "mode": mode,
                "iteration": iteration,
                "expected_group": MODES[mode]["group"],
                **sample,
            }
            rows.append(row)
            if not sample["success"]:
                failures += 1
                print(
                    f"[FAIL] {mode} sample {iteration}: {sample['error']}",
                    file=sys.stderr,
                )

    raw_path = run_dir / "tls_handshake_samples.csv"
    summary_path = run_dir / "tls_handshake_summary.csv"
    metadata_path = run_dir / "environment.json"
    report_path = run_dir / "report.md"

    with raw_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    summaries = []
    for mode in MODES:
        mode_rows = [r for r in rows if r["mode"] == mode]
        valid = [float(r["elapsed_ms"]) for r in mode_rows if r["success"]]
        summaries.append({
            "mode": mode,
            "expected_group": MODES[mode]["group"],
            "attempts": len(mode_rows),
            "successes": len(valid),
            "failures": len(mode_rows) - len(valid),
            "success_rate_percent": (
                100 * len(valid) / len(mode_rows) if mode_rows else 0
            ),
            "mean_ms": statistics.mean(valid) if valid else None,
            "median_ms": statistics.median(valid) if valid else None,
            "p95_ms": (
                sorted(valid)[math.ceil(0.95 * len(valid)) - 1]
                if valid else None
            ),
        })

    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "host": args.host,
        "port": args.port,
        "warmup_per_mode": args.warmup,
        "measured_iterations_per_mode": args.iterations,
        "timeout_seconds": args.timeout,
        "python": sys.version,
        "platform": platform.platform(),
        "openssl_version": subprocess.run(
            [openssl, "version"], capture_output=True, text=True, check=False
        ).stdout.strip(),
        "measurement_definition": (
            "Wall-clock duration of launching openssl s_client and completing "
            "a TLS connection; includes process startup and local connection "
            "overhead, not pure TLS handshake latency."
        ),
        "certificate_validation": (
            "The temporary self-signed localhost certificate is not trusted; "
            "this benchmark validates TLS connection and group evidence, not "
            "certificate identity or production trust."
        ),
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Classical versus hybrid TLS connection benchmark",
        "",
        f"- Target: `{args.host}:{args.port}`",
        f"- Measured iterations per mode: {args.iterations}",
        f"- Warm-ups per mode: {args.warmup}",
        "- Measurement includes OpenSSL process startup and local connection overhead.",
        "- The temporary self-signed certificate is not a production trust test.",
        "",
        "| Mode | Expected group | Successes | Failures | Success rate | Median (ms) | p95 (ms) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        median = (
            f"{summary['median_ms']:.3f}"
            if summary["median_ms"] is not None else "N/A"
        )
        p95 = (
            f"{summary['p95_ms']:.3f}"
            if summary["p95_ms"] is not None else "N/A"
        )
        lines.append(
            f"| {summary['mode']} | {summary['expected_group']} "
            f"| {summary['successes']} | {summary['failures']} "
            f"| {summary['success_rate_percent']:.1f}% | {median} | {p95} |"
        )

    classical = summaries[0]
    hybrid = summaries[1]
    if failures == 0 and classical["median_ms"] and hybrid["median_ms"]:
        delta = hybrid["median_ms"] - classical["median_ms"]
        overhead = delta / classical["median_ms"] * 100
        lines += [
            "",
            f"- Hybrid-minus-classical median difference: `{delta:.3f} ms`.",
            f"- Relative median difference: `{overhead:.2f}%`.",
            "- This is an observed local connection-time difference, not a universal performance claim.",
        ]
    else:
        lines += [
            "",
            "**Comparison not accepted:** at least one sample failed validation.",
            "Inspect the raw CSV errors and rerun after fixing the cause.",
        ]

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[INFO] Raw samples: {raw_path}")
    print(f"[INFO] Summary CSV: {summary_path}")
    print(f"[INFO] Environment: {metadata_path}")
    print(f"[INFO] Report: {report_path}")
    if failures:
        print(f"[FAIL] {failures} measured samples failed validation.")
        return 1
    print("[PASS] All measured handshakes completed and passed group-evidence checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
