"""Exploratory handshake-only benchmark using openssl_handshake_probe.

Each observation uses a new TLS context and TCP connection. Four balanced
blocks can start with either group; failed attempts are preserved, not retried.
This diagnostic does not implement client-certificate authentication.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
import platform
from pathlib import Path
import sys
import uuid

from openssl_handshake_probe import ProbeError, probe
from analyze_tls_results import compute_statistics, build_comparison

ORDERINGS = {
    "hybrid-first": ("hybrid", "classical", "classical", "hybrid"),
    "classical-first": ("classical", "hybrid", "hybrid", "classical"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--server-name", required=True)
    parser.add_argument("--ca-file", type=Path, required=True)
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--per-block", type=int, default=25)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--order", choices=tuple(ORDERINGS), default="hybrid-first",
                        help="First group in the balanced four-block sequence")
    args = parser.parse_args()
    if args.per_block < 1 or args.warmup < 0 or not math.isfinite(args.timeout) or args.timeout <= 0 or not 1 <= args.port <= 65535:
        parser.error("invalid block size, warmup, port or timeout")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    run_id = uuid.uuid4().hex[:12]
    metadata = {"run_id": run_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "host": args.host, "port": args.port, "server_name": args.server_name,
                "ca_file": str(args.ca_file), "dll": str(args.dll),
                "platform": platform.platform(), "python": sys.version,
                "ordering": list(ORDERINGS[args.order]),
                "measured_per_block": args.per_block, "warmup_per_block": args.warmup,
                "timeout_seconds": args.timeout, "concurrency": 1,
                "timing": "perf_counter_ns from immediately before the first SSL_connect call until successful completion; TCP setup excluded, certificate validation included",
                "session_policy": "new SSL context and TCP socket for each observation; session reuse checked",
                "server_provenance": "not supplied; record server build, configuration, identity and network path separately",
                "authentication": "server certificate and DNS hostname checked; no client certificate supported",
                "status": "running", "warmup_outcomes": []}
    meta_path = args.output_dir / "metadata.json"
    def save_meta():
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    save_meta()
    samples = {"classical": [], "hybrid": []}
    failed = False
    fields = ["run_id", "timestamp_utc", "block", "mode", "attempt", "success", "handshake_ms", "tls_version", "negotiated_group", "certificate_verified", "session_reused", "error"]
    with (args.output_dir / "raw.csv").open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for block, mode in enumerate(metadata["ordering"], 1):
            for attempt in range(-args.warmup, args.per_block + 1):
                if attempt == 0:
                    continue
                row = {"run_id": run_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                       "block": block, "mode": mode, "attempt": attempt, "success": False}
                try:
                    result = probe(args.host, args.port, args.server_name, args.ca_file,
                                   mode, args.timeout, args.dll)
                    row.update(result)
                    row["success"] = True
                except (ProbeError, OSError, ValueError) as exc:
                    row["error"] = str(exc)
                    failed = True
                if attempt < 0:
                    metadata["warmup_outcomes"].append(row)
                    save_meta()
                    if failed:
                        break
                else:
                    writer.writerow(row)
                    output.flush()
                    if row["success"]:
                        samples[mode].append(row["handshake_ms"])
                    if failed:
                        break
            if failed:
                break
    if failed:
        metadata["status"] = "failed or incomplete; inspect raw CSV and warmup outcomes"
        save_meta()
        print(metadata["status"], file=sys.stderr)
        return 1
    stats = {mode: compute_statistics(values) for mode, values in samples.items()}
    comparison = build_comparison(stats["classical"], stats["hybrid"])
    (args.output_dir / "summary.json").write_text(json.dumps({"statistics": stats, "comparison": comparison}, indent=2), encoding="utf-8")
    metadata["status"] = "complete"
    save_meta()
    print(json.dumps({"run_id": run_id, "statistics": stats, "comparison": comparison}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
