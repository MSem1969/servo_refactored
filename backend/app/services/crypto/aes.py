# =============================================================================
# SERV.O v11.6 - AES-256 ENCRYPTION SERVICE
# =============================================================================
# Servizio crittografia per dati sensibili (password FTP, etc.)
# Requisito NIS-2 compliance
# =============================================================================

import os
import base64
import secrets
from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend


# Costanti
KEY_LENGTH = 32  # 256 bits
IV_LENGTH = 16   # 128 bits (AES block size)
ENCODING = 'utf-8'


class CryptoError(Exception):
    """Errore durante operazioni crittografiche."""
    pass


class AESCrypto:
    """
    Servizio crittografia AES-256-CBC.

    Formato storage: base64(IV + encrypted_data)
    - IV: 16 bytes random (prepeso ai dati criptati)
    - Key: 32 bytes da variabile ambiente FTP_ENCRYPTION_KEY

    Uso:
        crypto = AESCrypto()
        encrypted = crypto.encrypt("password_segreta")
        decrypted = crypto.decrypt(encrypted)
    """

    def __init__(self, key: Optional[str] = None):
        """
        Inizializza con chiave da env o parametro.

        Args:
            key: Chiave esadecimale 64 caratteri (32 bytes).
                 Se None, usa FTP_ENCRYPTION_KEY da ambiente.
        """
        self.key = self._load_key(key)

    def _load_key(self, key: Optional[str] = None) -> bytes:
        """Carica e valida chiave di crittografia."""
        if key is None:
            key = os.environ.get('FTP_ENCRYPTION_KEY')

        if not key:
            raise CryptoError(
                "Chiave crittografia non configurata. "
                "Impostare FTP_ENCRYPTION_KEY (64 caratteri hex)"
            )

        try:
            key_bytes = bytes.fromhex(key)
            if len(key_bytes) != KEY_LENGTH:
                raise CryptoError(
                    f"Chiave deve essere {KEY_LENGTH * 2} caratteri hex "
                    f"({KEY_LENGTH} bytes), ricevuti {len(key_bytes)} bytes"
                )
            return key_bytes
        except ValueError as e:
            raise CryptoError(f"Chiave non valida (deve essere hex): {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Cripta stringa con AES-256-CBC.

        Args:
            plaintext: Testo da criptare

        Returns:
            Stringa base64 contenente IV + dati criptati
        """
        if not plaintext:
            raise CryptoError("Testo da criptare vuoto")

        # Genera IV random
        iv = secrets.token_bytes(IV_LENGTH)

        # Padding PKCS7
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode(ENCODING)) + padder.finalize()

        # Encrypt
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        # Preponi IV ai dati criptati e codifica base64
        return base64.b64encode(iv + encrypted).decode(ENCODING)

    def decrypt(self, ciphertext: str) -> str:
        """
        Decripta stringa AES-256-CBC.

        Args:
            ciphertext: Stringa base64 da decriptare

        Returns:
            Testo originale
        """
        if not ciphertext:
            raise CryptoError("Testo da decriptare vuoto")

        try:
            # Decodifica base64
            raw = base64.b64decode(ciphertext)

            if len(raw) < IV_LENGTH + 16:  # Minimo: IV + 1 blocco
                raise CryptoError("Dati criptati corrotti (troppo corti)")

            # Estrai IV e dati
            iv = raw[:IV_LENGTH]
            encrypted = raw[IV_LENGTH:]

            # Decrypt
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            padded = decryptor.update(encrypted) + decryptor.finalize()

            # Rimuovi padding
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded) + unpadder.finalize()

            return data.decode(ENCODING)

        except Exception as e:
            if isinstance(e, CryptoError):
                raise
            raise CryptoError(f"Errore decriptazione: {e}")

    @staticmethod
    def generate_key() -> str:
        """
        Genera nuova chiave AES-256 random.

        Returns:
            Stringa esadecimale 64 caratteri
        """
        return secrets.token_hex(KEY_LENGTH)


# =============================================================================
# FUNZIONI HELPER
# =============================================================================

_crypto_instance: Optional[AESCrypto] = None


def get_crypto() -> AESCrypto:
    """Ottiene istanza singleton del servizio crypto."""
    global _crypto_instance
    if _crypto_instance is None:
        _crypto_instance = AESCrypto()
    return _crypto_instance


def encrypt_password(password: str) -> str:
    """Cripta password FTP."""
    return get_crypto().encrypt(password)


def decrypt_password(encrypted: str) -> str:
    """Decripta password FTP."""
    return get_crypto().decrypt(encrypted)


def generate_encryption_key() -> str:
    """Genera nuova chiave per FTP_ENCRYPTION_KEY."""
    return AESCrypto.generate_key()
