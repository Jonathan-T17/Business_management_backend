from pathlib import Path
path = Path('.notification-fix/FormDesigner.tsx')
text = path.read_text(encoding='utf-8-sig')
old = '<label>Internal question ID <span className="text-xs text-neutral-500">(for rules and integrations)</span><input className={input} required pattern="[a-zA-Z0-9_-]+" value={field.key} onChange={e=>change(index,{key:e.target.value})}/></label>'
new = '<details><summary className="cursor-pointer text-sm font-medium">Advanced question identifier</summary><label>Question identifier<input className={input} required pattern="[a-zA-Z0-9_-]+" value={field.key} onChange={e=>change(index,{key:e.target.value})}/></label></details>'
assert old in text
text = text.replace(old, new).replace('<label>Data classification<select', '<label>Answer privacy<select')
text = text.replace('<label>Category<select', '<label className="sm:col-span-2">Form instructions<textarea className={input} rows={3} value={value.description??""} onChange={e=>setValue({...value,description:e.target.value})}/></label><label>Category<select')
text = text.replace('<label className="flex gap-2 text-sm"><input type="checkbox" checked={field.required}', '<label className="block text-sm">Help for the person answering<input className={input} value={field.help_text??""} onChange={e=>change(index,{help_text:e.target.value})}/></label><label className="flex gap-2 text-sm"><input type="checkbox" checked={field.required}')
text = text.replace('>{role}</label>', '>{friendly(role)}</label>')
path.write_text(text, encoding='utf-8')
