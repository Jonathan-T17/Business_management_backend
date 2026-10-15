from pathlib import Path
import re
from collections import Counter

root = Path('../business_management_frontend/src')
counts = Counter()
for path in root.rglob('*'):
    if path.suffix in {'.tsx', '.ts'}:
        counts.update(re.findall(r'(?<![\w-])(?:hover:)?(?:bg|text|border)-(?:gray|slate|neutral|blue|indigo|cyan|teal|emerald|green|amber|yellow|orange|red|rose|purple|violet)-\d+(?:/\d+)?', path.read_text(encoding='utf-8')))

palette = {
    'neutral': ('var(--surface-soft)', 'var(--muted)'),
    'gray': ('var(--surface-soft)', 'var(--muted)'),
    'slate': ('var(--surface-soft)', 'var(--muted)'),
    'blue': ('#203354', '#b3ceff'), 'indigo': ('#203354', '#b3ceff'), 'cyan': ('#203354', '#b3ceff'),
    'teal': ('#143d36', '#9be8c8'), 'emerald': ('#143d36', '#9be8c8'), 'green': ('#143d36', '#9be8c8'),
    'amber': ('#42341c', '#f6d68b'), 'yellow': ('#42341c', '#f6d68b'), 'orange': ('#42341c', '#f6d68b'),
    'red': ('#462635', '#ffb4bf'), 'rose': ('#462635', '#ffb4bf'),
    'purple': ('#352647', '#ddc2ff'), 'violet': ('#352647', '#ddc2ff'),
}
rules = []
for token in sorted(counts):
    match = re.fullmatch(r'(hover:)?(bg|text|border)-(\w+)-(\d+)(/\d+)?', token)
    hover, kind, family, shade, opacity = match.groups()
    shade = int(shade)
    bg, fg = palette[family]
    value = None
    if kind == 'bg' and shade <= 200:
        value = 'var(--surface-hover)' if hover and family in {'neutral', 'gray', 'slate'} else bg
    elif kind == 'text' and shade >= 400:
        value = 'var(--ink)' if family in {'neutral', 'gray', 'slate'} and shade >= 800 else fg
    elif kind == 'border' and shade <= 300:
        value = 'var(--line)'
    if value:
        escaped = token.replace(':', '\\:').replace('/', '\\/')
        selector = f'[data-theme="dark"] .{escaped}' + (':hover' if hover else '')
        # Keep white labels readable on solid buttons/toasts; only remap pale surfaces.
        rules.append(f'{selector} {{ {dict(bg="background-color", text="color", border="border-color")[kind]}: {value}; }}')

target = Path('.notification-fix/globals.css')
with target.open('a', encoding='utf-8') as file:
    file.write('\n/* Dark-mode coverage for legacy utility surfaces, status text and hover states.\n'
               'Pale translucent surfaces become opaque theme surfaces to keep text legible. */\n')
    file.write('\n'.join(rules))
    file.write('\n[data-theme="dark"] .workspace-content :where(input,select,textarea) { border-color: #58728f; }\n'
               '[data-theme="dark"] :where(a,button,input,select,textarea,summary):focus-visible { outline-color: #8ce7d6; }\n'
               '[data-theme="dark"] .workspace-platform :where(a,button,input,select,textarea,summary):focus-visible { outline-color: #c4bfff; }\n')
print(f'Scanned {len(list(root.rglob("*.tsx")))} UI files; generated {len(rules)} exact utility rules.')
