"""Reproducible in-process benchmarks for the three key-establishment flows.

The helpers in this module deliberately use the project implementations rather
than reproducing any cryptographic operation. They record only timings and
public-size metadata; private keys and shared secrets are never serialized.
"""

from __future__ import annotations

import csv
import json
import math
import os
import platform
import secrets
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable, Sequence

import cryptography
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.classical_ecdh import (
    DEFAULT_HKDF_INFO,
    derive_session_key,
    derive_shared_secret,
    generate_key_pair as generate_x25519_key_pair,
)
from src.hybrid_exchange import derive_hybrid_session_key, perform_hybrid_exchange
from src.pqc_mlkem import (
    decapsulate_shared_secret,
    encapsulate_shared_secret,
    generate_key_pair as generate_mlkem_key_pair,
)


DEFAULT_WARMUP_ITERATIONS = 20
DEFAULT_MEASURED_ITERATIONS = 500

CLASSICAL_ALGORITHM = "classical_x25519_hkdf"
MLKEM_ALGORITHM = "mlkem_768"
HYBRID_ALGORITHM = "hybrid_x25519_mlkem_768"

DISPLAY_NAMES = {
    CLASSICAL_ALGORITHM: "X25519 + HKDF",
    MLKEM_ALGORITHM: "ML-KEM-768",
    HYBRID_ALGORITHM: "Hybrid X25519 + ML-KEM-768",
}

RAW_CSV_COLUMNS = (
    "algorithm",
    "operation",
    "iteration",
    "latency_ns",
    "latency_us",
    "latency_ms",
)
PAYLOAD_CSV_COLUMNS = (
    "x25519_public_key_bytes",
    "x25519_public_key_count",
    "mlkem_public_key_bytes",
    "mlkem_public_key_count",
    "mlkem_ciphertext_bytes",
    "mlkem_ciphertext_count",
    "total_payload_bytes",
)
SUMMARY_CSV_COLUMNS = (
    "algorithm",
    "operation",
    "iterations",
    "mean_ms",
    "median_ms",
    "stddev_ms",
    "min_ms",
    "max_ms",
    "p95_ms",
    *PAYLOAD_CSV_COLUMNS,
)


@dataclass(frozen=True)
class TimingSample:
    """One timing observation from an actual cryptographic operation."""

    algorithm: str
    operation: str
    iteration: int
    latency_ns: int

    def csv_row(self) -> dict[str, str | int]:
        """Return a stable CSV representation without sensitive material."""

        return {
            "algorithm": self.algorithm,
            "operation": self.operation,
            "iteration": self.iteration,
            "latency_ns": self.latency_ns,
            "latency_us": f"{self.latency_ns / 1_000:.6f}",
            "latency_ms": f"{self.latency_ns / 1_000_000:.6f}",
        }


@dataclass(frozen=True)
class LatencyStatistics:
    """Latency statistics in milliseconds using sample standard deviation."""

    iterations: int
    mean_ms: float
    median_ms: float
    stddev_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float


@dataclass(frozen=True)
class PayloadSize:
    """Public cryptographic values that a simulated handshake would transmit."""

    algorithm: str
    x25519_public_key_bytes: int
    x25519_public_key_count: int
    mlkem_public_key_bytes: int
    mlkem_public_key_count: int
    mlkem_ciphertext_bytes: int
    mlkem_ciphertext_count: int
    total_payload_bytes: int

    def csv_values(self) -> dict[str, int]:
        """Return payload fields matching the summary CSV schema."""

        return {
            "x25519_public_key_bytes": self.x25519_public_key_bytes,
            "x25519_public_key_count": self.x25519_public_key_count,
            "mlkem_public_key_bytes": self.mlkem_public_key_bytes,
            "mlkem_public_key_count": self.mlkem_public_key_count,
            "mlkem_ciphertext_bytes": self.mlkem_ciphertext_bytes,
            "mlkem_ciphertext_count": self.mlkem_ciphertext_count,
            "total_payload_bytes": self.total_payload_bytes,
        }

    def json_values(self) -> dict[str, int | str]:
        """Return a JSON-safe public-size record."""

        return {"algorithm": self.algorithm, **self.csv_values()}


