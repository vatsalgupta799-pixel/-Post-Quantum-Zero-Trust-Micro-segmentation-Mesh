import time
import logging
import threading

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

    def __init__(self, rotation_interval=3600, grace_period=300):

        if rotation_interval <= 0:
            raise ValueError("Rotation interval must be positive")

        if grace_period < 0:
            raise ValueError("Grace period cannot be negative")

        self.rotation_interval = rotation_interval
        self.grace_period = grace_period

        self.lock = threading.RLock()

        self._keys = {}
        self.rotation_history = []

        self._stop_event = None
        self._rotation_thread = None

        self.current_key = self._generate_key(1)
        self._keys[self.current_key.key_id] = self.current_key

        logger.info("Initial encryption key generated")

    def _generate_key(self, key_id):

        return KeyRecord(
            key_id=key_id,
            key=AESGCM.generate_key(bit_length=256)
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
                "new_key_id": new_key_id,
                "rotated_at": now
            })

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

        with self.lock:

            self.check_rotation()

            key_record = self.current_key

            nonce = __import__("os").urandom(12)

            aad = key_record.key_id.to_bytes(8, "big")

            ciphertext = AESGCM(key_record.key).encrypt(
                nonce,
                message,
                aad
            )

            return key_record.key_id, nonce, ciphertext

    def decrypt(self, key_id, nonce, ciphertext):

        with self.lock:

            self._retire_expired_keys()

            key_record = self._keys.get(key_id)

            if key_record is None:
                raise ValueError("Encryption key is unavailable or retired")

            aad = key_id.to_bytes(8, "big")

            return AESGCM(key_record.key).decrypt(
                nonce,
                ciphertext,
                aad
            )

    def get_rotation_history(self):

        with self.lock:
            return list(self.rotation_history)

    # Automatic background key rotation

    def start_auto_rotation(self):

        with self.lock:

            if (self._rotation_thread is not None
                    and self._rotation_thread.is_alive()):
                logger.warning("Auto rotation is already running")
                return

            self._stop_event = threading.Event()

            def rotation_loop():

                while not self._stop_event.wait(1):
                    self.check_rotation()

            self._rotation_thread = threading.Thread(
                target=rotation_loop,
                daemon=True
            )

            self._rotation_thread.start()

            logger.info("Automatic key rotation started")

    def stop_auto_rotation(self):

        with self.lock:

            if self._stop_event is not None:
                self._stop_event.set()
                logger.info("Automatic key rotation stopped")
