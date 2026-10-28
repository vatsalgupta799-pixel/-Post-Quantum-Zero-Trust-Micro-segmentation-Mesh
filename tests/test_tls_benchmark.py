"""Tests for Week 2 TLS benchmarking and analysis code.

These tests validate the statistical calculations, CSV schema handling,
comparison logic, and edge cases. They use only synthetic data and never
pretend a TLS handshake occurred.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from io import StringIO

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# We import from the scripts directory — adjust path
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Import the functions we want to test from the three scripts.
# We use importlib to avoid __main__ execution.
import importlib.util


def _import_module(name: str, path: Path):
    """Import a module from a file path without executing __main__."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


benchmark_tls = _import_module("benchmark_tls_mod", SCRIPTS_DIR / "benchmark_tls.py")
analyze_tls = _import_module("analyze_tls_mod", SCRIPTS_DIR / "analyze_tls_results.py")
verify_tls = _import_module("verify_tls_mod", SCRIPTS_DIR / "verify_tls_group.py")


# ===================================================================
# Tests for percentile_linear (shared calculation method)
# ===================================================================

class TestPercentileCalculation:
    """Validate the linearly interpolated percentile function."""

    def test_single_value_returns_itself(self):
        assert benchmark_tls.percentile_linear([42.0], 50) == 42.0
        assert benchmark_tls.percentile_linear([42.0], 0) == 42.0
        assert benchmark_tls.percentile_linear([42.0], 100) == 42.0

    def test_median_of_odd_count(self):
        assert benchmark_tls.percentile_linear([1, 2, 3, 4, 5], 50) == 3.0

    def test_p95_with_linear_interpolation(self):
        values = [1, 2, 3, 4, 5]
        # (5-1) * 0.95 = 3.8 → 4 + (5-4)*0.8 = 4.8
        assert benchmark_tls.percentile_linear(values, 95) == pytest.approx(4.8)

    def test_p99_with_linear_interpolation(self):
        values = [1, 2, 3, 4, 5]
        # (5-1) * 0.99 = 3.96 → 4 + (5-4)*0.96 = 4.96
        assert benchmark_tls.percentile_linear(values, 99) == pytest.approx(4.96)

    def test_p0_returns_minimum(self):
        assert benchmark_tls.percentile_linear([5, 1, 3], 0) == 1.0

    def test_p100_returns_maximum(self):
        assert benchmark_tls.percentile_linear([5, 1, 3], 100) == 5.0

    def test_empty_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            benchmark_tls.percentile_linear([], 50)

    def test_invalid_percentile_raises(self):
        with pytest.raises(ValueError):
            benchmark_tls.percentile_linear([1, 2], -1)
        with pytest.raises(ValueError):
            benchmark_tls.percentile_linear([1, 2], 101)

    def test_two_values(self):
        # p50 of [10, 20] = 15.0 (linear interpolation)
        assert benchmark_tls.percentile_linear([10, 20], 50) == pytest.approx(15.0)

    def test_consistent_with_analysis_module(self):
        """Ensure both modules give the same result."""
        values = [1.5, 2.3, 4.7, 8.1, 12.0, 15.5]
        for p in (50, 95, 99):
            assert benchmark_tls.percentile_linear(values, p) == pytest.approx(
                analyze_tls.percentile_linear(values, p)
            )


# ===================================================================
# Tests for compute_statistics
# ===================================================================

