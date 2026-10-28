"""Merge regression tests for the verified per-connection benchmark."""
import math
import pytest

from scripts import benchmark_tls
from scripts import verify_tls_group


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


@pytest.mark.parametrize("name,verification_flag", [
    ("localhost", "-verify_hostname"),
    ("127.0.0.1", "-verify_ip"),
])
def test_openssl_requests_identity_and_chain_validation(monkeypatch, name, verification_flag):
    from types import SimpleNamespace
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=1, stdout="", stderr="verification failed")

    monkeypatch.setattr(verify_tls_group, "_find_openssl", lambda path: "openssl")
    monkeypatch.setattr(verify_tls_group.subprocess, "run", run)
    result = verify_tls_group.verify_tls_group(
        "classical", "127.0.0.1", 443, server_name=name, ca_file="ca.pem", use_openssl=True
    )
    command = captured["command"]
    assert "-verify_return_error" in command
    assert command[command.index(verification_flag) + 1] == name
    assert command[command.index("-CAfile") + 1] == "ca.pem"
    assert not result["connection_succeeded"]


@pytest.mark.parametrize("lines,expected", [
    ("New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384\n", False),
    ("Reused, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384\n", True),
    ("New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384\nReused, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384\n", None),
    ("CONNECTED\n", None),
])
def test_observed_session_status_fails_closed(lines, expected):
    assert verify_tls_group._session_status(lines) is expected


@pytest.mark.parametrize("session_status", [False, True, None])
def test_measurement_carries_observed_session_state(monkeypatch, session_status):
    result = {"connection_succeeded": True, "certificate_verified": True,
              "negotiated_group_verified": True, "tls_version": "TLSv1.3",
              "negotiated_group": "X25519", "session_reused": session_status}
    monkeypatch.setattr(benchmark_tls, "verify_tls_group", lambda **kw: result)
    sample = benchmark_tls._measure_single_connection("localhost", 443, "localhost", 5, "classical", 1, "run", None, None, None, None)
    assert sample.session_reused is session_status


def test_verbose_client_output_is_filtered(monkeypatch):
    from types import SimpleNamespace
    output = ("New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384\n"
              "Peer Temp Key: X25519, 253 bits\nVerification: OK\n"
              "Master-Key: secret-material\nSession-ID: secret-material\n")
    monkeypatch.setattr(verify_tls_group, "_find_openssl", lambda path: "openssl")
    monkeypatch.setattr(verify_tls_group.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0, stdout=output, stderr=""))
    result = verify_tls_group.verify_tls_group("classical", "localhost", 443, use_openssl=True)
    assert result["connection_succeeded"] and result["certificate_verified"]
    assert result["session_reused"] is False
    assert "secret-material" not in repr(result)


def test_failed_handshake_never_reports_certificate_verified(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(verify_tls_group, "_find_openssl", lambda path: "openssl")
    monkeypatch.setattr(verify_tls_group.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=1, stdout="Verification: OK\nVerify return code: 0 (ok)\n", stderr="handshake failure"))
    result = verify_tls_group.verify_tls_group("hybrid", "localhost", 443, use_openssl=True)
    assert not result["connection_succeeded"]
    assert not result["certificate_verified"]


def test_report_labels_process_timing_and_session_evidence(tmp_path):
    from scripts import analyze_tls_results
    classical = analyze_tls_results.compute_statistics([1.0, 2.0])
    hybrid = analyze_tls_results.compute_statistics([2.0, 3.0])
    comparison = analyze_tls_results.build_comparison(classical, hybrid)
    report = analyze_tls_results.generate_report(
        classical, hybrid, comparison, None, None, 2, 2, 0, 0, [], tmp_path
    ).read_text(encoding="utf-8")
    assert "not isolated handshake latency" in report
    assert "unknown or resumed sessions are rejected" in report
    assert "classical-full/raw.csv" not in report
