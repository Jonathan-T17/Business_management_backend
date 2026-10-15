"""Authenticated streaming encryption for backup files; keys stay outside archives."""
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"SBK1"
CHUNK = 1024 * 1024


class EncryptedWriter:
    def __init__(self, output, key):
        nonce = os.urandom(12)
        output.write(MAGIC + nonce)
        self.output = output
        self.encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
        self.encryptor.authenticate_additional_data(MAGIC)

    def write(self, data):
        self.output.write(self.encryptor.update(data))
        return len(data)

    def finish(self):
        self.output.write(self.encryptor.finalize())
        self.output.write(self.encryptor.tag)


def verify_archive(path, key):
    """Authenticate every byte without writing decrypted data anywhere."""
    with open(path, "rb") as source:
        header = source.read(16)
        if len(header) != 16 or header[:4] != MAGIC:
            raise ValueError("Invalid archive format")
        source.seek(0, 2)
        size = source.tell()
        if size < 32:
            raise ValueError("Incomplete archive")
        source.seek(-16, 2)
        tag = source.read(16)
        decryptor = Cipher(algorithms.AES(key), modes.GCM(header[4:], tag)).decryptor()
        decryptor.authenticate_additional_data(MAGIC)
        source.seek(16)
        remaining = size - 32
        while remaining:
            data = source.read(min(CHUNK, remaining))
            if not data:
                raise ValueError("Incomplete archive")
            decryptor.update(data)
            remaining -= len(data)
        decryptor.finalize()


def decrypt_archive(path, key, output):
    """Caller verifies authentication first; finalization rechecks it after reading."""
    with open(path, "rb") as source:
        header = source.read(16)
        source.seek(-16, 2)
        remaining = source.tell() - 16
        decryptor = Cipher(algorithms.AES(key), modes.GCM(header[4:], source.read(16))).decryptor()
        decryptor.authenticate_additional_data(MAGIC)
        source.seek(16)
        while remaining:
            data = source.read(min(CHUNK, remaining))
            if not data:
                raise ValueError("Incomplete archive")
            output.write(decryptor.update(data))
            remaining -= len(data)
        output.write(decryptor.finalize())