class TestComputeStatistics:
    """Validate the summary statistics computation."""

    def test_basic_statistics(self):
        latencies = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = benchmark_tls.compute_statistics(latencies)
        assert stats["count"] == 5
        assert stats["mean_ms"] == pytest.approx(3.0)
        assert stats["min_ms"] == pytest.approx(1.0)
        assert stats["max_ms"] == pytest.approx(5.0)
        assert stats["p50_ms"] == pytest.approx(3.0)
        assert stats["p95_ms"] == pytest.approx(4.8)
        assert stats["p99_ms"] == pytest.approx(4.96)

    def test_single_value(self):
        stats = benchmark_tls.compute_statistics([42.0])
        assert stats["count"] == 1
        assert stats["mean_ms"] == pytest.approx(42.0)
        assert stats["stddev_ms"] is None
        assert analyze_tls.compute_statistics([42.0])["stddev_ms"] is None
        assert stats["p50_ms"] == pytest.approx(42.0)

    def test_empty_returns_none_values(self):
        stats = benchmark_tls.compute_statistics([])
        assert stats["count"] == 0
        assert stats["mean_ms"] is None
        assert stats["p50_ms"] is None
        assert stats["p99_ms"] is None

    def test_stddev_with_two_values(self):
        stats = benchmark_tls.compute_statistics([10.0, 20.0])
        assert stats["count"] == 2
        assert stats["stddev_ms"] == pytest.approx(7.0710678, rel=1e-4)

    def test_identical_values(self):
        stats = benchmark_tls.compute_statistics([5.0, 5.0, 5.0])
        assert stats["stddev_ms"] == pytest.approx(0.0)
        assert stats["p50_ms"] == pytest.approx(5.0)
        assert stats["p99_ms"] == pytest.approx(5.0)


# ===================================================================
# Tests for relative_overhead
# ===================================================================

class TestRelativeOverhead:
    """Validate the percentage overhead calculation."""

    def test_positive_overhead(self):
        diff, pct = benchmark_tls.relative_overhead(2.0, 3.0)
        assert diff == pytest.approx(1.0)
        assert pct == pytest.approx(50.0)

    def test_negative_overhead(self):
        diff, pct = benchmark_tls.relative_overhead(3.0, 2.0)
        assert diff == pytest.approx(-1.0)
        assert pct == pytest.approx(-33.333, rel=1e-3)

    def test_zero_overhead(self):
        diff, pct = benchmark_tls.relative_overhead(5.0, 5.0)
        assert diff == pytest.approx(0.0)
        assert pct == pytest.approx(0.0)

    def test_zero_baseline_returns_none_percentage(self):
        diff, pct = benchmark_tls.relative_overhead(0.0, 5.0)
        assert diff == pytest.approx(5.0)
        assert pct is None

    def test_large_overhead(self):
        diff, pct = benchmark_tls.relative_overhead(1.0, 10.0)
        assert diff == pytest.approx(9.0)
        assert pct == pytest.approx(900.0)

    def test_analysis_module_agrees(self):
        """Both modules' relative_overhead must behave the same."""
        diff_b, pct_b = benchmark_tls.relative_overhead(2.0, 3.5)
        diff_a, pct_a = analyze_tls.relative_overhead(2.0, 3.5)
        assert diff_b == pytest.approx(diff_a)
        assert pct_b == pytest.approx(pct_a)

    def test_analysis_overhead_with_none_inputs(self):
        diff, pct = analyze_tls.relative_overhead(None, 5.0)
        assert diff is None
        assert pct is None

        diff, pct = analyze_tls.relative_overhead(5.0, None)
        assert diff is None
        assert pct is None


# ===================================================================
# Tests for CSV reading and schema validation
# ===================================================================

