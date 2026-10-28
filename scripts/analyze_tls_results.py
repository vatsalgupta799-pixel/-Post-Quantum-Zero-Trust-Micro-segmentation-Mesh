"""Analyze and compare classical vs hybrid TLS benchmark results.

This script reads raw CSV files produced by benchmark_tls.py and generates:
- Summary statistics (p50, p95, p99, mean, stddev, min, max)
- Comparative analysis with absolute and relative overhead
- Latency distribution charts (CDF, box plot, percentile comparison)
- A combined summary CSV

Usage:
    python scripts/analyze_tls_results.py \
        --classical-csv results/week2/classical-full/raw.csv \
        --hybrid-csv results/week2/hybrid-full/raw.csv \
        --output-dir results/week2/comparison
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Percentile (same algorithm as Day 5 and benchmark_tls.py)
# ---------------------------------------------------------------------------

def percentile_linear(values: Sequence[float], p: float) -> float:
    """Linearly interpolated percentile."""
    if not values:
        raise ValueError("empty sequence for percentile calculation")
    if not 0 <= p <= 100:
        raise ValueError(f"percentile must be 0–100, got {p}")
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


def relative_overhead(
    classical_ms: float | None,
    hybrid_ms: float | None,
) -> tuple[float | None, float | None]:
    """Compute (abs_diff_ms, relative_pct). Returns None if invalid."""
    if classical_ms is None or hybrid_ms is None:
        return None, None
    diff = hybrid_ms - classical_ms
    if classical_ms > 0 and math.isfinite(classical_ms):
        return diff, (diff / classical_ms) * 100
    return diff, None


# ---------------------------------------------------------------------------
# CSV reading and validation
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "mode",
    "attempt",
    "success",
    "latency_ms",
    "tls_version",
    "negotiated_group",
    "certificate_verified",
    "session_reused",
}

def read_raw_csv(path: Path) -> list[dict[str, str]]:
    """Read a benchmark raw CSV and validate its schema."""
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Empty CSV file: {path}")

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"CSV {path} is missing required columns: {missing}"
            )
        rows = list(reader)

    if not rows:
        raise ValueError(f"CSV {path} contains headers but no data rows")

    return rows


def extract_latencies(rows: list[dict[str, str]], expected_mode: str) -> tuple[list[float], int, int]:
    """Extract successful latencies and count successes/failures.

    Returns: (successful_latencies_ms, success_count, fail_count)
    """
    successful: list[float] = []
    fail_count = 0

    for row in rows:
        mode = row.get("mode", "")
        if expected_mode and mode != expected_mode:
            # Mixed modes in one file — warn but skip mismatched rows
            continue

        success_str = row.get("success", "False")
        is_success = success_str.strip().lower() in ("true", "1", "yes")

        if is_success:
            try:
                latency = float(row["latency_ms"])
                successful.append(latency)
            except (ValueError, KeyError):
                fail_count += 1
        else:
            fail_count += 1

    return successful, len(successful), fail_count


def validate_verified_samples(
    rows: list[dict[str, str]], expected_mode: str, expected_group: str
) -> None:
    """Reject a comparison input that lacks direct per-sample TLS evidence."""
    successful_rows = [
        row for row in rows
        if row.get("mode") == expected_mode
        and row.get("success", "").strip().lower() in ("true", "1", "yes")
    ]
    if not successful_rows:
        return

    for row in successful_rows:
        actual_group = row.get("negotiated_group", "").strip().rstrip(",")
        certificate_verified = row.get("certificate_verified", "").strip().lower()
        if row.get("tls_version") != "TLSv1.3":
            raise ValueError(
                f"{expected_mode} row {row.get('attempt')} is not TLSv1.3"
            )
        if actual_group.lower() != expected_group.lower():
            raise ValueError(
                f"{expected_mode} row {row.get('attempt')} lacks a directly verified "
                f"{expected_group} group (observed {actual_group!r})"
            )
        if certificate_verified not in ("true", "1", "yes"):
            raise ValueError(
                f"{expected_mode} row {row.get('attempt')} lacks certificate verification"
            )
        if row.get("session_reused", "").strip().lower() not in ("false", "0", "no"):
            raise ValueError(f"{expected_mode} row {row.get('attempt')} lacks a fresh session")


# ---------------------------------------------------------------------------
# Comparison analysis
# ---------------------------------------------------------------------------

def build_comparison(
    classical_stats: dict,
    hybrid_stats: dict,
) -> dict:
    """Build a comparison dictionary with absolute and relative differences."""
    comparison = {}

    for metric in ("p50_ms", "p95_ms", "p99_ms", "mean_ms"):
        c_val = classical_stats.get(metric)
        h_val = hybrid_stats.get(metric)
        abs_diff, rel_pct = relative_overhead(c_val, h_val)

        label = metric.replace("_ms", "")
        comparison[f"{label}_classical_ms"] = c_val
        comparison[f"{label}_hybrid_ms"] = h_val
        comparison[f"{label}_abs_diff_ms"] = abs_diff
        comparison[f"{label}_rel_overhead_pct"] = rel_pct

    # Success rate comparison
    c_total = classical_stats.get("count", 0)
    h_total = hybrid_stats.get("count", 0)
    comparison["classical_success_count"] = c_total
    comparison["hybrid_success_count"] = h_total

    return comparison


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------

def generate_charts(
    classical_latencies: list[float],
    hybrid_latencies: list[float],
    classical_stats: dict,
    hybrid_stats: dict,
    output_dir: Path,
) -> list[Path]:
    """Generate comparison charts. Returns list of created file paths."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("[WARN] matplotlib not available. Skipping chart generation.")
        return []

    chart_paths: list[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    # Color scheme
    classical_color = "#2196F3"
    hybrid_color = "#FF5722"

    # --- Chart 1: Percentile Comparison Bar Chart ---
    fig, ax = plt.subplots(figsize=(10, 6))
    percentiles = ["p50", "p95", "p99", "mean"]
    c_values = [
        classical_stats.get("p50_ms", 0) or 0,
        classical_stats.get("p95_ms", 0) or 0,
        classical_stats.get("p99_ms", 0) or 0,
        classical_stats.get("mean_ms", 0) or 0,
    ]
    h_values = [
        hybrid_stats.get("p50_ms", 0) or 0,
        hybrid_stats.get("p95_ms", 0) or 0,
        hybrid_stats.get("p99_ms", 0) or 0,
        hybrid_stats.get("mean_ms", 0) or 0,
    ]

    x = range(len(percentiles))
    width = 0.35
    bars1 = ax.bar([i - width / 2 for i in x], c_values, width,
                   label="Classical (X25519)", color=classical_color, alpha=0.85)
    bars2 = ax.bar([i + width / 2 for i in x], h_values, width,
                   label="Hybrid (X25519MLKEM768)", color=hybrid_color, alpha=0.85)

    ax.set_xlabel("Statistic")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("TLS Connection-Establishment Latency: Classical vs Hybrid")
    ax.set_xticks(list(x))
    ax.set_xticklabels(percentiles)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax.annotate(
                f"{height:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=8,
            )
    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax.annotate(
                f"{height:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=8,
            )

    fig.tight_layout()
    path1 = output_dir / "percentile_comparison.png"
    fig.savefig(path1, dpi=150)
    plt.close(fig)
    chart_paths.append(path1)

    # --- Chart 2: Empirical CDF ---
    if classical_latencies and hybrid_latencies:
        fig, ax = plt.subplots(figsize=(10, 6))

        for label, latencies, color in [
            ("Classical (X25519)", classical_latencies, classical_color),
            ("Hybrid (X25519MLKEM768)", hybrid_latencies, hybrid_color),
        ]:
            sorted_lat = sorted(latencies)
            n = len(sorted_lat)
            cdf = [(i + 1) / n for i in range(n)]
            ax.plot(sorted_lat, cdf, label=label, color=color, linewidth=1.5)

        ax.set_xlabel("Latency (ms)")
        ax.set_ylabel("Cumulative Probability")
        ax.set_title("Empirical CDF: TLS Connection-Establishment Latency")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()

        path2 = output_dir / "latency_cdf.png"
        fig.savefig(path2, dpi=150)
        plt.close(fig)
        chart_paths.append(path2)

    # --- Chart 3: Box Plot ---
    if classical_latencies and hybrid_latencies:
        fig, ax = plt.subplots(figsize=(8, 6))

        bp = ax.boxplot(
            [classical_latencies, hybrid_latencies],
            tick_labels=["Classical\n(X25519)", "Hybrid\n(X25519MLKEM768)"],
            patch_artist=True,
            widths=0.5,
        )
        bp["boxes"][0].set_facecolor(classical_color)
        bp["boxes"][0].set_alpha(0.6)
        bp["boxes"][1].set_facecolor(hybrid_color)
        bp["boxes"][1].set_alpha(0.6)

        ax.set_ylabel("Latency (ms)")
        ax.set_title("TLS Connection-Establishment Latency Distribution")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()

        path3 = output_dir / "latency_boxplot.png"
        fig.savefig(path3, dpi=150)
        plt.close(fig)
        chart_paths.append(path3)

    return chart_paths


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    classical_stats: dict,
    hybrid_stats: dict,
    comparison: dict,
    classical_meta: dict | None,
    hybrid_meta: dict | None,
    classical_total: int,
    hybrid_total: int,
    classical_failures: int,
    hybrid_failures: int,
    chart_paths: list[Path],
    output_dir: Path,
) -> Path:
    """Generate a markdown comparison report."""

    def _fmt(val: Any) -> str:
        if val is None:
            return "N/A"
        if isinstance(val, float):
            return f"{val:.4f}"
        return str(val)

    lines: list[str] = []
    lines.append("# Week 2 TLS Benchmark — Comparative Analysis Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    p50_diff = comparison.get("p50_abs_diff_ms")
    p50_pct = comparison.get("p50_rel_overhead_pct")
    if p50_diff is not None and p50_pct is not None:
        direction = "higher" if p50_diff > 0 else "lower"
        lines.append(
            f"Hybrid TLS (X25519MLKEM768) showed a median (p50) latency that "
            f"was {abs(p50_diff):.4f} ms {direction} than classical TLS (X25519), "
            f"representing a {abs(p50_pct):.2f}% {'overhead' if p50_diff > 0 else 'improvement'}."
        )
    else:
        lines.append("Insufficient data for a comparative summary.")
    lines.append("")

    # Environment
    lines.append("## Experimental Setup")
    lines.append("")
    for label, meta in [("Classical", classical_meta), ("Hybrid", hybrid_meta)]:
        if meta:
            lines.append(f"### {label} Run")
            lines.append(f"- Run ID: {meta.get('run_id', 'N/A')}")
            lines.append(f"- Target: {meta.get('host')}:{meta.get('port')}")
            lines.append(f"- Expected group: {meta.get('expected_group')}")
            lines.append(f"- Python: {meta.get('python_version', 'N/A')}")
            lines.append(f"- Python OpenSSL backend: {meta.get('openssl_backend', 'N/A')}")
            lines.append(f"- OpenSSL client: {meta.get('openssl_client_version', 'not recorded')}")
            lines.append(f"- OS: {meta.get('os', 'N/A')}")
            lines.append(f"- Warmup: {meta.get('warmup_connections', 'N/A')}")
            lines.append(f"- Measured: {meta.get('measured_connections', 'N/A')}")
            lines.append(f"- Timeout: {meta.get('timeout_seconds', 'N/A')}s")
            lines.append(f"- Timing: {meta.get('timing_description', 'N/A')}")
            lines.append("")

    # Results table
    lines.append("## Results")
    lines.append("")
    lines.append("| Metric | Classical (X25519) | Hybrid (X25519MLKEM768) |")
    lines.append("| --- | --- | --- |")
    lines.append(f"| Total attempts | {classical_total + classical_failures} | {hybrid_total + hybrid_failures} |")
    lines.append(f"| Successful | {classical_total} | {hybrid_total} |")
    lines.append(f"| Failed | {classical_failures} | {hybrid_failures} |")

    c_sr = classical_total / (classical_total + classical_failures) if (classical_total + classical_failures) > 0 else 0
    h_sr = hybrid_total / (hybrid_total + hybrid_failures) if (hybrid_total + hybrid_failures) > 0 else 0
    lines.append(f"| Success rate | {c_sr:.1%} | {h_sr:.1%} |")

    for metric, label in [
        ("p50_ms", "p50 latency (ms)"),
        ("p95_ms", "p95 latency (ms)"),
        ("p99_ms", "p99 latency (ms)"),
        ("mean_ms", "Mean latency (ms)"),
        ("stddev_ms", "Std deviation (ms)"),
        ("min_ms", "Min latency (ms)"),
        ("max_ms", "Max latency (ms)"),
    ]:
        lines.append(
            f"| {label} | {_fmt(classical_stats.get(metric))} "
            f"| {_fmt(hybrid_stats.get(metric))} |"
        )
    lines.append("")

    # Comparative analysis
    lines.append("## Comparative Analysis")
    lines.append("")
    lines.append("| Percentile | Abs. Difference (ms) | Relative Overhead (%) |")
    lines.append("| --- | --- | --- |")
    for label in ("p50", "p95", "p99", "mean"):
        abs_d = comparison.get(f"{label}_abs_diff_ms")
        rel_p = comparison.get(f"{label}_rel_overhead_pct")
        lines.append(f"| {label} | {_fmt(abs_d)} | {_fmt(rel_p)} |")
    lines.append("")
    lines.append(
        "Relative overhead (%) = ((hybrid - classical) / classical) × 100. "
        "Positive values indicate hybrid is slower."
    )
    lines.append("")

    # Charts
    if chart_paths:
        lines.append("## Charts")
        lines.append("")
        for cp in chart_paths:
            lines.append(f"![{cp.stem}]({cp.name})")
            lines.append("")

    # Limitations
    lines.append("## Limitations")
    lines.append("")
    lines.append("- Each accepted input row has OpenSSL-reported TLS 1.3, certificate, and named-group evidence.")
    lines.append("- Timing includes OpenSSL client startup and TCP setup (connection-establishment latency, not pure handshake).")
    lines.append("- Results apply only to the specific endpoint, hardware, and software versions tested.")
    lines.append("- Loopback connections do not measure realistic network conditions.")
    lines.append("- No packet capture or handshake-size data was collected.")
    lines.append("")

    # Reproduction
    lines.append("## Reproduction Instructions")
    lines.append("")
    lines.append("```powershell")
    lines.append("$python = python")
    lines.append("& $python scripts/benchmark_tls.py --mode classical --host HOST --port PORT --ca-file CA --openssl-path /path/to/openssl --warmup 100 --iterations 1000 --output-dir results/week2/classical-verified")
    lines.append("& $python scripts/benchmark_tls.py --mode hybrid --host HOST --port PORT --ca-file CA --openssl-path /path/to/openssl --warmup 100 --iterations 1000 --output-dir results/week2/hybrid-verified")
    lines.append("& $python scripts/analyze_tls_results.py --classical-csv results/week2/classical-full/raw.csv --hybrid-csv results/week2/hybrid-full/raw.csv --output-dir results/week2/comparison")
    lines.append("```")
    lines.append("")

    report_path = output_dir / "comparison_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze and compare classical vs hybrid TLS benchmark results. "
            "Reads raw CSV files from benchmark_tls.py."
        ),
    )
    parser.add_argument(
        "--classical-csv",
        type=Path,
        required=True,
        help="Path to the classical benchmark raw.csv",
    )
    parser.add_argument(
        "--hybrid-csv",
        type=Path,
        required=True,
        help="Path to the hybrid benchmark raw.csv",
    )
    parser.add_argument(
        "--classical-metadata",
        type=Path,
        default=None,
        help="Path to the classical metadata.json (optional)",
    )
    parser.add_argument(
        "--hybrid-metadata",
        type=Path,
        default=None,
        help="Path to the hybrid metadata.json (optional)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for analysis output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print("[INFO] Reading classical results...")
    try:
        classical_rows = read_raw_csv(args.classical_csv)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    print("[INFO] Reading hybrid results...")
    try:
        hybrid_rows = read_raw_csv(args.hybrid_csv)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    try:
        validate_verified_samples(classical_rows, "classical", "X25519")
        validate_verified_samples(hybrid_rows, "hybrid", "X25519MLKEM768")
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    # Extract latencies
    c_lat, c_success, c_fail = extract_latencies(classical_rows, "classical")
    h_lat, h_success, h_fail = extract_latencies(hybrid_rows, "hybrid")

    print(f"[INFO] Classical: {c_success} successful, {c_fail} failed")
    print(f"[INFO] Hybrid:    {h_success} successful, {h_fail} failed")

    if c_success == 0:
        print("[FAIL] No successful classical measurements.", file=sys.stderr)
        return 1
    if h_success == 0:
        print("[FAIL] No successful hybrid measurements.", file=sys.stderr)
        return 1

    # Compute statistics
    c_stats = compute_statistics(c_lat)
    h_stats = compute_statistics(h_lat)

    # Build comparison
    comparison = build_comparison(c_stats, h_stats)

    # Load metadata if available
    c_meta = None
    h_meta = None
    if args.classical_metadata and args.classical_metadata.exists():
        c_meta = json.loads(args.classical_metadata.read_text(encoding="utf-8"))
    elif (args.classical_csv.parent / "metadata.json").exists():
        c_meta = json.loads(
            (args.classical_csv.parent / "metadata.json").read_text(encoding="utf-8")
        )
    if args.hybrid_metadata and args.hybrid_metadata.exists():
        h_meta = json.loads(args.hybrid_metadata.read_text(encoding="utf-8"))
    elif (args.hybrid_csv.parent / "metadata.json").exists():
        h_meta = json.loads(
            (args.hybrid_csv.parent / "metadata.json").read_text(encoding="utf-8")
        )

    # Never silently replace an earlier analysis.
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        print(f"[FAIL] Output directory is not empty: {args.output_dir}", file=sys.stderr)
        return 1

    # Generate charts
    args.output_dir.mkdir(parents=True, exist_ok=True)
    chart_paths = generate_charts(c_lat, h_lat, c_stats, h_stats, args.output_dir)

    # Save combined summary CSV
    summary_csv_path = args.output_dir / "combined_summary.csv"
    with summary_csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "mode", "count", "mean_ms", "stddev_ms", "min_ms", "max_ms",
            "p50_ms", "p95_ms", "p99_ms",
        ])
        writer.writeheader()
        writer.writerow({"mode": "classical", **{k: f"{v:.6f}" if isinstance(v, float) else v for k, v in c_stats.items()}})
        writer.writerow({"mode": "hybrid", **{k: f"{v:.6f}" if isinstance(v, float) else v for k, v in h_stats.items()}})

    # Save comparison JSON
    comparison_path = args.output_dir / "comparison.json"
    comparison_path.write_text(
        json.dumps(comparison, indent=2, default=str),
        encoding="utf-8",
    )

    # Generate report
    report_path = generate_report(
        c_stats, h_stats, comparison,
        c_meta, h_meta,
        c_success, h_success,
        c_fail, h_fail,
        chart_paths,
        args.output_dir,
    )

    print(f"\n[DONE] Analysis complete.")
    print(f"  Summary CSV:  {summary_csv_path}")
    print(f"  Comparison:   {comparison_path}")
    print(f"  Report:       {report_path}")
    for cp in chart_paths:
        print(f"  Chart:        {cp}")

    # Print key results
    print(f"\n{'=' * 60}")
    print("KEY RESULTS")
    print(f"{'=' * 60}")
    for metric in ("p50", "p95", "p99"):
        c_val = comparison.get(f"{metric}_classical_ms")
        h_val = comparison.get(f"{metric}_hybrid_ms")
        diff = comparison.get(f"{metric}_abs_diff_ms")
        pct = comparison.get(f"{metric}_rel_overhead_pct")
        print(
            f"  {metric}: Classical={c_val:.4f}ms, Hybrid={h_val:.4f}ms, "
            f"Diff={diff:+.4f}ms ({pct:+.2f}%)" if all(
                v is not None for v in [c_val, h_val, diff, pct]
            ) else f"  {metric}: insufficient data"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
