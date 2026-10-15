import base64
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import threading
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from platform_admin.backup_archive import CHUNK, EncryptedWriter, verify_archive
from platform_admin.health import record_evidence

LOCK_ID = 738421906


def storage_files(directory=""):
    if isinstance(default_storage, FileSystemStorage):
        location = Path(default_storage.path(directory))
        root = Path(default_storage.location).resolve()
        if location.is_symlink() or not location.resolve().is_relative_to(root):
            raise ValueError("Uploaded-file directory leaves storage")
    folders, files = default_storage.listdir(directory)
    for item in files:
        name = str(PurePosixPath(directory) / item)
        parts = PurePosixPath(name).parts
        if name.startswith("/") or ".." in parts or "\\" in name:
            raise ValueError("Unsafe storage name")
        if ".healthchecks" not in parts:
            yield name
    for folder in folders:
        if folder == ".healthchecks":
            continue
        if "/" in folder or "\\" in folder or folder == "..":
            raise ValueError("Unsafe storage directory")
        yield from storage_files(str(PurePosixPath(directory) / folder))


class Command(BaseCommand):
    help = "Create encrypted database and uploaded-file archives in the configured backup directory."

    def handle(self, *args, **options):
        directory = getattr(settings, "BACKUP_DIRECTORY", "")
        encoded_key = getattr(settings, "BACKUP_ENCRYPTION_KEY", "")
        if not directory or not encoded_key:
            raise CommandError("Configure BACKUP_DIRECTORY and BACKUP_ENCRYPTION_KEY before creating backups.")
        try:
            key = base64.b64decode(encoded_key, validate=True)
            if len(key) != 32:
                raise ValueError()
        except ValueError:
            raise CommandError("BACKUP_ENCRYPTION_KEY must be a base64-encoded 32-byte key.") from None
        root = Path(directory).resolve()
        base = Path(settings.BASE_DIR).resolve()
        if not root.is_dir() or root == base or root.is_relative_to(base):
            raise CommandError("Use an existing protected backup directory outside the application checkout.")
        if isinstance(default_storage, FileSystemStorage):
            media = Path(default_storage.location).resolve()
            if media == base or base.is_relative_to(media) or root.is_relative_to(media):
                raise CommandError("Configure a dedicated uploaded-file storage directory before backing up files.")
        executable = shutil.which("pg_dump")
        if connection.vendor != "postgresql" or not executable:
            raise CommandError("PostgreSQL and pg_dump are required for this backup command.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK_ID])
            if not cursor.fetchone()[0]:
                raise CommandError("Another backup is already running.")
        target = root / (timezone.now().strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex)
        try:
            target.mkdir(mode=0o700)
            self.backup_database(target / "database.enc", key, executable)
            self.backup_files(target / "files.enc", key)
            verify_archive(target / "database.enc", key)
            verify_archive(target / "files.enc", key)
            # A marker is written only after both archives authenticate successfully.
            (target / "COMPLETE").write_text("SmartBiz encrypted backup v1\n", encoding="utf-8")
            record_evidence("backup_copy", "healthy", "Encrypted database and file archives completed and passed integrity checks. A separate restore test is still required.")
            self.stdout.write("Encrypted backup completed. Retain its encryption key separately; verify a restore before relying on recovery.")
        except Exception:
            record_evidence("backup_copy", "unhealthy", "The backup failed. Check backup storage, uploaded-file configuration and database access. Incomplete archives must not be used for recovery.")
            raise CommandError("Backup failed. No completed backup was recorded.") from None
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])

    def backup_database(self, path, key, executable):
        database = connection.settings_dict
        env = os.environ.copy()
        for setting, variable in (("NAME", "PGDATABASE"), ("HOST", "PGHOST"), ("PORT", "PGPORT"), ("USER", "PGUSER"), ("PASSWORD", "PGPASSWORD")):
            env[variable] = str(database.get(setting) or "")
        env["PGCONNECT_TIMEOUT"] = "30"
        for setting, variable in (("sslmode", "PGSSLMODE"), ("sslrootcert", "PGSSLROOTCERT"), ("sslcert", "PGSSLCERT"), ("sslkey", "PGSSLKEY"), ("options", "PGOPTIONS")):
            if setting in database.get("OPTIONS", {}):
                env[variable] = str(database["OPTIONS"][setting])
        with path.open("xb") as output:
            writer = EncryptedWriter(output, key)
            with subprocess.Popen([executable, "--format=custom", "--no-password"], env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
                timer = threading.Timer(3600, process.kill)
                timer.daemon = True
                timer.start()
                try:
                    while data := process.stdout.read(CHUNK):
                        writer.write(data)
                    if process.wait() != 0:
                        raise RuntimeError("Database dump failed")
                    writer.finish()
                finally:
                    timer.cancel()
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=10)

    def backup_files(self, path, key):
        with path.open("xb") as output:
            writer = EncryptedWriter(output, key)
            with tarfile.open(fileobj=writer, mode="w|gz") as archive:
                for name in storage_files():
                    if isinstance(default_storage, FileSystemStorage):
                        location = Path(default_storage.path(name))
                        if location.is_symlink() or not location.resolve().is_relative_to(Path(default_storage.location).resolve()):
                            raise ValueError("Uploaded-file path leaves storage")
                    entry = tarfile.TarInfo(name)
                    entry.size = default_storage.size(name)
                    entry.mode = 0o600
                    with default_storage.open(name, "rb") as source:
                        archive.addfile(entry, source)
            writer.finish()