class TestCSVParsing:
    """Validate raw CSV reading and data extraction."""

    def _write_csv(self, tmp_dir: Path, filename: str, rows: list[dict]) -> Path:
        path = tmp_dir / filename
        if not rows:
            path.write_text("", encoding="utf-8")
            return path
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return path

    def test_valid_csv_reads_successfully(self, tmp_path):
        rows = [
            {"run_id": "abc", "timestamp_utc": "2026-01-01", "mode": "classical",
             "attempt": "1", "success": "True", "latency_ms": "1.234",
             "tls_version": "TLSv1.3", "negotiated_group": "X25519",
             "certificate_verified": "True", "session_reused": "False", "error_type": ""},
            {"run_id": "abc", "timestamp_utc": "2026-01-01", "mode": "classical",
             "attempt": "2", "success": "True", "latency_ms": "2.345",
             "tls_version": "TLSv1.3", "negotiated_group": "X25519",
             "certificate_verified": "True", "session_reused": "False", "error_type": ""},
        ]
        path = self._write_csv(tmp_path, "test.csv", rows)
        result = analyze_tls.read_raw_csv(path)
        assert len(result) == 2

    def test_missing_columns_raises(self, tmp_path):
        rows = [{"run_id": "abc", "timestamp_utc": "2026-01-01"}]
        path = self._write_csv(tmp_path, "bad.csv", rows)
        with pytest.raises(ValueError, match="missing required columns"):
            analyze_tls.read_raw_csv(path)

    def test_empty_file_raises(self, tmp_path):
        path = tmp_path / "empty.csv"
        path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="Empty CSV"):
            analyze_tls.read_raw_csv(path)

    def test_headers_only_raises(self, tmp_path):
        path = tmp_path / "headers_only.csv"
        path.write_text(
            "mode,attempt,success,latency_ms,tls_version,negotiated_group,"
            "certificate_verified,session_reused\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="no data rows"):
            analyze_tls.read_raw_csv(path)

    def test_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            analyze_tls.read_raw_csv(tmp_path / "nope.csv")

    def test_extract_latencies_filters_by_mode(self, tmp_path):
        rows = [
            {"mode": "classical", "attempt": "1", "success": "True", "latency_ms": "1.0"},
            {"mode": "hybrid", "attempt": "2", "success": "True", "latency_ms": "2.0"},
            {"mode": "classical", "attempt": "3", "success": "True", "latency_ms": "3.0"},
        ]
        latencies, success, fail = analyze_tls.extract_latencies(rows, "classical")
        assert success == 2
        assert fail == 0
        assert latencies == pytest.approx([1.0, 3.0])

    def test_extract_latencies_counts_failures(self, tmp_path):
        rows = [
            {"mode": "classical", "attempt": "1", "success": "True", "latency_ms": "1.0"},
            {"mode": "classical", "attempt": "2", "success": "False", "latency_ms": "5.0"},
            {"mode": "classical", "attempt": "3", "success": "False", "latency_ms": "6.0"},
        ]
        latencies, success, fail = analyze_tls.extract_latencies(rows, "classical")
        assert success == 1
        assert fail == 2

    def test_malformed_latency_counted_as_failure(self, tmp_path):
        rows = [
            {"mode": "classical", "attempt": "1", "success": "True", "latency_ms": "not_a_number"},
        ]
        latencies, success, fail = analyze_tls.extract_latencies(rows, "classical")
        assert success == 0
        assert fail == 1

    def test_verified_samples_reject_configuration_only_group_label(self):
        rows = [{
            "mode": "classical", "attempt": "1", "success": "True",
            "latency_ms": "1.0", "tls_version": "TLSv1.3",
            "negotiated_group": "CONFIGURED:X25519",
            "certificate_verified": "True", "session_reused": "False",
        }]
        with pytest.raises(ValueError, match="directly verified"):
            analyze_tls.validate_verified_samples(rows, "classical", "X25519")

    def test_verified_samples_accept_exact_group_and_certificate(self):
        rows = [{
            "mode": "hybrid", "attempt": "1", "success": "True",
            "latency_ms": "1.0", "tls_version": "TLSv1.3",
            "negotiated_group": "X25519MLKEM768",
            "certificate_verified": "True", "session_reused": "False",
        }]
        analyze_tls.validate_verified_samples(rows, "hybrid", "X25519MLKEM768")


# ===================================================================
# Tests for TLSSample CSV schema
# ===================================================================

class TestTLSSampleSchema:
    """Verify TLSSample dataclass produces the correct CSV schema."""

    def test_csv_row_keys_match_columns(self):
        sample = benchmark_tls.TLSSample(
            run_id="test",
            timestamp_utc="2026-01-01T00:00:00Z",
            mode="classical",
            attempt=1,
            success=True,
            latency_ms=1.234567,
            tls_version="TLSv1.3",
            negotiated_group="X25519",
            certificate_verified=True,
            session_reused=False,
            error_type="",
        )
        row = sample.csv_row()
        assert tuple(row.keys()) == benchmark_tls.RAW_CSV_COLUMNS

    def test_latency_precision(self):
        sample = benchmark_tls.TLSSample(
            run_id="test",
            timestamp_utc="2026-01-01T00:00:00Z",
            mode="classical",
            attempt=1,
            success=True,
            latency_ms=1.123456789,
            tls_version="TLSv1.3",
            negotiated_group="X25519",
            certificate_verified=True,
            session_reused=False,
            error_type="",
        )
        row = sample.csv_row()
        # Verify 6 decimal places
        assert row["latency_ms"] == "1.123457"

    def test_failed_sample_records_error(self):
        sample = benchmark_tls.TLSSample(
            run_id="test",
            timestamp_utc="2026-01-01T00:00:00Z",
            mode="hybrid",
            attempt=1,
            success=False,
            latency_ms=100.0,
            tls_version="",
            negotiated_group="",
            certificate_verified=False,
            session_reused=False,
            error_type="SSLError:SSLCertVerificationError",
        )
        row = sample.csv_row()
        assert row["success"] == "False"
        assert row["error_type"] == "SSLError:SSLCertVerificationError"
        assert row["negotiated_group"] == ""
        assert row["certificate_verified"] == "False"


# ===================================================================
# Tests for comparison logic
# ===================================================================

class TestComparisonLogic:
    """Validate the build_comparison function."""

    def test_comparison_with_valid_stats(self):
        c_stats = {"p50_ms": 1.0, "p95_ms": 2.0, "p99_ms": 3.0, "mean_ms": 1.5}
        h_stats = {"p50_ms": 1.5, "p95_ms": 3.0, "p99_ms": 4.5, "mean_ms": 2.0}
        comp = analyze_tls.build_comparison(c_stats, h_stats)

        assert comp["p50_classical_ms"] == 1.0
        assert comp["p50_hybrid_ms"] == 1.5
        assert comp["p50_abs_diff_ms"] == pytest.approx(0.5)
        assert comp["p50_rel_overhead_pct"] == pytest.approx(50.0)

        assert comp["p95_abs_diff_ms"] == pytest.approx(1.0)
        assert comp["p95_rel_overhead_pct"] == pytest.approx(50.0)

    def test_comparison_with_none_values(self):
        c_stats = {"p50_ms": None, "p95_ms": 2.0, "p99_ms": 3.0, "mean_ms": 1.5}
        h_stats = {"p50_ms": 1.5, "p95_ms": None, "p99_ms": 4.5, "mean_ms": 2.0}
        comp = analyze_tls.build_comparison(c_stats, h_stats)
        assert comp["p50_abs_diff_ms"] is None
        assert comp["p95_abs_diff_ms"] is None

    def test_comparison_zero_classical(self):
        c_stats = {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "mean_ms": 0.0}
        h_stats = {"p50_ms": 1.0, "p95_ms": 2.0, "p99_ms": 3.0, "mean_ms": 1.5}
        comp = analyze_tls.build_comparison(c_stats, h_stats)
        # Should not divide by zero
        assert comp["p50_abs_diff_ms"] == pytest.approx(1.0)
        assert comp["p50_rel_overhead_pct"] is None


# ===================================================================
# Tests for classical/hybrid sample separation
# ===================================================================

class TestModeSeparation:
    """Ensure classical and hybrid samples are never mixed."""

    def test_classical_rows_not_in_hybrid_extraction(self):
        rows = [
            {"mode": "classical", "attempt": "1", "success": "True", "latency_ms": "1.0"},
            {"mode": "classical", "attempt": "2", "success": "True", "latency_ms": "2.0"},
        ]
        latencies, success, fail = analyze_tls.extract_latencies(rows, "hybrid")
        assert success == 0
        assert latencies == []

    def test_hybrid_rows_not_in_classical_extraction(self):
        rows = [
            {"mode": "hybrid", "attempt": "1", "success": "True", "latency_ms": "5.0"},
        ]
        latencies, success, fail = analyze_tls.extract_latencies(rows, "classical")
        assert success == 0


# ===================================================================
# Tests for verification module
# ===================================================================

class TestVerificationModule:
    """Test the verify_tls_group module's helper functions."""

    def test_expected_groups_map(self):
        assert verify_tls.EXPECTED_GROUPS["classical"] == "X25519"
        assert verify_tls.EXPECTED_GROUPS["hybrid"] == "X25519MLKEM768"

    def test_classical_group_does_not_match_hybrid_substring(self, monkeypatch):
        from types import SimpleNamespace
        monkeypatch.setattr(verify_tls, "_find_openssl", lambda path: "openssl")
        monkeypatch.setattr(verify_tls.subprocess, "run", lambda *a, **kw: SimpleNamespace(
            stdout="CONNECTION ESTABLISHED\nProtocol version: TLSv1.3\nVerification: OK\nNegotiated TLS1.3 group: X25519MLKEM768\n",
            stderr="", returncode=0))
        result = verify_tls.verify_tls_group("classical", "localhost", 443, use_openssl=True)
        assert not result["negotiated_group_verified"]

    def test_nonzero_client_exit_is_not_success(self, monkeypatch):
        from types import SimpleNamespace
        monkeypatch.setattr(verify_tls, "_find_openssl", lambda path: "openssl")
        monkeypatch.setattr(verify_tls.subprocess, "run", lambda *a, **kw: SimpleNamespace(
            stdout="CONNECTED\nProtocol version: TLSv1.3\nVerification: OK\nPeer Temp Key: X25519, 253 bits\n",
            stderr="", returncode=1))
        result = verify_tls.verify_tls_group("classical", "localhost", 443, use_openssl=True)
        assert not result["connection_succeeded"]

    def test_analysis_rejects_resumed_or_unknown_session(self):
        row = {"mode": "classical", "attempt": "1", "success": "True",
               "tls_version": "TLSv1.3", "negotiated_group": "X25519",
               "certificate_verified": "True", "session_reused": "True"}
        with pytest.raises(ValueError, match="fresh session"):
            analyze_tls.validate_verified_samples([row], "classical", "X25519")

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="mode must be"):
            verify_tls.verify_tls_group(
                mode="invalid",
                host="localhost",
                port=443,
            )

    def test_supported_modes_tuple(self):
        assert "classical" in verify_tls.SUPPORTED_MODES
        assert "hybrid" in verify_tls.SUPPORTED_MODES

    def test_envoy_style_negotiated_group_output_is_recognized(self):
        output = "Negotiated TLS1.3 group: X25519MLKEM768"
        match = next(
            (re.search(pattern, output, re.IGNORECASE)
             for pattern in verify_tls.NEGOTIATED_GROUP_PATTERNS
             if re.search(pattern, output, re.IGNORECASE)),
            None,
        )
        assert match is not None
        assert match.group(1) == "X25519MLKEM768"

    def test_openssl_41_protocol_version_output_is_recognized(self):
        output = "Protocol version: TLSv1.3"
        match = re.search(
            r"Protocol(?:\s+version)?\s*:\s*(TLSv[\d.]+)",
            output,
            re.IGNORECASE,
        )
        assert match is not None
        assert match.group(1) == "TLSv1.3"

    def test_openssl_41_peer_temp_key_output_is_recognized(self):
        output = "Peer Temp Key: X25519, 253 bits"
        match = next(
            (re.search(pattern, output, re.IGNORECASE)
             for pattern in verify_tls.NEGOTIATED_GROUP_PATTERNS
             if re.search(pattern, output, re.IGNORECASE)),
            None,
        )
        assert match is not None
        assert match.group(1).rstrip(",") == "X25519"