@dataclass(frozen=True)
class BenchmarkSummary:
    """One operation's calculated summary and optional exchange payload."""

    algorithm: str
    operation: str
    statistics: LatencyStatistics
    payload: PayloadSize | None = None

    def csv_row(self) -> dict[str, str | int]:
        """Return a stable summary CSV representation."""

        values: dict[str, str | int] = {
            "algorithm": self.algorithm,
            "operation": self.operation,
            "iterations": self.statistics.iterations,
            "mean_ms": f"{self.statistics.mean_ms:.6f}",
            "median_ms": f"{self.statistics.median_ms:.6f}",
            "stddev_ms": f"{self.statistics.stddev_ms:.6f}",
            "min_ms": f"{self.statistics.min_ms:.6f}",
            "max_ms": f"{self.statistics.max_ms:.6f}",
            "p95_ms": f"{self.statistics.p95_ms:.6f}",
        }
        values.update(
            self.payload.csv_values()
            if self.payload is not None
            else {column: "" for column in PAYLOAD_CSV_COLUMNS}
        )
        return values


@dataclass(frozen=True)
class BenchmarkRun:
    """All public artifacts produced by one benchmark execution."""

    samples: tuple[TimingSample, ...]
    summaries: tuple[BenchmarkSummary, ...]
    payloads: tuple[PayloadSize, ...]
    environment: dict[str, Any]


def validate_benchmark_config(warmup: int, iterations: int) -> None:
    """Reject invalid repetition counts before any cryptographic work starts."""

    if isinstance(warmup, bool) or not isinstance(warmup, int) or warmup < 0:
        raise ValueError("warmup must be a non-negative integer")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 1:
        raise ValueError("iterations must be a positive integer")


def _validated_values(values: Sequence[int | float]) -> list[float]:
    if not values:
        raise ValueError("at least one timing value is required")

    converted = [float(value) for value in values]
    if any(not math.isfinite(value) or value < 0 for value in converted):
        raise ValueError("timing values must be finite and non-negative")
    return converted


def percentile_linear(values: Sequence[int | float], percentile: float) -> float:
    """Return a percentile with NumPy-compatible linear interpolation."""

    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be between 0 and 100")

    ordered = sorted(_validated_values(values))
    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * (percentile / 100)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize_latencies(latency_ns: Sequence[int | float]) -> LatencyStatistics:
    """Calculate benchmark statistics after converting nanoseconds to ms."""

    values_ms = [value / 1_000_000 for value in _validated_values(latency_ns)]
    return LatencyStatistics(
        iterations=len(values_ms),
        mean_ms=statistics.mean(values_ms),
        median_ms=statistics.median(values_ms),
        stddev_ms=statistics.stdev(values_ms) if len(values_ms) > 1 else 0.0,
        min_ms=min(values_ms),
        max_ms=max(values_ms),
        p95_ms=percentile_linear(values_ms, 95),
    )


def relative_overhead(
    classical_median_ms: float,
    hybrid_median_ms: float,
) -> tuple[float, float]:
    """Return hybrid-minus-classical latency and percentage overhead."""

    if not math.isfinite(classical_median_ms) or classical_median_ms <= 0:
        raise ValueError("classical median latency must be a positive finite value")
    if not math.isfinite(hybrid_median_ms) or hybrid_median_ms < 0:
        raise ValueError("hybrid median latency must be a non-negative finite value")

    difference_ms = hybrid_median_ms - classical_median_ms
    return difference_ms, (difference_ms / classical_median_ms) * 100


def measure_operation(
    algorithm: str,
    operation_name: str,
    operation: Callable[[], object],
    warmup: int,
    iterations: int,
) -> tuple[TimingSample, ...]:
    """Warm up and time one operation serially with a monotonic high-res clock."""

    validate_benchmark_config(warmup, iterations)
    for _ in range(warmup):
        operation()

    samples: list[TimingSample] = []
    for iteration in range(1, iterations + 1):
        started_at = time.perf_counter_ns()
        operation()
        samples.append(
            TimingSample(
                algorithm=algorithm,
                operation=operation_name,
                iteration=iteration,
                latency_ns=time.perf_counter_ns() - started_at,
            )
        )
    return tuple(samples)


