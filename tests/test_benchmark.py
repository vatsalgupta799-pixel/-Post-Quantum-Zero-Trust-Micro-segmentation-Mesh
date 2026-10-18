"""Focused tests for Day 5 benchmark processing and artifact writing."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.benchmark import (
    CLASSICAL_ALGORITHM,
    HYBRID_ALGORITHM,
    MLKEM_ALGORITHM,
    PAYLOAD_CSV_COLUMNS,
    RAW_CSV_COLUMNS,
    SUMMARY_CSV_COLUMNS,
    BenchmarkRun,
    PayloadSize,
    TimingSample,
    build_summaries,
    collect_environment,
    measure_operation,
    measure_payload_sizes,
    percentile_linear,
    relative_overhead,
    summarize_latencies,
    validate_benchmark_config,
    write_benchmark_outputs,
)


def _payloads() -> tuple[PayloadSize, ...]:
    return (
        PayloadSize(CLASSICAL_ALGORITHM, 32, 2, 0, 0, 0, 0, 64),
        PayloadSize(MLKEM_ALGORITHM, 0, 0, 1184, 1, 1088, 1, 2272),
        PayloadSize(HYBRID_ALGORITHM, 32, 2, 1184, 1, 1088, 1, 2336),
    )


def _synthetic_run() -> BenchmarkRun:
    payloads = _payloads()
    samples = (
        TimingSample(CLASSICAL_ALGORITHM, "complete_exchange", 1, 1_000_000),
        TimingSample(CLASSICAL_ALGORITHM, "complete_exchange", 2, 2_000_000),
        TimingSample(MLKEM_ALGORITHM, "complete_exchange", 1, 3_000_000),
        TimingSample(MLKEM_ALGORITHM, "complete_exchange", 2, 4_000_000),
        TimingSample(HYBRID_ALGORITHM, "complete_exchange", 1, 5_000_000),
        TimingSample(HYBRID_ALGORITHM, "complete_exchange", 2, 6_000_000),
        TimingSample(CLASSICAL_ALGORITHM, "x25519_key_generation", 1, 500_000),
    )
    return BenchmarkRun(
        samples=samples,
        summaries=build_summaries(samples, payloads),
        payloads=payloads,
        environment=collect_environment(0, 2, payloads),
    )


def _workspace_temporary_directory() -> TemporaryDirectory[str]:
    root = Path(__file__).resolve().parents[1] / ".tmp"
    root.mkdir(exist_ok=True)
    return TemporaryDirectory(dir=root)


def test_raw_sample_schema_is_stable() -> None:
    sample = TimingSample(CLASSICAL_ALGORITHM, "operation", 1, 42)

    assert tuple(sample.csv_row()) == RAW_CSV_COLUMNS
    assert sample.csv_row()["latency_ns"] == 42
    assert sample.csv_row()["latency_us"] == "0.042000"
    assert sample.csv_row()["latency_ms"] == "0.000042"


def test_measured_samples_are_non_negative() -> None:
    samples = measure_operation("test", "no_op", lambda: None, warmup=0, iterations=3)

    assert len(samples) == 3
    assert all(sample.latency_ns >= 0 for sample in samples)


def test_statistics_use_mean_median_sample_stddev_and_linear_p95() -> None:
    statistics = summarize_latencies(
        [1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]
    )

    assert statistics.iterations == 5
    assert statistics.mean_ms == pytest.approx(3.0)
    assert statistics.median_ms == pytest.approx(3.0)
    assert statistics.stddev_ms == pytest.approx(1.5811388301)
    assert statistics.min_ms == pytest.approx(1.0)
    assert statistics.max_ms == pytest.approx(5.0)
    assert statistics.p95_ms == pytest.approx(4.8)
    assert percentile_linear([1, 2, 3, 4, 5], 95) == pytest.approx(4.8)


def test_relative_overhead_is_calculated_against_classical_baseline() -> None:
    difference, percentage = relative_overhead(2.0, 3.5)

    assert difference == pytest.approx(1.5)
    assert percentage == pytest.approx(75.0)


def test_payload_sizes_use_actual_serialized_values() -> None:
    payloads = {payload.algorithm: payload for payload in measure_payload_sizes()}
    classical = payloads[CLASSICAL_ALGORITHM]
    mlkem = payloads[MLKEM_ALGORITHM]
    hybrid = payloads[HYBRID_ALGORITHM]

    assert classical.total_payload_bytes == (
        classical.x25519_public_key_bytes * classical.x25519_public_key_count
    )
    assert mlkem.total_payload_bytes == (
        mlkem.mlkem_public_key_bytes * mlkem.mlkem_public_key_count
        + mlkem.mlkem_ciphertext_bytes * mlkem.mlkem_ciphertext_count
    )
    assert hybrid.total_payload_bytes == (
        hybrid.x25519_public_key_bytes * hybrid.x25519_public_key_count
        + hybrid.mlkem_public_key_bytes * hybrid.mlkem_public_key_count
        + hybrid.mlkem_ciphertext_bytes * hybrid.mlkem_ciphertext_count
    )


def test_csv_output_generation_uses_documented_columns() -> None:
    run = _synthetic_run()
    with _workspace_temporary_directory() as directory:
        temporary_path = Path(directory)
        paths = write_benchmark_outputs(
            run,
            temporary_path / "results",
            temporary_path / "benchmark_report.md",
        )

        with paths["raw"].open(newline="", encoding="utf-8") as handle:
            raw_rows = list(csv.DictReader(handle))
            assert tuple(raw_rows[0]) == RAW_CSV_COLUMNS
        with paths["summary"].open(newline="", encoding="utf-8") as handle:
            summary_rows = list(csv.DictReader(handle))
            assert tuple(summary_rows[0]) == SUMMARY_CSV_COLUMNS
            complete = next(
                row
                for row in summary_rows
                if row["algorithm"] == CLASSICAL_ALGORITHM
                and row["operation"] == "complete_exchange"
            )
            assert all(complete[column] for column in PAYLOAD_CSV_COLUMNS)


def test_environment_metadata_is_json_serializable() -> None:
    run = _synthetic_run()
    with _workspace_temporary_directory() as directory:
        temporary_path = Path(directory)
        paths = write_benchmark_outputs(
            run,
            temporary_path / "results",
            temporary_path / "benchmark_report.md",
        )

        metadata = json.loads(paths["environment"].read_text(encoding="utf-8"))
        assert metadata["benchmark_configuration"]["warmup_iterations"] == 0
        assert metadata["benchmark_configuration"]["measured_iterations"] == 2
        assert len(metadata["payload_sizes"]) == 3
        assert paths["report"].read_text(encoding="utf-8").startswith(
            "# Day 5 Benchmark Report"
        )


def test_existing_artifacts_require_explicit_overwrite() -> None:
    run = _synthetic_run()
    with _workspace_temporary_directory() as directory:
        temporary_path = Path(directory)
        output_dir = temporary_path / "results"
        report_path = temporary_path / "benchmark_report.md"
        write_benchmark_outputs(run, output_dir, report_path)

        with pytest.raises(FileExistsError):
            write_benchmark_outputs(run, output_dir, report_path)

        write_benchmark_outputs(run, output_dir, report_path, overwrite=True)


def test_empty_or_invalid_measurements_are_rejected() -> None:
    with pytest.raises(ValueError):
        summarize_latencies([])
    with pytest.raises(ValueError):
        percentile_linear([], 50)
    with pytest.raises(ValueError):
        summarize_latencies([-1])
    with pytest.raises(ValueError):
        build_summaries([], _payloads())


def test_invalid_iteration_counts_are_rejected() -> None:
    with pytest.raises(ValueError):
        validate_benchmark_config(-1, 1)
    with pytest.raises(ValueError):
        validate_benchmark_config(0, 0)
    with pytest.raises(ValueError):
        validate_benchmark_config(True, 1)


def test_same_stored_samples_produce_same_summary() -> None:
    samples = _synthetic_run().samples
    assert build_summaries(samples, _payloads()) == build_summaries(samples, _payloads())