# ===================================================================
# Tests for incomplete experiment handling
# ===================================================================

class TestIncompleteExperiments:
    """Edge cases for incomplete or all-failure runs."""

    def test_all_failures_produce_none_statistics(self):
        rows = [
            {"mode": "classical", "attempt": "1", "success": "False", "latency_ms": "100.0"},
            {"mode": "classical", "attempt": "2", "success": "False", "latency_ms": "200.0"},
        ]
        latencies, success, fail = analyze_tls.extract_latencies(rows, "classical")
        assert success == 0
        assert fail == 2
        stats = analyze_tls.compute_statistics(latencies)
        assert stats["count"] == 0
        assert stats["p50_ms"] is None

    def test_mixed_success_failure(self):
        rows = [
            {"mode": "hybrid", "attempt": "1", "success": "True", "latency_ms": "1.0"},
            {"mode": "hybrid", "attempt": "2", "success": "False", "latency_ms": "999.0"},
            {"mode": "hybrid", "attempt": "3", "success": "True", "latency_ms": "2.0"},
        ]
        latencies, success, fail = analyze_tls.extract_latencies(rows, "hybrid")
        assert success == 2
        assert fail == 1
        # Failure latency should NOT appear in the success latencies
        assert 999.0 not in latencies

    def test_write_results_creates_all_files(self, tmp_path):
        """Test that write_results creates raw.csv, metadata.json, and summary.txt."""
        samples = [
            benchmark_tls.TLSSample(
                run_id="test",
                timestamp_utc="2026-01-01T00:00:00Z",
                mode="classical",
                attempt=1,
                success=True,
                latency_ms=1.5,
                tls_version="TLSv1.3",
                negotiated_group="X25519",
                certificate_verified=True,
                session_reused=False,
                error_type="",
            ),
        ]
        metadata = {
            "run_id": "test",
            "mode": "classical",
            "statistics": {"p50_ms": 1.5, "p95_ms": 1.5, "p99_ms": 1.5},
        }
        output_dir = tmp_path / "output"
        paths = benchmark_tls.write_results(samples, metadata, output_dir)
        assert paths["raw"].exists()
        assert paths["metadata"].exists()
        assert paths["summary"].exists()

        # Verify CSV contents
        with paths["raw"].open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["mode"] == "classical"
        assert rows[0]["success"] == "True"
        assert paths["verification"].exists()

    def test_write_results_refuses_to_overwrite_by_default(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "raw.csv").write_text("old data", encoding="utf-8")
        with pytest.raises(FileExistsError, match="Refusing to overwrite"):
            benchmark_tls.write_results([], {}, output_dir)


