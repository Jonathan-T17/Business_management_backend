"use client";

import { useState } from "react";
import { Paperclip } from "lucide-react";
import { Button } from "@/components/ui/Button";

export const supportingFileTypes = ".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.csv,.docx,.xlsx,.pptx";
export function supportingFileError(file: File): string | null {
  if (!file.size) return `${file.name} is empty. Choose a file with content.`;
  if (file.size > 25 * 1024 * 1024) return `${file.name} is larger than 25 MB.`;
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  return supportingFileTypes.split(",").includes(extension) ? null : `${file.name}: choose a PDF, image, text or Office document.`;
}

export function PendingFormFiles({files, onChange, disabled}: {files: File[]; onChange: (files: File[]) => void; disabled: boolean}) {
  const [error, setError] = useState("");
  return <section className="border-t border-[var(--line)] py-4" aria-label="Receipts and supporting files">
    <h2 className="flex items-center gap-2 font-semibold"><Paperclip size={18} aria-hidden="true"/>Receipts & supporting files <span className="text-xs font-normal text-[var(--muted)]">Optional</span></h2>
    <p id="pending-file-help" className="mt-1 text-sm text-[var(--muted)]">Add receipts, photos or documents. Files upload when you save or submit. Up to 25 MB each.</p>
    <label className="mt-3 block text-sm font-medium">Choose files<input type="file" multiple accept={supportingFileTypes} aria-describedby="pending-file-help" disabled={disabled} className="mt-2 block w-full min-w-0 text-sm file:mr-3 file:rounded-lg file:border file:border-[var(--line)] file:bg-[var(--surface-soft)] file:px-3 file:py-2 file:text-[var(--ink)]" onChange={event => {
      const selected = Array.from(event.target.files ?? []);
      const problems = selected.map(supportingFileError).filter(Boolean);
      setError(problems.join(" "));
      const valid = selected.filter(file => !supportingFileError(file));
      const combined = [...files];
      for (const file of valid) if (!combined.some(existing => existing.name === file.name && existing.size === file.size && existing.lastModified === file.lastModified)) combined.push(file);
      onChange(combined); event.target.value = "";
    }}/></label>
    {!!files.length && <ul className="mt-3 space-y-2" aria-label="Files waiting to upload">{files.map((file, index) => <li key={`${file.name}-${index}`} className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--line)] p-3"><div className="min-w-0 flex-1"><p className="break-words text-sm font-medium">{file.name}</p><p className="text-xs text-[var(--muted)]">{Math.ceil(file.size / 1024)} KB · Waiting to upload</p></div><Button size="sm" variant="outline" aria-label={`Remove ${file.name} from pending uploads`} disabled={disabled} onClick={() => onChange(files.filter((_, position) => position !== index))}>Remove</Button></li>)}</ul>}
    {error && <p role="alert" className="sb-notice mt-3">{error}</p>}
  </section>;
}
