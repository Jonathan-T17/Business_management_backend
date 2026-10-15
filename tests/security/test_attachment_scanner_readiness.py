import io
from unittest.mock import Mock

import pytest
import yaml
from django.core.management import call_command
from django.core.management.base import CommandError


def run_probe(settings, monkeypatch, scanner, **options):
    settings.ATTACHMENT_SCANNER = 'documents.scanning.clamav'
    monkeypatch.setattr('documents.management.commands.check_attachment_scanner.import_string', lambda path: scanner)
    output = io.StringIO()
    call_command('check_attachment_scanner', stdout=output, **options)
    return output.getvalue()


def test_scanner_readiness_never_passes_without_configuration(settings):
    settings.ATTACHMENT_SCANNER = ''
    with pytest.raises(CommandError, match='No attachment scanner'):
        call_command('check_attachment_scanner')


def test_scanner_readiness_verifies_clean_detection_and_upload_limit(settings, monkeypatch):
    sizes = []
    def scanner(file):
        data = file.read()
        sizes.append(len(data))
        return b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE' not in data
    output = run_probe(settings, monkeypatch, scanner, test_detection=True, test_upload_limit=True)
    assert sizes[1] == 25 * 1024 * 1024
    assert sizes[2] == 68
    assert 'antivirus test detection' in output
    assert 'No uploads were stored' in output


@pytest.mark.parametrize('verdict', [False, None, 'OK', 1])
def test_scanner_readiness_requires_explicit_clean_verdict(settings, monkeypatch, verdict):
    with pytest.raises(CommandError, match='clean verdict'):
        run_probe(settings, monkeypatch, lambda file: verdict)


def test_scanner_readiness_rejects_false_detection_claim(settings, monkeypatch):
    with pytest.raises(CommandError, match='Detection verification failed'):
        run_probe(settings, monkeypatch, lambda file: True, test_detection=True)


def test_scanner_readiness_outage_hides_private_details(settings, monkeypatch):
    with pytest.raises(CommandError) as error:
        run_probe(settings, monkeypatch, Mock(side_effect=OSError('private service detail')))
    assert 'private service detail' not in str(error.value)


def test_clean_only_probe_does_not_claim_detection(settings, monkeypatch):
    assert 'Detection has not been verified' in run_probe(settings, monkeypatch, lambda file: True)


def test_scanner_deployment_has_no_public_socket_or_company_storage():
    from pathlib import Path
    config = yaml.safe_load(Path('deployment/docker-compose.scanner.yml').read_text())
    scanner = config['services']['clamav']
    assert not scanner.get('ports')
    assert scanner['volumes'] == ['clamav_signatures:/var/lib/clamav']
    assert config['networks']['upload_scanning']['internal'] is True
    assert config['services']['backend']['depends_on']['clamav']['condition'] == 'service_healthy'


@pytest.mark.parametrize('reply,expected', [(b'stream: OK\0', True), (b'stream: OK', False), (b'stream: OK\0unexpected', False), (b'stream: Eicar-Test-Signature FOUND\0', False), (b'INSTREAM size limit exceeded. ERROR\0', False), (b'', False)])
def test_scanner_requires_a_complete_clean_protocol_response(settings, monkeypatch, reply, expected):
    from documents.scanning import clamav
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def settimeout(self, value): pass
        def sendall(self, data): pass
        def recv(self, size):
            nonlocal reply
            block, reply = reply[:size], reply[size:]
            return block
    monkeypatch.setattr('documents.scanning.socket.create_connection', lambda *args, **kwargs: Connection())
    assert clamav(io.BytesIO(b'synthetic probe')) is expected
