from pathlib import Path
p=Path('docs/ready-made-forms-implementation.md');s=p.read_text(encoding='utf-8');s=s.replace('Open Form library, expand Add ready-made forms to your company, preview a card and add it to Company forms.','Open Forms and select Ready-made library, preview a card and add it to Company forms.');s+='''

## Navigation refinement — 3 October 2026

Company forms opens first. Administrators browse the Ready-made library in a separate tab, open saved cards within the same workspace, and return with Back to forms. Card descriptions are limited to two lines. Rare actions appear under More options; update details and approval settings expand on request. Submissions is a separate entry view with its existing server-authorized scope. Duplicate Form library navigation and the local Forms navigation row have been removed. Existing URLs continue to work.

Saved company forms now load across all API pages so searching does not omit later forms. Frontend type checking and lint passed. Live administrator cards, library switching, form opening/return, submissions and keyboard tab navigation were checked; employee cards show no administrator controls. No forms or work entries were changed by these checks.
''';p.write_text(s,encoding='utf-8')