def _verify_implementations() -> None:
    """Perform one correctness check per flow outside all timed sections."""

    private_a, public_a = generate_x25519_key_pair()
    private_b, public_b = generate_x25519_key_pair()
    secret_a = derive_shared_secret(private_a, public_b)
    secret_b = derive_shared_secret(private_b, public_a)
    salt = secrets.token_bytes(16)
    if derive_session_key(secret_a, salt, DEFAULT_HKDF_INFO) != derive_session_key(
        secret_b,
        salt,
        DEFAULT_HKDF_INFO,
    ):
        raise RuntimeError("classical benchmark validation failed")

    mlkem_private, mlkem_public = generate_mlkem_key_pair()
    encapsulation = encapsulate_shared_secret(mlkem_public)
    if encapsulation.shared_secret != decapsulate_shared_secret(
        mlkem_private,
        encapsulation.ciphertext,
    ):
        raise RuntimeError("ML-KEM benchmark validation failed")

    hybrid_result = perform_hybrid_exchange()
    if hybrid_result.session_key_a != hybrid_result.session_key_b:
        raise RuntimeError("hybrid benchmark validation failed")


def _complete_classical_exchange() -> None:
    """Run a full local classical exchange without reporting the result."""

    private_a, public_a = generate_x25519_key_pair()
    private_b, public_b = generate_x25519_key_pair()
    secret_a = derive_shared_secret(private_a, public_b)
    secret_b = derive_shared_secret(private_b, public_a)
    salt = secrets.token_bytes(16)
    derive_session_key(secret_a, salt, DEFAULT_HKDF_INFO)
    derive_session_key(secret_b, salt, DEFAULT_HKDF_INFO)


def _complete_mlkem_exchange() -> None:
    """Run fresh ML-KEM key generation, encapsulation, and decapsulation."""

    private_key, public_key = generate_mlkem_key_pair()
    encapsulation = encapsulate_shared_secret(public_key)
    decapsulate_shared_secret(private_key, encapsulation.ciphertext)


def _benchmark_specs() -> tuple[tuple[str, str, Callable[[], object]], ...]:
    """Build actual operation callables with setup deliberately outside timing."""

    x25519_private_a, x25519_public_a = generate_x25519_key_pair()
    x25519_private_b, x25519_public_b = generate_x25519_key_pair()
    x25519_secret = derive_shared_secret(x25519_private_a, x25519_public_b)
    x25519_salt = secrets.token_bytes(16)

    mlkem_private, mlkem_public = generate_mlkem_key_pair()
    mlkem_ciphertext = encapsulate_shared_secret(mlkem_public).ciphertext

    hybrid_x_private_a, hybrid_x_public_a = generate_x25519_key_pair()
    hybrid_x_private_b, hybrid_x_public_b = generate_x25519_key_pair()
    hybrid_mlkem_private, hybrid_mlkem_public = generate_mlkem_key_pair()
    hybrid_seed = perform_hybrid_exchange()

    def hybrid_x25519_operations() -> None:
        derive_shared_secret(hybrid_x_private_a, hybrid_x_public_b)
        derive_shared_secret(hybrid_x_private_b, hybrid_x_public_a)

    def hybrid_mlkem_operations() -> None:
        result = encapsulate_shared_secret(hybrid_mlkem_public)
        decapsulate_shared_secret(hybrid_mlkem_private, result.ciphertext)

    def hybrid_hkdf_combination() -> None:
        derive_hybrid_session_key(
            hybrid_seed.x25519_shared_secret_a,
            hybrid_seed.mlkem_shared_secret_a,
            hybrid_seed.transcript,
        )
        derive_hybrid_session_key(
            hybrid_seed.x25519_shared_secret_b,
            hybrid_seed.mlkem_shared_secret_b,
            hybrid_seed.transcript,
        )

    return (
        (CLASSICAL_ALGORITHM, "x25519_key_generation", generate_x25519_key_pair),
        (
            CLASSICAL_ALGORITHM,
            "x25519_shared_secret_derivation",
            lambda: derive_shared_secret(x25519_private_a, x25519_public_b),
        ),
        (
            CLASSICAL_ALGORITHM,
            "x25519_hkdf_session_key_derivation",
            lambda: derive_session_key(x25519_secret, x25519_salt, DEFAULT_HKDF_INFO),
        ),
        (CLASSICAL_ALGORITHM, "complete_exchange", _complete_classical_exchange),
        (MLKEM_ALGORITHM, "mlkem_768_key_generation", generate_mlkem_key_pair),
        (
            MLKEM_ALGORITHM,
            "mlkem_768_encapsulation",
            lambda: encapsulate_shared_secret(mlkem_public),
        ),
        (
            MLKEM_ALGORITHM,
            "mlkem_768_decapsulation",
            lambda: decapsulate_shared_secret(mlkem_private, mlkem_ciphertext),
        ),
        (MLKEM_ALGORITHM, "complete_exchange", _complete_mlkem_exchange),
        (HYBRID_ALGORITHM, "hybrid_x25519_operations", hybrid_x25519_operations),
        (
            HYBRID_ALGORITHM,
            "hybrid_mlkem_encapsulation_and_decapsulation",
            hybrid_mlkem_operations,
        ),
        (HYBRID_ALGORITHM, "hybrid_hkdf_combination", hybrid_hkdf_combination),
        (HYBRID_ALGORITHM, "complete_exchange", perform_hybrid_exchange),
    )


