import base64
from io import BytesIO
from unittest.mock import patch
import pytest
from cryptography.exceptions import InvalidTag
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command, CommandError
from django.test import override_settings
from platform_admin.backup_archive import EncryptedWriter, verify_archive, decrypt_archive
from platform_admin.health import backup_health
from platform_admin.models import ServiceHealthEvidence

KEY = b"k" * 32
ENCODED_KEY = base64.b64encode(KEY).decode("ascii")


def write_archive(path, data, key=KEY):
    with path.open("wb") as target:
        writer = EncryptedWriter(target, key)
        writer.write(data)
        writer.finish()


def test_archive_round_trip_and_tamper_detection(tmp_path):
    archive = tmp_path / "test.enc"
    payload = b"private company data" * 100000
    write_archive(archive, payload)
    assert payload[:50] not in archive.read_bytes()
    verify_archive(archive, KEY)
    plain = BytesIO()
    decrypt_archive(archive, KEY, plain)
    assert plain.getvalue() == payload
    with pytest.raises(InvalidTag):
        verify_archive(archive, b"j" * 32)
    data = bytearray(archive.read_bytes())
    data[30] ^= 1
    archive.write_bytes(data)
    with pytest.raises(InvalidTag):
        verify_archive(archive, KEY)


def test_recovery_authenticates_both_before_writing(tmp_path):
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "COMPLETE").touch()
    write_archive(backup / "database.enc", b"database")
    write_archive(backup / "files.enc", b"files", b"j" * 32)
    output = tmp_path / "recovery"
    with override_settings(BACKUP_ENCRYPTION_KEY=ENCODED_KEY):
        with pytest.raises(CommandError, match="authentication failed"):
            call_command("prepare_backup_restore", backup=str(backup), output=str(output))
    assert not output.exists()


def test_recovery_refuses_overwrite(tmp_path):
    with pytest.raises(CommandError, match="new protected"):
        call_command("prepare_backup_restore", backup=str(tmp_path), output=str(tmp_path))


@pytest.mark.django_db
def test_backup_records_integrity_but_never_restore_success(tmp_path):
    from platform_admin.management.commands.create_platform_backup import Command
    media = tmp_path / "uploads"
    media.mkdir()
    (media / "report.txt").write_bytes(b"report")
    (media / ".healthchecks").mkdir()
    (media / ".healthchecks" / "canary").write_bytes(b"probe")
    destination = tmp_path / "copies"
    destination.mkdir()
    def fake_dump(self, path, key, executable):
        write_archive(path, b"fake-test-dump", key)
    with override_settings(BACKUP_DIRECTORY=str(destination), BACKUP_ENCRYPTION_KEY=ENCODED_KEY), patch("platform_admin.management.commands.create_platform_backup.default_storage", FileSystemStorage(location=media)), patch("platform_admin.management.commands.create_platform_backup.shutil.which", return_value="pg_dump"), patch.object(Command, "backup_database", fake_dump):
        call_command("create_platform_backup")
    run = next(destination.iterdir())
    assert (run / "COMPLETE").exists()
    verify_archive(run / "files.enc", KEY)
    assert ServiceHealthEvidence.objects.get(service="backup_copy").status == "healthy"
    assert backup_health()["status"] == "not_monitored"
    assert "unverified" in backup_health()["detail"]
    # Repeat invocation proves the database advisory lock was released.
    with override_settings(BACKUP_DIRECTORY=str(destination), BACKUP_ENCRYPTION_KEY=ENCODED_KEY), patch("platform_admin.management.commands.create_platform_backup.default_storage", FileSystemStorage(location=media)), patch("platform_admin.management.commands.create_platform_backup.shutil.which", return_value="pg_dump"), patch.object(Command, "backup_database", side_effect=RuntimeError):
        with pytest.raises(CommandError, match="Backup failed"):
            call_command("create_platform_backup")
    assert backup_health()["status"] == "unhealthy"
    assert len(list(destination.glob("*/COMPLETE"))) == 1


def test_backup_without_configuration_refuses_to_copy():
    with override_settings(BACKUP_DIRECTORY="", BACKUP_ENCRYPTION_KEY=""):
        with pytest.raises(CommandError, match="Configure BACKUP_DIRECTORY"):
            call_command("create_platform_backup")


@pytest.mark.django_db
def test_backup_into_checkout_is_rejected(settings):
    with override_settings(BACKUP_DIRECTORY=str(settings.BASE_DIR), BACKUP_ENCRYPTION_KEY=ENCODED_KEY):
        with pytest.raises(CommandError, match="outside the application"):
            call_command("create_platform_backup")


@pytest.mark.django_db
def test_failed_encryption_stops_database_dump(tmp_path):
    from unittest.mock import MagicMock
    from platform_admin.management.commands.create_platform_backup import Command
    process = MagicMock()
    process.stdout.read.return_value = b"database"
    process.poll.return_value = None
    with patch("platform_admin.management.commands.create_platform_backup.subprocess.Popen") as launch, patch("platform_admin.management.commands.create_platform_backup.EncryptedWriter") as writer:
        launch.return_value.__enter__.return_value = process
        writer.return_value.write.side_effect = OSError("disk full")
        with pytest.raises(OSError):
            Command().backup_database(tmp_path / "database.enc", KEY, "pg_dump")
        process.kill.assert_called_once()
        process.wait.assert_called_once_with(timeout=10)
        assert launch.call_args.args[0] == ["pg_dump", "--format=custom", "--no-password"]
