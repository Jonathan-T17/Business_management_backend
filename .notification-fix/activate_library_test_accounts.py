from pathlib import Path
p=Path('tests/security/test_form_library.py');s=p.read_text(encoding='utf-8');s=s.replace("role='ADMIN')","role='ADMIN', is_active=True)");p.write_text(s,encoding='utf-8')