def measure_payload_sizes() -> tuple[PayloadSize, ...]:
    """Measure serialized public values used by the simulated handshakes."""

    _, x25519_public_a = generate_x25519_key_pair()
    _, x25519_public_b = generate_x25519_key_pair()
    _, mlkem_public = generate_mlkem_key_pair()
    mlkem_encapsulation = encapsulate_shared_secret(mlkem_public)

    x25519_a_size = len(
        x25519_public_a.public_bytes(Encoding.Raw, PublicFormat.Raw)
    )
    x25519_b_size = len(
        x25519_public_b.public_bytes(Encoding.Raw, PublicFormat.Raw)
    )
    mlkem_public_size = len(mlkem_public.public_bytes(Encoding.Raw, PublicFormat.Raw))
    mlkem_ciphertext_size = len(mlkem_encapsulation.ciphertext)

    return (
        PayloadSize(
            algorithm=CLASSICAL_ALGORITHM,
            x25519_public_key_bytes=x25519_a_size,
            x25519_public_key_count=2,
            mlkem_public_key_bytes=0,
            mlkem_public_key_count=0,
            mlkem_ciphertext_bytes=0,
            mlkem_ciphertext_count=0,
            total_payload_bytes=x25519_a_size + x25519_b_size,
        ),
        PayloadSize(
            algorithm=MLKEM_ALGORITHM,
            x25519_public_key_bytes=0,
            x25519_public_key_count=0,
            mlkem_public_key_bytes=mlkem_public_size,
            mlkem_public_key_count=1,
            mlkem_ciphertext_bytes=mlkem_ciphertext_size,
            mlkem_ciphertext_count=1,
            total_payload_bytes=mlkem_public_size + mlkem_ciphertext_size,
        ),
        PayloadSize(
            algorithm=HYBRID_ALGORITHM,
            x25519_public_key_bytes=x25519_a_size,
            x25519_public_key_count=2,
            mlkem_public_key_bytes=mlkem_public_size,
            mlkem_public_key_count=1,
            mlkem_ciphertext_bytes=mlkem_ciphertext_size,
            mlkem_ciphertext_count=1,
            total_payload_bytes=(
                x25519_a_size
                + x25519_b_size
                + mlkem_public_size
                + mlkem_ciphertext_size
            ),
        ),
    )


def build_summaries(
    samples: Sequence[TimingSample],
    payloads: Sequence[PayloadSize],
) -> tuple[BenchmarkSummary, ...]:
    """Group raw samples and attach payload data only to complete exchanges."""

    if not samples:
        raise ValueError("at least one timing sample is required")

    grouped: dict[tuple[str, str], list[int]] = {}
    for sample in samples:
        grouped.setdefault((sample.algorithm, sample.operation), []).append(
            sample.latency_ns
        )
    payload_by_algorithm = {payload.algorithm: payload for payload in payloads}

    return tuple(
        BenchmarkSummary(
            algorithm=algorithm,
            operation=operation,
            statistics=summarize_latencies(latencies),
            payload=(
                payload_by_algorithm.get(algorithm)
                if operation == "complete_exchange"
                else None
            ),
        )
        for (algorithm, operation), latencies in grouped.items()
    )


def _cpu_model() -> str:
    """Return the Windows CPU model when available, with portable fallback."""

    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if value:
                    return str(value).strip()
        except OSError:
            pass
    return platform.processor() or "unavailable"


