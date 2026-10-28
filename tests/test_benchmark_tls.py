"""Merge regression tests for the verified per-connection benchmark."""
import math
import pytest

from scripts import benchmark_tls


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_invalid_ports_rejected(port):
    with pytest.raises(ValueError, match="port"):
        benchmark_tls.run_tls_benchmark("classical", "localhost", port)


@pytest.mark.parametrize("timeout", [0, -1, math.inf, math.nan])
def test_invalid_timeouts_rejected(timeout):
    with pytest.raises(ValueError, match="timeout"):
        benchmark_tls.run_tls_benchmark("classical", "localhost", 443, timeout=timeout)


@pytest.mark.parametrize("missing", ["connection_succeeded", "certificate_verified", "negotiated_group_verified"])
def test_missing_connection_evidence_is_not_success(monkeypatch, missing):
    result = {"connection_succeeded": True, "certificate_verified": True,
              "negotiated_group_verified": True, "tls_version": "TLSv1.3",
              "negotiated_group": "X25519"}
    result[missing] = False
    monkeypatch.setattr(benchmark_tls, "verify_tls_group", lambda **kw: result)
    sample = benchmark_tls._measure_single_connection("localhost", 443, "localhost", 5, "classical", 1, "run", None, None, None, None)
    assert not sample.success
    assert sample.error_type


def test_failed_measured_attempt_returns_nonzero_after_writing(monkeypatch, tmp_path):
    samples = [benchmark_tls.TLSSample("run", "now", "classical", 1, False, 1.0, "", "", False, None, "failed")]
    monkeypatch.setattr(benchmark_tls, "run_tls_benchmark", lambda **kw: (samples, {}))
    result = benchmark_tls.main(["--mode", "classical", "--host", "localhost", "--port", "443", "--output-dir", str(tmp_path)])
    assert result == 1
    assert "failed" in (tmp_path / "raw.csv").read_text()


def test_analysis_rejects_failed_attempts(monkeypatch, tmp_path, capsys):
    from scripts import analyze_tls_results
    classical = [{"mode": "classical", "attempt": "1", "success": "True",
                  "latency_ms": "1", "tls_version": "TLSv1.3",
                  "negotiated_group": "X25519", "certificate_verified": "True",
                  "session_reused": "False"},
                 {"mode": "classical", "attempt": "2", "success": "False", "latency_ms": "2"}]
    hybrid = [{"mode": "hybrid", "attempt": "1", "success": "True",
               "latency_ms": "1", "tls_version": "TLSv1.3",
               "negotiated_group": "X25519MLKEM768", "certificate_verified": "True",
               "session_reused": "False"}]
    monkeypatch.setattr(analyze_tls_results, "read_raw_csv", lambda path: classical if path.name == "c.csv" else hybrid)
    status = analyze_tls_results.main(["--classical-csv", str(tmp_path / "c.csv"),
                                       "--hybrid-csv", str(tmp_path / "h.csv"),
                                       "--output-dir", str(tmp_path / "report")])
    assert status == 1
    assert "1 classical and 0 hybrid" in capsys.readouterr().err
    assert not (tmp_path / "report").exists()
