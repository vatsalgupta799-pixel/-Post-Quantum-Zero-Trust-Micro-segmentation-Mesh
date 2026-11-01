"""Input safety checks; live TLS controls are documented in the study report."""
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from openssl_handshake_probe import ProbeError, probe
from benchmark_handshake_probe import ORDERINGS


@pytest.mark.parametrize("timeout", [0, -1, math.inf, math.nan])
def test_invalid_timeout_rejected_before_loading_library(timeout):
    with pytest.raises(ValueError):
        probe("127.0.0.1", 443, "localhost", Path("missing"), "classical", timeout, Path("missing"))


def test_ip_server_name_rejected_until_ip_identity_check_is_supported():
    with pytest.raises(ValueError, match="DNS name"):
        probe("127.0.0.1", 443, "127.0.0.1", Path("missing"), "classical", 1, Path("missing"))


def test_missing_ca_or_library_is_rejected():
    with pytest.raises(ProbeError, match="does not exist"):
        probe("127.0.0.1", 443, "localhost", Path("missing"), "classical", 1, Path("missing"))


def test_both_block_orders_are_balanced_and_start_with_requested_mode():
    for name, ordering in ORDERINGS.items():
        assert ordering[0] == name.removesuffix("-first")
        assert ordering.count("classical") == ordering.count("hybrid") == 2
        assert ordering == ordering[::-1]