# ===================================================================
# Tests for benchmark input validation
# ===================================================================

class TestBenchmarkValidation:
    """Validate that run_tls_benchmark rejects bad inputs."""

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="mode must be"):
            benchmark_tls.run_tls_benchmark(mode="invalid", host="localhost", port=443)

    def test_negative_warmup_raises(self):
        with pytest.raises(ValueError, match="warmup"):
            benchmark_tls.run_tls_benchmark(mode="classical", host="localhost", port=443, warmup=-1)

    def test_zero_iterations_raises(self):
        with pytest.raises(ValueError, match="iterations"):
            benchmark_tls.run_tls_benchmark(mode="classical", host="localhost", port=443, iterations=0)


# ===================================================================
# Tests for reproducible output schema
# ===================================================================

class TestOutputSchemaReproducibility:
    """Ensure the output schema is stable and documented."""

    def test_raw_csv_columns_are_documented(self):
        assert benchmark_tls.RAW_CSV_COLUMNS == (
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

    def test_statistics_keys_are_complete(self):
        stats = benchmark_tls.compute_statistics([1.0, 2.0, 3.0])
        required_keys = {"count", "mean_ms", "stddev_ms", "min_ms", "max_ms",
                         "p50_ms", "p95_ms", "p99_ms"}
        assert required_keys.issubset(set(stats.keys()))


def test_tcp_connected_is_not_completed_tls(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(verify_tls, "_find_openssl", lambda path: "openssl")
    monkeypatch.setattr(verify_tls.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        stdout="CONNECTED\nProtocol version: TLSv1.3\nVerification: OK\nPeer Temp Key: X25519, 253 bits\n", stderr="", returncode=0))
    assert not verify_tls.verify_tls_group("classical", "localhost", 443, use_openssl=True)["connection_succeeded"]


def test_cli_requires_certificate_verification(monkeypatch):
    monkeypatch.setattr(verify_tls, "verify_tls_group", lambda **kw: {
        "negotiated_group_verified": True, "connection_succeeded": True,
        "certificate_verified": False, "tls_version": "TLSv1.3"})
    assert verify_tls.main(["--mode", "classical", "--host", "localhost", "--port", "443"]) == 1


def test_unknown_session_is_not_independent_freshness_evidence():
    row = {"mode": "classical", "attempt": "1", "success": "True",
           "tls_version": "TLSv1.3", "negotiated_group": "X25519",
           "certificate_verified": "True", "session_reused": "None"}
    with pytest.raises(ValueError, match="fresh session"):
        analyze_tls.validate_verified_samples([row], "classical", "X25519")
