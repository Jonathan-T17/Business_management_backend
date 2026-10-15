from pathlib import Path
p=Path('.notification-fix/simple-forms/src/components/forms/FormDetail.tsx');s=p.read_text(encoding='utf-8');s=s.replace('<section className="sb-workspace-panel space-y-3"><h2 className="font-semibold">An updated library template is available</h2>','<details className="sb-workspace-panel space-y-3"><summary className="cursor-pointer font-semibold">Template update available</summary>')
s=s.replace('Your company form stays unchanged until you review and publish an update. Custom fields are kept. Existing submissions keep their original form.','Review an updated draft before publishing. Your custom fields and previous entries are kept.')
s=s.replace(' existing fields will be preserved. Review the full draft and remove any duplicate fields before publishing.',' existing fields kept. Check for duplicate fields before publishing.')
s=s.replace('Prepare updated draft for review</Button></section>','Prepare updated draft</Button></details>')
p.write_text(s,encoding='utf-8')
