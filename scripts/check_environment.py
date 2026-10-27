"""Verify the Day 1 Python and cryptographic environment.

This script checks library capability only. It intentionally does not
implement or claim to implement the project's future hybrid protocol.
"""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VENV = (PROJECT_ROOT / ".venv").resolve()
MINIMUM_PYTHON = (3, 11)


class Result:
    """A single user-facing environment check result."""

    def __init__(self, name: str, state: str, detail: str) -> None:
        self.name = name
        self.state = state
        self.detail = detail

    def print(self) -> None:
        print(f"[{self.state}] {self.name}: {self.detail}")


def check_python() -> Result:
    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info[:2] < MINIMUM_PYTHON:
        return Result(
            "Python version",
            "BLOCKED",
            f"{version}; Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}+ is recommended",
        )
    return Result("Python version", "PASS", version)


def check_virtual_environment() -> Result:
    actual_prefix = Path(sys.prefix).resolve()
    if sys.prefix == sys.base_prefix:
        return Result(
            "Virtual environment",
            "FAIL",
            f"not active; expected interpreter under {EXPECTED_VENV}",
        )
    if actual_prefix != EXPECTED_VENV:
        return Result(
            "Virtual environment",
            "FAIL",
            f"interpreter prefix is {actual_prefix}, expected {EXPECTED_VENV}",
        )
    return Result("Virtual environment", "PASS", str(actual_prefix))


def check_cryptography_import() -> Result:
    try:
        import cryptography

        installed_version = importlib.metadata.version("cryptography")
        return Result(
            "cryptography import",
            "PASS",
            f"{installed_version} (module reports {cryptography.__version__})",
        )
    except (ImportError, importlib.metadata.PackageNotFoundError) as error:
        return Result("cryptography import", "FAIL", f"package unavailable: {error}")


def check_x25519() -> Result:
    try:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

        service_a = X25519PrivateKey.generate()
        service_b = X25519PrivateKey.generate()
        secret_a = service_a.exchange(service_b.public_key())
        secret_b = service_b.exchange(service_a.public_key())
        if secret_a != secret_b:
            return Result("X25519 support", "FAIL", "exchange results did not match")
        return Result("X25519 support", "PASS", "import and exchange check passed")
    except ImportError as error:
        return Result("X25519 support", "FAIL", f"API unavailable: {error}")
    except Exception as error:  # pragma: no cover - backend-specific diagnostic
        return Result("X25519 support", "FAIL", f"runtime check failed: {error}")


def check_mlkem768() -> Result:
    try:
        from cryptography.exceptions import UnsupportedAlgorithm
        from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey

        private_key = MLKEM768PrivateKey.generate()
        shared_secret, ciphertext = private_key.public_key().encapsulate()
        recovered_secret = private_key.decapsulate(ciphertext)
        if shared_secret != recovered_secret:
            return Result(
                "ML-KEM-768 support",
                "FAIL",
                "encapsulation and decapsulation results did not match",
            )
        return Result(
            "ML-KEM-768 support",
            "PASS",
            "encapsulation and decapsulation check passed",
        )
    except ImportError as error:
        return Result(
            "ML-KEM-768 support",
            "BLOCKED",
            f"selected cryptography backend does not expose ML-KEM-768: {error}",
        )
    except UnsupportedAlgorithm as error:
        return Result(
            "ML-KEM-768 support",
            "BLOCKED",
            f"selected cryptography backend does not expose ML-KEM-768: {error}",
        )
    except NotImplementedError as error:
        return Result("ML-KEM-768 support", "BLOCKED", f"backend limitation: {error}")
    except Exception as error:  # pragma: no cover - backend-specific diagnostic
        return Result("ML-KEM-768 support", "FAIL", f"runtime check failed: {error}")


def main() -> int:
    results = [
        check_python(),
        check_virtual_environment(),
        check_cryptography_import(),
    ]

    # Avoid attempting primitive checks when the selected package cannot be imported.
    if results[-1].state == "PASS":
        results.extend((check_x25519(), check_mlkem768()))
    else:
        results.extend(
            (
                Result("X25519 support", "BLOCKED", "cryptography import did not pass"),
                Result("ML-KEM-768 support", "BLOCKED", "cryptography import did not pass"),
            )
        )

    for result in results:
        result.print()

    counts = {
        state: sum(result.state == state for result in results)
        for state in ("PASS", "FAIL", "BLOCKED")
    }
    print(
        "Summary: "
        f"{counts['PASS']} passed, {counts['FAIL']} failed, {counts['BLOCKED']} blocked"
    )

    if counts["FAIL"]:
        return 1
    if counts["BLOCKED"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
