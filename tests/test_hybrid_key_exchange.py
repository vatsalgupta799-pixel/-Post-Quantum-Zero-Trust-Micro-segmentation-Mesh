import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "src" / "hybrid_key_exchange.py"


class TestHybridKeyExchange(unittest.TestCase):
    def test_hybrid_exchange_and_encryption(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT,
            timeout=30,
        )

        output = result.stdout
        self.assertIn("ECDH shared secrets match: True", output)
        self.assertIn("ML-KEM shared secrets match: True", output)
        self.assertIn("Hybrid session keys match: True", output)
        self.assertIn("AES-GCM message recovered: True", output)


if __name__ == "__main__":
    unittest.main()
