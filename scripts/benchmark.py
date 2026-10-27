"""Run the Day 5 benchmark and save only non-sensitive results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.benchmark import (  # noqa: E402
    DEFAULT_MEASURED_ITERATIONS,
    DEFAULT_WARMUP_ITERATIONS,
    run_benchmarks,
    write_benchmark_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the small, explicit command-line interface."""

    parser = argparse.ArgumentParser(
        description="Benchmark the project's classical, ML-KEM, and hybrid flows."
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=DEFAULT_WARMUP_ITERATIONS,
        help=f"warm-up iterations per operation (default: {DEFAULT_WARMUP_ITERATIONS})",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_MEASURED_ITERATIONS,
        help=(
            "measured iterations per operation "
            f"(default: {DEFAULT_MEASURED_ITERATIONS})"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "results",
        help="directory for CSV and JSON output",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=PROJECT_ROOT / "docs" / "benchmark_report.md",
        help="path for the measured Markdown report",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace existing benchmark artifacts instead of preserving them",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute all benchmark measurements once."""

    args = build_parser().parse_args(argv)
    try:
        run = run_benchmarks(args.warmup, args.iterations)
        paths = write_benchmark_outputs(
            run,
            args.output_dir,
            args.report_path,
            overwrite=args.overwrite,
        )
    except (FileExistsError, OSError, RuntimeError, ValueError) as error:
        print(f"[FAIL] Benchmark did not complete: {error}", file=sys.stderr)
        return 1

    print(
        "[PASS] Measured "
        f"{len(run.samples)} timing samples across {len(run.summaries)} operations."
    )
    print(f"[PASS] Raw timings: {paths['raw']}")
    print(f"[PASS] Summary statistics: {paths['summary']}")
    print(f"[PASS] Environment metadata: {paths['environment']}")
    print(f"[PASS] Benchmark report: {paths['report']}")
    print("Run scripts/plot_benchmarks.py to create charts from the summary CSV.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
