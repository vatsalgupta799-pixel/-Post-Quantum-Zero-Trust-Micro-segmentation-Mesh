import os
import subprocess
import sys
import unittest
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


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
        self.assertIn("X25519 shared secrets match: True", output)
        self.assertIn("ML-KEM shared secrets match: True", output)
        self.assertIn("Hybrid session keys match: True", output)
        self.assertIn("AES-GCM message recovered: True", output)
        self.assertIn("Recovered message: Zero-Trust hybrid session established", output)
        self.assertIn("Hybrid session key length: 32 bytes", output)
        self.assertNotIn("P-256", output)
        self.assertNotIn("pqcrypto", output)

    def test_aes_gcm_rejects_tampered_ciphertext(self):
        key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        plaintext = b"Zero-Trust test message"

        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        tampered = bytearray(ciphertext)
        tampered[0] ^= 1

        with self.assertRaises(InvalidTag):
            aesgcm.decrypt(nonce, bytes(tampered), None)


if __name__ == "__main__":
    unittest.main()
