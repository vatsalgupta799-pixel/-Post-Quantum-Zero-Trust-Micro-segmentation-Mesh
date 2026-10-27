"""Create Day 5 charts from an actual benchmark summary CSV."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".tmp" / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ALGORITHM_ORDER = (
    "classical_x25519_hkdf",
    "mlkem_768",
    "hybrid_x25519_mlkem_768",
)
DISPLAY_NAMES = {
    "classical_x25519_hkdf": "X25519 + HKDF",
    "mlkem_768": "ML-KEM-768",
    "hybrid_x25519_mlkem_768": "Hybrid X25519 + ML-KEM-768",
}


def load_complete_exchange_rows(summary_path: Path) -> list[dict[str, str]]:
    """Load only complete-exchange rows needed by both comparisons."""

    with summary_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "algorithm",
            "operation",
            "median_ms",
            "stddev_ms",
            "total_payload_bytes",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("summary CSV does not contain the required columns")
        rows = [
            row
            for row in reader
            if row["operation"] == "complete_exchange"
        ]

    by_algorithm = {row["algorithm"]: row for row in rows}
    missing = [algorithm for algorithm in ALGORITHM_ORDER if algorithm not in by_algorithm]
    if missing:
        raise ValueError(
            "summary CSV is missing complete-exchange rows for: " + ", ".join(missing)
        )
    return [by_algorithm[algorithm] for algorithm in ALGORITHM_ORDER]


def _ensure_chart_paths(paths: tuple[Path, ...], overwrite: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        names = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"refusing to overwrite existing charts: {names}; use --overwrite"
        )
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def create_charts(
    summary_path: Path,
    output_dir: Path,
    *,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Create complete-latency and payload charts from the summary CSV."""

    rows = load_complete_exchange_rows(summary_path)
    latency_path = output_dir / "latency_comparison.png"
    payload_path = output_dir / "payload_size_comparison.png"
    _ensure_chart_paths((latency_path, payload_path), overwrite)

    labels = [DISPLAY_NAMES[row["algorithm"]] for row in rows]
    medians = [float(row["median_ms"]) for row in rows]
    standard_deviations = [float(row["stddev_ms"]) for row in rows]
    payloads = [int(row["total_payload_bytes"]) for row in rows]
    positions = list(range(len(labels)))
    colors = ["#4C78A8", "#F58518", "#54A24B"]

    figure, axis = plt.subplots(figsize=(9, 5))
    bars = axis.bar(
        positions,
        medians,
        yerr=standard_deviations,
        capsize=5,
        color=colors,
        label="Median latency with sample standard deviation",
    )
    axis.set_xticks(positions, labels)
    axis.set_ylabel("Latency (ms)")
    axis.set_title("Complete in-process key-establishment latency")
    axis.legend()
    axis.grid(axis="y", alpha=0.25)
    label_offset = max(medians) * 0.015
    for bar, value, standard_deviation in zip(bars, medians, standard_deviations):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + standard_deviation + label_offset,
            f"{value:.4f} ms",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    figure.tight_layout()
    figure.savefig(latency_path, dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 5))
    bars = axis.bar(
        positions,
        payloads,
        color=colors,
        label="Cryptographic payload",
    )
    axis.set_xticks(positions, labels)
    axis.set_ylabel("Bytes")
    axis.set_title("Simulated cryptographic payload size, not network traffic")
    axis.legend()
    axis.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, payloads):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value} bytes",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    figure.tight_layout()
    figure.savefig(payload_path, dpi=180)
    plt.close(figure)
    return latency_path, payload_path


def build_parser() -> argparse.ArgumentParser:
    """Create the chart CLI."""

    parser = argparse.ArgumentParser(
        description="Create charts from benchmark_summary.csv."
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=PROJECT_ROOT / "results" / "benchmark_summary.csv",
        help="summary CSV created by scripts/benchmark.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "results",
        help="directory for PNG charts",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace existing chart files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Load real data and write both figures."""

    args = build_parser().parse_args(argv)
    try:
        latency_path, payload_path = create_charts(
            args.summary_path,
            args.output_dir,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        print(f"[FAIL] Charts were not generated: {error}", file=sys.stderr)
        return 1

    print(f"[PASS] Latency chart: {latency_path}")
    print(f"[PASS] Payload chart: {payload_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
