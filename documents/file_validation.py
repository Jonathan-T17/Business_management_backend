"""Content checks for supported uploads. These checks do not replace malware scanning."""
import io
import zipfile
from PIL import Image
from xml.etree import ElementTree
from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.exceptions import ValidationError


def inspect_content(file, extension):
    position = file.tell()
    try:
        file.seek(0)
        data = file.read()
        if extension in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
            expected = {'.png':'PNG', '.jpg':'JPEG', '.jpeg':'JPEG', '.gif':'GIF', '.webp':'WEBP'}[extension]
            with Image.open(io.BytesIO(data)) as image:
                if image.format != expected or image.width * image.height > 25_000_000:
                    raise ValueError()
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                frames = getattr(image, 'n_frames', 1)
                if frames > 200 or image.width * image.height * frames > 50_000_000:
                    raise ValueError()
                for frame in range(frames):
                    image.seek(frame)
                    image.load()
        elif extension == '.pdf':
            # Signatures alone do not establish a structurally readable PDF.
            if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-2048:]:
                raise ValueError()
            from pypdf import PdfReader
            try:
                reader = PdfReader(io.BytesIO(data), strict=True)
                try:
                    if reader.is_encrypted:
                        raise ValidationError({'file': 'Choose an unencrypted PDF so its contents can be checked.'})
                    if not 1 <= len(reader.pages) <= 2000:
                        raise ValueError()
                finally:
                    reader.close()
            except ValidationError:
                raise
            except Exception as exc:
                raise ValueError() from exc
        elif extension in {'.docx', '.xlsx', '.pptx'}:
            part = {'.docx':'word/document.xml', '.xlsx':'xl/workbook.xml', '.pptx':'ppt/presentation.xml'}[extension]
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > 10_000 or sum(item.file_size for item in entries) > 100 * 1024 * 1024:
                    raise ValueError()
                names = [item.filename for item in entries]
                if len(names) != len(set(names)) or '[Content_Types].xml' not in names or part not in names:
                    raise ValueError()
                for item in entries:
                    name = item.filename.replace('\\', '/')
                    if name.startswith('/') or '..' in name.split('/') or item.flag_bits & 1 or item.file_size > max(item.compress_size, 1) * 1000:
                        raise ValueError()
                    if 'vbaproject' in name.lower() or '/activex/' in name.lower():
                        raise ValueError()
                roots = {}
                for name in ('[Content_Types].xml', part):
                    raw = archive.read(name)
                    text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
                    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
                        raise ValueError()
                    roots[name] = ElementTree.fromstring(text)
                content_namespace = 'http://schemas.openxmlformats.org/package/2006/content-types'
                if roots['[Content_Types].xml'].tag != f'{{{content_namespace}}}Types':
                    raise ValueError()
                kind, node = {'.docx':('wordprocessingml','document'), '.xlsx':('spreadsheetml','workbook'), '.pptx':('presentationml','presentation')}[extension]
                namespaces = [f'http://schemas.openxmlformats.org/{kind}/2006/main', f'http://purl.oclc.org/ooxml/{kind}/main']
                if roots[part].tag not in [f'{{{namespace}}}{node}' for namespace in namespaces]:
                    raise ValueError()
                expected_type = {'.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml', '.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml', '.pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'}[extension]
                if not any(item.get('PartName') == '/' + part and item.get('ContentType') == expected_type for item in roots['[Content_Types].xml']):
                    raise ValueError()
        else:
            # Text/CSV must be decodable text, not executable or binary content.
            if data.startswith((b'\x7fELF', b'PK\x03\x04')):
                raise ValueError()
            text = data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
            if any((ord(char) < 32 and char not in '\t\r\n') or ord(char) == 127 for char in text):
                raise ValueError()
    except (ValueError, OSError, SyntaxError, zipfile.BadZipFile, KeyError, UnicodeError, ElementTree.ParseError, Image.DecompressionBombError) as exc:
        raise ValidationError({'file': 'The file content does not match a supported, valid document. Choose the original PDF, image, Office document, or UTF-8/UTF-16 text file.'}) from exc
    finally:
        file.seek(position)


def scan_content(file):
    scanner = getattr(settings, 'ATTACHMENT_SCANNER', '')
    required = getattr(settings, 'ATTACHMENT_SCAN_REQUIRED', False)
    if not scanner:
        if required:
            raise ValidationError({'file': 'File safety checking is unavailable. Your draft remains saved; try uploading later.'})
        return
    position = file.tell()
    try:
        file.seek(0)
        if import_string(scanner)(file) is not True:
            raise ValidationError({'file': 'This file did not pass the safety check. Choose another file.'})
    except ValidationError:
        raise
    except Exception as exc:
        # An outage is never a clean verdict and scanner details stay private.
        raise ValidationError({'file': 'File safety checking is unavailable. Your draft remains saved; try uploading later.'}) from exc
    finally:
        file.seek(position)