def _openssl_version() -> str:
    try:
        from cryptography.hazmat.backends.openssl.backend import backend

        return backend.openssl_version_text()
    except Exception:
        return "unavailable"


def collect_environment(
    warmup: int,
    iterations: int,
    payloads: Sequence[PayloadSize],
) -> dict[str, Any]:
    """Collect non-sensitive environment metadata for one benchmark run."""

    validate_benchmark_config(warmup, iterations)
    try:
        matplotlib_version = version("matplotlib")
    except PackageNotFoundError:
        matplotlib_version = "not installed"

    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "operating_system": platform.platform(aliased=True),
        "architecture": platform.machine() or "unavailable",
        "cpu_model": _cpu_model(),
        "logical_cpu_count": os.cpu_count() or "unavailable",
        "python_version": sys.version.split()[0],
        "cryptographic_libraries": {
            "cryptography": cryptography.__version__,
            "mlkem_implementation": (
                "cryptography.hazmat.primitives.asymmetric.mlkem.MLKEM768"
            ),
            "openssl_backend": _openssl_version(),
            "matplotlib": matplotlib_version,
        },
        "benchmark_configuration": {
            "warmup_iterations": warmup,
            "measured_iterations": iterations,
            "timer": "time.perf_counter_ns",
            "measurement_units": {
                "raw_samples": "nanoseconds",
                "summaries": "milliseconds",
            },
            "percentile_method": "linear interpolation at index (n - 1) * p",
        },
        "payload_sizes": [payload.json_values() for payload in payloads],
        "warnings": [
            "Timings include Python wrapper and installed cryptography backend overhead.",
            "Measurements are serial, local, in-process cryptographic timings.",
            "Payloads are cryptographic values for the simulated handshake, not network traffic.",
            "No TLS, Envoy, certificate, Kubernetes, or network latency is measured.",
            "Operating-system scheduling, CPU power policy, and background work can affect results.",
        ],
    }


def run_benchmarks(warmup: int, iterations: int) -> BenchmarkRun:
    """Validate implementations, then collect the configured real samples."""

    validate_benchmark_config(warmup, iterations)
    _verify_implementations()
    payloads = measure_payload_sizes()
    samples: list[TimingSample] = []
    for algorithm, operation_name, operation in _benchmark_specs():
        samples.extend(
            measure_operation(
                algorithm,
                operation_name,
                operation,
                warmup,
                iterations,
            )
        )
    summaries = build_summaries(samples, payloads)
    return BenchmarkRun(
        samples=tuple(samples),
        summaries=summaries,
        payloads=payloads,
        environment=collect_environment(warmup, iterations, payloads),
    )


def _ensure_output_paths(
    output_paths: Sequence[Path],
    overwrite: bool,
) -> None:
    existing = [path for path in output_paths if path.exists()]
    if existing and not overwrite:
        names = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"refusing to overwrite existing benchmark artifacts: {names}; "
            "use --overwrite or choose a different output path"
        )
    for path in output_paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def _complete_exchange_summaries(
    summaries: Sequence[BenchmarkSummary],
) -> dict[str, BenchmarkSummary]:
    complete = {
        summary.algorithm: summary
        for summary in summaries
        if summary.operation == "complete_exchange"
    }
    expected = {CLASSICAL_ALGORITHM, MLKEM_ALGORITHM, HYBRID_ALGORITHM}
    if set(complete) != expected:
        raise ValueError("all three complete-exchange summaries are required")
    return complete


def _format_ms(value: float) -> str:
    return f"{value:.6f}"


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    divider = ["---"] * len(headers)
    table_rows = [headers, divider, *rows]
    return "\n".join("| " + " | ".join(row) + " |" for row in table_rows)


