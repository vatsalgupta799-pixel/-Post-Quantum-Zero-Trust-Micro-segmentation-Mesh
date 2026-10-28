from types import SimpleNamespace

from scripts.benchmark_tls import run_handshake


def _mock_openssl(monkeypatch, output, returncode=0):
    monkeypatch.setattr(
        "scripts.benchmark_tls.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=returncode,
            stdout=output,
        ),
    )


def test_classical_handshake_requires_x25519_evidence(monkeypatch):
    _mock_openssl(
        monkeypatch,
        "CONNECTION ESTABLISHED\n"
        "Protocol version: TLSv1.3\n"
        "Peer Temp Key: X25519, 253 bits\n",
    )

    result = run_handshake("classical", "127.0.0.1", 8444, 5)

    assert result["success"] is True
    assert "X25519" in result["observed_group_evidence"]


def test_hybrid_handshake_requires_hybrid_group_evidence(monkeypatch):
    _mock_openssl(
        monkeypatch,
        "CONNECTION ESTABLISHED\n"
        "Protocol version: TLSv1.3\n"
        "Negotiated TLS1.3 group: X25519MLKEM768\n",
    )

    result = run_handshake("hybrid", "127.0.0.1", 8444, 5)

    assert result["success"] is True
    assert "X25519MLKEM768" in result["observed_group_evidence"]


def test_handshake_without_expected_group_evidence_is_rejected(monkeypatch):
    _mock_openssl(
        monkeypatch,
        "CONNECTION ESTABLISHED\n"
        "Protocol version: TLSv1.3\n",
    )

    result = run_handshake("hybrid", "127.0.0.1", 8444, 5)

    assert result["success"] is False
    assert "expected_group_evidence_missing" in result["error"]
