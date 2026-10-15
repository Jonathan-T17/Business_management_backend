from pathlib import Path
root=Path(r'C:\Users\1213\Desktop\Jonathan\business_management_frontend')
out=Path(r'C:\Users\1213\.codex\visualizations\2026\09\17\01a0aebf-e46f-7301-ae2c-f2074a76aefc\experience-foundation\reporting-browser-fixes')
path='src/components/forms/DynamicForm.tsx';s=(root/path).read_text(encoding='utf-8')
s=s.replace('import type { FormField', 'import { useId } from "react";\nimport type { FormField').replace('key={field.id}', 'key={field.key}')
s=s.replace('  const inputClass =', '''  const inputId = useId();
  const controlProps = { id: inputId, "aria-required": field.required, "aria-invalid": Boolean(error), "aria-describedby": [field.help_text ? `${inputId}-help` : "", error ? `${inputId}-error` : ""].filter(Boolean).join(" ") || undefined };
  const inputClass =''')
s=s.replace('border-neutral-300 bg-white', 'border-[var(--line)] bg-[var(--surface)]').replace('text-neutral-900','text-[var(--ink)]').replace('disabled:bg-neutral-100','disabled:bg-[var(--surface-soft)]').replace('text-neutral-500','text-[var(--muted)]')
s=s.replace('<label className="text-sm font-medium', '<label htmlFor={inputId} className="text-sm font-medium')
s=s.replace('<textarea className=', '<textarea {...controlProps} className=').replace('<select className=', '<select {...controlProps} className=')
s=s.replace('<input type="checkbox"', '<input {...controlProps} type="checkbox"')
s=s.replace('control = <input className=', 'control = <input {...controlProps} className=')
s=s.replace('<input className={inputClass} type="number"', '<input aria-label={`${field.label}: ${axis}`} aria-invalid={Boolean(error)} className={inputClass} type="number"')
s=s.replace('<p className="mt-1 text-xs text-[var(--muted)]">{field.help_text}', '<p id={`${inputId}-help`} className="mt-1 text-xs text-[var(--muted)]">{field.help_text}')
s=s.replace('<p className="mt-1 text-xs text-red-600">{error}', '<p id={`${inputId}-error`} role="alert" className="mt-1 text-xs text-red-600">{error}')
p=out/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
path='src/app/(dashboard)/forms/submissions/[submissionId]/page.tsx';s=(root/path).read_text(encoding='utf-8')
s=s.replace('import { useParams }', 'import Link from "next/link";\nimport { formatEnumLabel } from "@/utils/format";\nimport { normalizeApiError } from "@/utils/apiError";\nimport { useParams }')
s=s.replace('  const [values,', '  const [notice, setNotice] = useState("");\n  const [values,')
s=s.replace('  const save = useMutation', '''  async function refreshWork() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.forms.submission(submissionId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.reporting.obligations }),
      queryClient.invalidateQueries({ queryKey: ["workspace"] }),
      queryClient.invalidateQueries({ queryKey: ["analytics"] }),
    ]);
  }
  const save = useMutation''')
s=s.replace('onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.forms.submission(submissionId) }) });', 'onSuccess: async () => { await refreshWork(); setNotice("Draft saved. You can continue later or submit when ready."); } });',1)
s=s.replace('onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.forms.submission(submissionId) }) });', 'onSuccess: async () => { await refreshWork(); setNotice("Report submitted. You can check its progress in My reports."); } });',1)
s=s.replace('`${submission.status.replaceAll("_", " ")} \u00b7 schema version ${submission.template_version}`', '`${submission.status === "RETURNED" ? "Changes requested" : formatEnumLabel(submission.status)} \u00b7 Form version ${submission.template_version}`')
s=s.replace('    {submission.status === "RETURNED"', '''    <Link href="/reporting/obligations" className="sb-text-link">Back to my reports</Link>
    {notice && <p role="status" className="sb-context-note">{notice}</p>}
    {submission.status === "RETURNED"''')
s=s.replace('<section className="rounded-lg border border-neutral-200 bg-white p-5">', '<section className="sb-workspace-panel">')
s=s.replace('disabled={!canEdit}', 'disabled={!canEdit || save.isPending || submit.isPending}')
s=s.replace('onChange={(key, value) => { setValues', 'onChange={(key, value) => { setNotice(""); setValues')
s=s.replace('<p className="text-sm text-red-600">The operation was not accepted. Refresh the submission before trying again.</p>', '<p role="alert" className="text-sm text-red-600">{normalizeApiError(save.error || submit.error).message}</p>')
s=s.replace('loading={save.isPending} onClick=', 'loading={save.isPending} disabled={submit.isPending} onClick=')
s=s.replace('loading={submit.isPending} onClick=', 'loading={submit.isPending} disabled={save.isPending} onClick=')
p=out/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
