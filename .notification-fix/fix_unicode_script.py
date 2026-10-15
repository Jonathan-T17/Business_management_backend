from pathlib import Path
p=Path('.notification-fix/repair_form_unicode.py');s=p.read_text(encoding='utf-8-sig').replace("decode('cp1252')","decode('cp1252',errors='replace')");p.write_text(s,encoding='utf-8');
