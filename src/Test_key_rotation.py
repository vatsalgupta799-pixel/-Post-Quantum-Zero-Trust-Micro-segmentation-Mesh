import time
import unittest

from Key_rotation import KeyRotationManager


class TestKeyRotation(unittest.TestCase):

    def setUp(self):
        self.manager = KeyRotationManager(
            rotation_interval=3600,
            grace_period=0
        )

    def tearDown(self):
        self.manager.stop_auto_rotation()

        if self.manager._rotation_thread is not None:
            self.manager._rotation_thread.join(timeout=2)

    # Initial key generation

    def test_initial_key_generation(self):
        self.assertEqual(
            self.manager.get_active_key_id(), 1
        )

    def test_generated_key_is_256_bits(self):
        key = self.manager.current_key.key
        self.assertEqual(len(key), 32)

    # Manual key rotation

    def test_manual_key_rotation(self):
        self.manager.rotate_key()

        self.assertEqual(
            self.manager.get_active_key_id(), 2
        )

    # Encryption and decryption

    def test_encryption_and_decryption(self):
        message = b"Zero Trust Security Test"

        key_id, nonce, ciphertext = self.manager.encrypt(message)

        decrypted = self.manager.decrypt(
            key_id, nonce, ciphertext
        )

        self.assertEqual(decrypted, message)

    # Old key retirement

    def test_old_key_retirement(self):
        old_key_id = self.manager.get_active_key_id()

        self.manager.rotate_key()

        with self.assertRaises(ValueError):
            self.manager.decrypt(
                old_key_id,
                b"0" * 12,
                b"invalid"
            )

    # Grace period validation

    def test_old_key_works_during_grace_period(self):
        manager = KeyRotationManager(
            rotation_interval=3600,
            grace_period=3
        )

        try:
            message = b"Grace Period Security Test"

            old_id, nonce, ciphertext = manager.encrypt(message)

            manager.rotate_key()

            self.assertEqual(
                manager.get_active_key_id(), 2
            )

            decrypted = manager.decrypt(
                old_id, nonce, ciphertext
            )

            self.assertEqual(decrypted, message)

        finally:
            manager.stop_auto_rotation()

    def test_old_key_rejected_after_grace_period(self):
        manager = KeyRotationManager(
            rotation_interval=3600,
            grace_period=1
        )

        try:
            message = b"Expired Key Security Test"

            old_id, nonce, ciphertext = manager.encrypt(message)

            manager.rotate_key()

            time.sleep(1.2)

            with self.assertRaises(ValueError):
                manager.decrypt(
                    old_id, nonce, ciphertext
                )

        finally:
            manager.stop_auto_rotation()

    # Time-based rotation

    def test_time_based_rotation(self):
        manager = KeyRotationManager(
            rotation_interval=1,
            grace_period=0
        )

        try:
            time.sleep(1.2)

            self.assertTrue(manager.check_rotation())

            self.assertEqual(
                manager.get_active_key_id(), 2
            )

        finally:
            manager.stop_auto_rotation()

    # Automatic background rotation

    def test_automatic_background_rotation(self):
        manager = KeyRotationManager(
            rotation_interval=1,
            grace_period=0
        )

        try:
            manager.start_auto_rotation()

            time.sleep(1.5)

            self.assertEqual(
                manager.get_active_key_id(), 2
            )

        finally:
            manager.stop_auto_rotation()

            if manager._rotation_thread is not None:
                manager._rotation_thread.join(timeout=2)

    def test_scheduler_starts_only_once(self):
        manager = KeyRotationManager()

        try:
            manager.start_auto_rotation()

            first_thread = manager._rotation_thread

            manager.start_auto_rotation()

            self.assertIs(
                manager._rotation_thread, first_thread
            )

        finally:
            manager.stop_auto_rotation()

            if manager._rotation_thread is not None:
                manager._rotation_thread.join(timeout=2)

    # Security validation tests

    def test_invalid_key_id_rejected(self):
        with self.assertRaises(ValueError):
            self.manager._generate_key(-1)

        with self.assertRaises(ValueError):
            self.manager._generate_key(0)

    def test_invalid_nonce_length_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.decrypt(
                1,
                b"short",
                b"invalid"
            )

    def test_invalid_key_id_during_decryption(self):
        with self.assertRaises(ValueError):
            self.manager.decrypt(
                -1,
                b"0" * 12,
                b"invalid"
            )

    def test_non_bytes_message_rejected(self):
        with self.assertRaises(TypeError):
            self.manager.encrypt("Invalid message")

    # Day 6: Key history validation

    def test_invalid_max_history_rejected(self):
        with self.assertRaises(ValueError):
            KeyRotationManager(max_history=0)

        with self.assertRaises(ValueError):
            KeyRotationManager(max_history=-1)

    def test_max_history_accepts_valid_value(self):
        manager = KeyRotationManager(max_history=5)

        try:
            self.assertEqual(manager.max_history, 5)
        finally:
            manager.stop_auto_rotation()


if __name__ == "__main__":
    unittest.main()
