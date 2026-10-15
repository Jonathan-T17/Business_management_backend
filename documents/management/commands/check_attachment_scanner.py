"""Probe the configured scanner without storing uploads or changing company data."""
import io

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string


class Command(BaseCommand):
    help = 'Verify the configured upload scanner using synthetic in-memory content.'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--test-detection', action='store_true', help='Also require rejection of the harmless standard EICAR antivirus test string.')
        parser.add_argument('--test-upload-limit', action='store_true', help='Also scan a clean 25 MiB stream to verify the application upload limit.')

    def handle(self, *args, **options):
        scanner_path = getattr(settings, 'ATTACHMENT_SCANNER', '')
        if not scanner_path:
            raise CommandError('No attachment scanner is configured; verification did not run.')
        try:
            scanner = import_string(scanner_path)
            if scanner(io.BytesIO(b'Synthetic clean upload safety probe.\n')) is not True:
                raise CommandError('The scanner did not return a clean verdict for the synthetic clean probe.')
            if options['test_upload_limit']:
                from documents.services import MAX_ATTACHMENT_SIZE
                if scanner(io.BytesIO(b' ' * MAX_ATTACHMENT_SIZE)) is not True:
                    raise CommandError('The scanner did not accept the application upload-size probe.')
            if options['test_detection']:
                # Standard harmless antivirus test content; never written to disk.
                test_content = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
                if scanner(io.BytesIO(test_content)) is not False:
                    raise CommandError('Detection verification failed: the scanner did not explicitly reject the antivirus test content.')
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError('Scanner verification could not complete. Check its private connection, readiness and signatures.') from exc
        checks = ['clean content']
        if options['test_upload_limit']:
            checks.append('upload-size limit')
        if options['test_detection']:
            checks.append('antivirus test detection')
        self.stdout.write(self.style.SUCCESS('Scanner checks passed: ' + ', '.join(checks) + '. No uploads were stored.'))
        if not options['test_detection']:
            self.stdout.write('Detection has not been verified; run --test-detection on the isolated deployment host.')
