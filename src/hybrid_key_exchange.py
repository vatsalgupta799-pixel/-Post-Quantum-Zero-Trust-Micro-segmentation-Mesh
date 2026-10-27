from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pqcrypto.kem import ml_kem_768
import os


def main():
    print("=== Hybrid ECDH + ML-KEM-768 Demo ===")

    # Receiver creates classical ECDH and post-quantum ML-KEM keys.
    receiver_ec_private = ec.generate_private_key(ec.SECP256R1())
    receiver_ec_public = receiver_ec_private.public_key()
    receiver_kem_public, receiver_kem_secret = ml_kem_768.keygen()

    # Sender creates its own ECDH key pair.
    sender_ec_private = ec.generate_private_key(ec.SECP256R1())
    sender_ec_public = sender_ec_private.public_key()

    # Classical shared secret: ECDH.
    sender_ec_secret = sender_ec_private.exchange(
        ec.ECDH(), receiver_ec_public
    )
    receiver_ec_secret = receiver_ec_private.exchange(
        ec.ECDH(), sender_ec_public
    )

    # Post-quantum shared secret: ML-KEM-768.
    ciphertext, sender_kem_secret = ml_kem_768.encaps(
        receiver_kem_public
    )
    receiver_kem_secret = ml_kem_768.decaps(
        receiver_kem_secret, ciphertext
    )

    # Combine both secrets and derive a 256-bit session key.
    if sender_ec_secret != receiver_ec_secret:
        raise RuntimeError("ECDH secrets do not match")
    if sender_kem_secret != receiver_kem_secret:
        raise RuntimeError("ML-KEM secrets do not match")

    combined_sender = sender_ec_secret + sender_kem_secret
    combined_receiver = receiver_ec_secret + receiver_kem_secret
    salt = os.urandom(32)

    def derive_key(secret):
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b"Post-Quantum Zero-Trust Hybrid Session v1",
        ).derive(secret)

    sender_key = derive_key(combined_sender)
    receiver_key = derive_key(combined_receiver)

    print("ECDH shared secrets match:", sender_ec_secret == receiver_ec_secret)
    print("ML-KEM shared secrets match:", sender_kem_secret == receiver_kem_secret)
    print("Hybrid session keys match:", sender_key == receiver_key)

    # Demonstrate authenticated encryption with the derived key.
    nonce = os.urandom(12)
    message = b"Zero-Trust hybrid session established"
    encrypted = AESGCM(sender_key).encrypt(nonce, message, None)
    decrypted = AESGCM(receiver_key).decrypt(nonce, encrypted, None)

    print("AES-GCM message recovered:", decrypted == message)
    print("Recovered message:", decrypted.decode())
    print("ML-KEM ciphertext bytes:", len(ciphertext))
    print("Hybrid key bytes:", len(sender_key))


if __name__ == "__main__":
    main()
