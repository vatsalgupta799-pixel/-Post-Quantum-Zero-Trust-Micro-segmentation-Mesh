import time
import logging
import threading
import os

from dataclasses import dataclass, field
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class KeyRecord:
    key_id: int
    key: bytes = field(repr=False)
    created_at: float = field(default_factory=time.time)
    active: bool = True
    retire_at: float | None = None


class KeyRotationManager:

    def __init__(
        self,
        rotation_interval=3600,
        grace_period=300,
        max_history=1000
    ):

        if rotation_interval <= 0:
            raise ValueError("Rotation interval must be positive")

        if grace_period < 0:
            raise ValueError("Grace period cannot be negative")

        if (
            not isinstance(max_history, int)
            or isinstance(max_history, bool)
            or max_history <= 0
        ):
            raise ValueError("Maximum history must be a positive integer")

        self.rotation_interval = rotation_interval
        self.grace_period = grace_period
        self.max_history = max_history

        self.lock = threading.RLock()

        self._keys = {}
        self.rotation_history = []

        self._stop_event = None
        self._rotation_thread = None

        self.current_key = self._generate_key(1)
        self._keys[self.current_key.key_id] = self.current_key

        logger.info("Initial encryption key generated")

    def _generate_key(self, key_id):

        if (
            not isinstance(key_id, int)
            or isinstance(key_id, bool)
            or key_id <= 0
            or key_id >= 2**64
        ):
            raise ValueError("Key ID must be a valid positive integer")

        key = AESGCM.generate_key(bit_length=256)

        if len(key) != 32:
            raise ValueError("Generated key must be 256 bits")

        return KeyRecord(
            key_id=key_id,
            key=key
        )

    def _retire_expired_keys(self):

        now = time.time()

        expired_ids = [
            key_id
            for key_id, record in self._keys.items()
            if not record.active
            and record.retire_at is not None
            and now >= record.retire_at
        ]

        for key_id in expired_ids:
            del self._keys[key_id]
            logger.info("Previous key %s retired", key_id)

    def rotate_key(self):

        with self.lock:

            now = time.time()

            old_key = self.current_key
            new_key_id = old_key.key_id + 1

            new_key = self._generate_key(new_key_id)

            old_key.active = False
            old_key.retire_at = now + self.grace_period

            self.current_key = new_key
            self._keys[new_key_id] = new_key

            self.rotation_history.append({
                "old_key_id": old_key.key_id,
                "new_key_id": new_key.key_id,
                "rotated_at": now
            })

            # Keep history within the configured limit
            if len(self.rotation_history) > self.max_history:
                del self.rotation_history[
                    :-self.max_history
                ]

            self._retire_expired_keys()

            logger.info(
                "Key rotation successful: %s -> %s",
                old_key.key_id,
                new_key.key_id
            )

            return new_key_id

    def check_rotation(self):

        with self.lock:

            elapsed = time.time() - self.current_key.created_at

            if elapsed >= self.rotation_interval:
                self.rotate_key()
                return True

            self._retire_expired_keys()
            return False

    def get_active_key_id(self):

        with self.lock:
            return self.current_key.key_id

    def encrypt(self, message):

        if not isinstance(message, bytes):
            raise TypeError("Message must be bytes")

        with self.lock:

            self.check_rotation()

            key_record = self.current_key

            nonce = os.urandom(12)

            aad = key_record.key_id.to_bytes(8, "big")

            ciphertext = AESGCM(key_record.key).encrypt(
                nonce,
                message,
                aad
            )

            return key_record.key_id, nonce, ciphertext

    def decrypt(self, key_id, nonce, ciphertext):

        if (
            not isinstance(key_id, int)
            or isinstance(key_id, bool)
            or key_id <= 0
            or key_id >= 2**64
        ):
            raise ValueError("Invalid key ID")

        if not isinstance(nonce, bytes) or len(nonce) != 12:
            raise ValueError("Nonce must be exactly 12 bytes")

        if not isinstance(ciphertext, bytes):
            raise TypeError("Ciphertext must be bytes")

        with self.lock:

            self._retire_expired_keys()

            key_record = self._keys.get(key_id)

            if key_record is None:
                raise ValueError(
                    "Encryption key is unavailable or retired"
                )

            aad = key_id.to_bytes(8, "big")

            return AESGCM(key_record.key).decrypt(
                nonce,
                ciphertext,
                aad
            )

    def get_rotation_history(self):

        with self.lock:
            return [
                record.copy()
                for record in self.rotation_history
            ]

    # Automatic background key rotation

    def start_auto_rotation(self):

        with self.lock:

            if (
                self._rotation_thread is not None
                and self._rotation_thread.is_alive()
            ):
                logger.warning("Auto rotation is already running")
                return

            stop_event = threading.Event()
            self._stop_event = stop_event

            def rotation_loop():

                while not stop_event.wait(1):

                    try:
                        self.check_rotation()

                    except Exception:
                        logger.exception(
                            "Automatic key rotation check failed"
                        )

            self._rotation_thread = threading.Thread(
                target=rotation_loop,
                daemon=True
            )

            self._rotation_thread.start()

            logger.info("Automatic key rotation started")

    def stop_auto_rotation(self):

        with self.lock:

            stop_event = self._stop_event
            rotation_thread = self._rotation_thread

            if stop_event is None or rotation_thread is None:
                logger.info("Automatic rotation is not running")
                return

            stop_event.set()

        # Wait outside the lock so the worker can finish safely
        if rotation_thread is not threading.current_thread():
            rotation_thread.join()

        with self.lock:

            if self._rotation_thread is rotation_thread:
                self._rotation_thread = None
                self._stop_event = None

        logger.info("Automatic key rotation stopped")