def render_benchmark_report(run: BenchmarkRun) -> str:
    """Render a report whose numerical results come only from this run."""

    complete = _complete_exchange_summaries(run.summaries)
    classical = complete[CLASSICAL_ALGORITHM].statistics
    hybrid = complete[HYBRID_ALGORITHM].statistics
    difference_ms, overhead_percent = relative_overhead(
        classical.median_ms,
        hybrid.median_ms,
    )
    fastest_algorithm, fastest_summary = min(
        complete.items(),
        key=lambda item: item[1].statistics.median_ms,
    )
    slowest_component = max(
        (
            summary
            for summary in run.summaries
            if summary.operation != "complete_exchange"
        ),
        key=lambda summary: summary.statistics.median_ms,
    )

    environment = run.environment
    libraries = environment["cryptographic_libraries"]
    result_rows = [
        [
            DISPLAY_NAMES[summary.algorithm],
            summary.operation,
            _format_ms(summary.statistics.mean_ms),
            _format_ms(summary.statistics.median_ms),
            _format_ms(summary.statistics.stddev_ms),
            _format_ms(summary.statistics.min_ms),
            _format_ms(summary.statistics.max_ms),
            _format_ms(summary.statistics.p95_ms),
        ]
        for summary in run.summaries
    ]
    payload_rows = [
        [
            DISPLAY_NAMES[payload.algorithm],
            (
                f"{payload.x25519_public_key_bytes} x "
                f"{payload.x25519_public_key_count}"
                if payload.x25519_public_key_count
                else "none"
            ),
            (
                f"{payload.mlkem_public_key_bytes} x "
                f"{payload.mlkem_public_key_count}"
                if payload.mlkem_public_key_count
                else "none"
            ),
            (
                f"{payload.mlkem_ciphertext_bytes} x "
                f"{payload.mlkem_ciphertext_count}"
                if payload.mlkem_ciphertext_count
                else "none"
            ),
            str(payload.total_payload_bytes),
        ]
        for payload in run.payloads
    ]

    return "\n".join(
        [
            "# Day 5 Benchmark Report",
            "",
            "## Executive summary",
            "",
            (
                "This report contains actual local measurements collected on "
                f"{environment['timestamp']}."
            ),
            (
                f"{DISPLAY_NAMES[fastest_algorithm]} was the fastest complete "
                f"exchange in this run at a {_format_ms(fastest_summary.statistics.median_ms)} ms median."
            ),
            (
                f"The hybrid complete exchange had a {_format_ms(difference_ms)} ms "
                f"absolute median difference from the classical baseline "
                f"({_format_ms(overhead_percent)}%)."
            ),
            "",
            "## Experimental environment",
            "",
            _markdown_table(
                ["Item", "Observed value"],
                [
                    ["Timestamp", str(environment["timestamp"])],
                    ["Operating system", str(environment["operating_system"])],
                    ["CPU model", str(environment["cpu_model"])],
                    ["Architecture", str(environment["architecture"])],
                    ["Logical CPUs", str(environment["logical_cpu_count"])],
                    ["Python", str(environment["python_version"])],
                    ["cryptography", str(libraries["cryptography"])],
                    ["ML-KEM implementation", str(libraries["mlkem_implementation"])],
                    ["OpenSSL backend", str(libraries["openssl_backend"])],
                    ["Matplotlib", str(libraries["matplotlib"])],
                    [
                        "Warm-up / measured iterations",
                        (
                            f"{environment['benchmark_configuration']['warmup_iterations']} / "
                            f"{environment['benchmark_configuration']['measured_iterations']}"
                        ),
                    ],
                ],
            ),
            "",
            "The cryptography package uses its installed backend; this benchmark records "
            "the exposed OpenSSL backend version but does not identify ML-KEM backend "
            "internals separately.",
            "",
            "## Methodology",
            "",
            "The timer is time.perf_counter_ns. Each benchmark first performs the "
            "documented warm-up count, then records serial samples without console "
            "output. The 95th percentile uses linear interpolation at index "
            "(n - 1) * 0.95, and standard deviation is the sample standard deviation.",
            "",
            "A one-time correctness check for every implementation runs outside timed "
            "sections. Isolated operations use prebuilt valid inputs where appropriate "
            "so they measure the named operation. Complete exchanges create fresh key "
            "material and run the actual project flow: the classical path creates two "
            "X25519 pairs, performs both exchanges, and derives both HKDF keys; ML-KEM "
            "creates a pair, encapsulates, and decapsulates; the hybrid path calls "
            "perform_hybrid_exchange, including its existing transcript and agreement "
            "checks. Individual rows overlap with complete exchanges and must not be "
            "added together.",
            "",
            "## Reproducing safely",
            "",
            "To preserve existing artifacts, write a fresh run to a separate output "
            "directory instead of using --overwrite. For example, run `python "
            "scripts/benchmark.py --warmup 20 --iterations 500 --output-dir "
            "<new-output-dir> --report-path <new-report-path>`, then run `python "
            "scripts/plot_benchmarks.py --summary-path "
            "<new-output-dir>/benchmark_summary.csv --output-dir <new-chart-dir>`.",
            "",
            "## Results",
            "",
            "Latency values are milliseconds.",
            "",
            _markdown_table(
                [
                    "Approach",
                    "Operation",
                    "Mean",
                    "Median",
                    "Std. dev.",
                    "Min",
                    "Max",
                    "P95",
                ],
                result_rows,
            ),
            "",
            "## Cryptographic payload sizes",
            "",
            "These are in-memory simulated cryptographic payloads, not measured network "
            "traffic or total TLS handshake sizes. TLS framing, certificates, signatures, "
            "and protocol metadata are excluded.",
            "",
            _markdown_table(
                [
                    "Approach",
                    "X25519 public key bytes x count",
                    "ML-KEM public key bytes x count",
                    "ML-KEM ciphertext bytes x count",
                    "Total bytes",
                ],
                payload_rows,
            ),
            "",
            "Charts generated from the summary CSV:",
            "",
            "- ../results/latency_comparison.png",
            "- ../results/payload_size_comparison.png",
            "",
            "## Performance interpretation",
            "",
            (
                f"The separately measured operation with the highest median in this run "
                f"was {slowest_component.operation} for "
                f"{DISPLAY_NAMES[slowest_component.algorithm]} at "
                f"{_format_ms(slowest_component.statistics.median_ms)} ms. "
                "That observation identifies an isolated cost, not an additive "
                "breakdown of the complete-exchange measurement."
            ),
            (
                f"Compared with X25519 + HKDF, the observed hybrid complete-exchange "
                f"median changed by {_format_ms(difference_ms)} ms "
                f"({_format_ms(overhead_percent)}%)."
            ),
            (
                "ML-KEM-768 increases the cryptographic payload because its public key "
                "and ciphertext are transmitted in addition to the two small X25519 "
                "public keys used by the hybrid flow."
            ),
            "",
            "## Relative overhead",
            "",
            "Hybrid overhead percentage equals (hybrid median - classical median) / "
            "classical median * 100. Both values use the complete_exchange timing scope.",
            "",
            _markdown_table(
                ["Comparison", "Absolute median difference (ms)", "Relative overhead"],
                [
                    [
                        "Hybrid versus X25519 + HKDF",
                        _format_ms(difference_ms),
                        f"{_format_ms(overhead_percent)}%",
                    ]
                ],
            ),
            "",
            "## Limitations",
            "",
            "- Results are specific to this machine, OS, Python process, and installed libraries.",
            "- Python wrapper and native-library overhead are both included.",
            "- Local in-process measurements do not measure network latency, TLS, Envoy, or Kubernetes performance.",
            "- The experiment does not establish formal cryptographic security, authentication, or production readiness.",
            "- Scheduling, CPU frequency policy, and background tasks can introduce variation.",
            "",
            "## Conclusion",
            "",
            (
                "The experiment provides a reproducible local comparison of the "
                "prototype's cryptographic operations and their payload trade-offs. "
                "It supports using these measurements to plan service-mesh integration, "
                "while authenticated protocol design and real deployment benchmarks "
                "remain necessary next steps."
            ),
            "",
        ]
    )


def write_benchmark_outputs(
    run: BenchmarkRun,
    output_dir: Path,
    report_path: Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Write raw data, summary, metadata, and report after a completed run."""

    paths = {
        "raw": output_dir / "benchmark_results.csv",
        "summary": output_dir / "benchmark_summary.csv",
        "environment": output_dir / "benchmark_environment.json",
        "report": report_path,
    }
    _ensure_output_paths(tuple(paths.values()), overwrite)

    with paths["raw"].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(sample.csv_row() for sample in run.samples)

    with paths["summary"].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(summary.csv_row() for summary in run.summaries)

    with paths["environment"].open("w", encoding="utf-8") as handle:
        json.dump(run.environment, handle, indent=2)
        handle.write("\n")

    paths["report"].write_text(render_benchmark_report(run), encoding="utf-8")
    return paths
