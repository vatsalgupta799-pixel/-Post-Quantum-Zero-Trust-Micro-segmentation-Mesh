import time
import unittest

from Key_rotation import KeyRotationManager


class TestKeyRotation(unittest.TestCase):

    def setUp(self):
        self.manager = KeyRotationManager(
            rotation_interval=3600,
            grace_period=0
        )

    def test_initial_key_generation(self):
        self.assertEqual(
            self.manager.get_active_key_id(), 1
        )

    def test_manual_key_rotation(self):
        self.manager.rotate_key()

        self.assertEqual(
            self.manager.get_active_key_id(), 2
        )

    def test_encryption_and_decryption(self):
        message = b"Zero Trust Security Test"

        key_id, nonce, ciphertext = self.manager.encrypt(message)

        decrypted = self.manager.decrypt(
            key_id, nonce, ciphertext
        )

        self.assertEqual(decrypted, message)

    def test_old_key_retirement(self):
        old_key_id = self.manager.get_active_key_id()

        self.manager.rotate_key()

        with self.assertRaises(ValueError):
            self.manager.decrypt(
                old_key_id,
                b"0" * 12,
                b"invalid"
            )

    def test_time_based_rotation(self):
        manager = KeyRotationManager(
            rotation_interval=1,
            grace_period=0
        )

        time.sleep(1.2)

        self.assertTrue(manager.check_rotation())

        self.assertEqual(
            manager.get_active_key_id(), 2
        )


if __name__ == "__main__":
    unittest.main()
