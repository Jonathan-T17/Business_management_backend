import base64
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from platform_admin.backup_archive import verify_archive, decrypt_archive


class Command(BaseCommand):
    help = "Authenticate and decrypt a backup into a new protected recovery directory; never restores the live database."

    def add_arguments(self, parser):
        parser.add_argument("--backup", required=True)
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        backup = Path(options["backup"]).resolve()
        output = Path(options["output"]).resolve()
        base = Path(settings.BASE_DIR).resolve()
        if output.exists() or output.is_relative_to(base) or output.is_relative_to(backup):
            raise CommandError("Choose a new protected recovery directory outside the application and backup directory.")
        if not (backup / "COMPLETE").is_file():
            raise CommandError("This backup has no completion marker.")
        try:
            key = base64.b64decode(getattr(settings, "BACKUP_ENCRYPTION_KEY", ""), validate=True)
            if len(key) != 32:
                raise ValueError()
            for name in ("database.enc", "files.enc"):
                verify_archive(backup / name, key)
        except Exception:
            raise CommandError("Backup authentication failed. Check the encryption key and archive integrity.") from None
        output.mkdir(mode=0o700)
        try:
            for encrypted, plain in (("database.enc", "database.dump"), ("files.enc", "files.tar.gz")):
                with (output / plain).open("xb") as destination:
                    decrypt_archive(backup / encrypted, key, destination)
        except Exception:
            raise CommandError("Recovery preparation failed. Discard incomplete recovery files and try a new directory.") from None
        self.stdout.write("Recovery files prepared. Restore into an isolated test database and file store, then verify application data. No restore-success evidence was recorded.")
