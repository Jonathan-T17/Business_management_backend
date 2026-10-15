"""Synchronous ClamAV INSTREAM scanner; no upload is persisted before a clean verdict."""
import socket
import struct
from django.conf import settings


def clamav(file):
    with socket.create_connection((settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=15) as connection:
        connection.settimeout(15)
        connection.sendall(b'zINSTREAM\0')
        for chunk in iter(lambda: file.read(64 * 1024), b''):
            connection.sendall(struct.pack('!I', len(chunk)) + chunk)
        connection.sendall(struct.pack('!I', 0))
        response = b''
        while b'\0' not in response and len(response) < 4096:
            block = connection.recv(4096 - len(response))
            if not block:
                break
            response += block
        # zINSTREAM requires a complete NUL-terminated verdict. A disconnected
        # or truncated reply is not proof that the file was scanned clean.
        return response == b'stream: OK\0'
