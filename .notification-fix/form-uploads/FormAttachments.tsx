"use client";

import { useEffect, useId, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Paperclip } from "lucide-react";
import { formsApi } from "@/api/formsApi";
import { normalizeApiError } from "@/utils/apiError";
import { Button } from "@/components/ui/Button";
import { supportingFileError, supportingFileTypes } from "./PendingFormFiles";

export function FormAttachments({submissionId, status, disabled = false, onBusyChange}: {
  submissionId: string; status: string; disabled?: boolean; onBusyChange?: (busy: boolean) => void;
}) {
  const client = useQueryClient();
  const helpId = useId();
  const [validationError, setValidationError] = useState("");
  const [notice, setNotice] = useState("");
  const query = useQuery({queryKey: ["forms", "attachments", submissionId, status], queryFn: () => formsApi.attachments(submissionId)});
  const refresh = () => client.invalidateQueries({queryKey: ["forms", "attachments", submissionId]});
  const upload = useMutation({mutationFn: (file: File) => formsApi.uploadAttachment(submissionId, file), onSuccess: async () => {await refresh(); setNotice("File uploaded and saved with this entry.");}});
  const remove = useMutation({mutationFn: (id: string) => formsApi.removeAttachment(submissionId, id), onSuccess: async () => {await refresh(); setNotice("File removed from this entry.");}});
  const download = useMutation({mutationFn: async (file: {id: string; name: string}) => {
    const blob = await formsApi.downloadAttachment(submissionId, file.id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = file.name; document.body.appendChild(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }});
  const busy = upload.isPending || remove.isPending;
  useEffect(() => {onBusyChange?.(busy);}, [busy, onBusyChange]);
  useEffect(() => () => {onBusyChange?.(false);}, [onBusyChange]);
  const error = query.error || upload.error || remove.error || download.error;
  const errorDetails = error ? normalizeApiError(error) : null;
  return <section className="sb-workspace-panel space-y-3" aria-label="Saved supporting files">
    <h2 className="flex items-center gap-2 font-semibold"><Paperclip size={18} aria-hidden="true"/>Receipts & supporting files</h2>
    <p id={helpId} className="text-sm text-[var(--muted)]">{query.data?.can_upload ? "Add a receipt, photo or document before submitting. Up to 25 MB per file." : "Saved supporting files. Files are locked after submission."}</p>
    {query.isPending && <p role="status" className="text-sm text-[var(--muted)]">Loading saved files…</p>}
    {query.data?.restricted && <p className="text-sm text-[var(--muted)]">These files contain restricted information and are not available to your account.</p>}
    {query.isSuccess && !query.data.restricted && !query.data.files.length && <p className="text-sm text-[var(--muted)]">No supporting files added.</p>}
    {!!query.data?.files.length && <ul className="space-y-2" aria-label="Saved files">{query.data.files.map(file => <li key={file.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--line)] p-3"><div className="min-w-0 flex-1"><p className="break-words text-sm font-medium">{file.name}</p><p className="text-xs text-[var(--muted)]">{Math.ceil(file.size / 1024)} KB · Saved</p></div><Button size="sm" variant="outline" aria-label={`Download ${file.name}`} disabled={download.isPending} onClick={() => download.mutate(file)}>Download</Button>{query.data?.can_remove && <Button size="sm" variant="outline" aria-label={`Remove ${file.name}`} disabled={disabled || busy} onClick={() => {setNotice(""); remove.mutate(file.id);}}>Remove</Button>}</li>)}</ul>}
    {query.data?.can_upload && <label className="block text-sm font-medium">Add a supporting file<input type="file" aria-describedby={helpId} className="mt-2 block w-full min-w-0 text-sm file:mr-3 file:rounded-lg file:border file:border-[var(--line)] file:bg-[var(--surface-soft)] file:px-3 file:py-2 file:text-[var(--ink)]" accept={supportingFileTypes} disabled={disabled || busy} onChange={event => {
      const file = event.target.files?.[0]; event.target.value = "";
      if (!file) return;
      const problem = supportingFileError(file); setValidationError(problem ?? ""); setNotice("");
      upload.reset(); remove.reset(); download.reset();
      if (!problem) upload.mutate(file);
    }}/></label>}
    {busy && <p role="status" className="text-sm">{upload.isPending ? "Uploading file — wait before submitting…" : "Removing file…"}</p>}
    {notice && <p role="status" className="text-sm text-[var(--accent-text)]">{notice}</p>}
    {(error || validationError) && <div role="alert" className="sb-notice text-sm">{validationError || (errorDetails && (Object.values(errorDetails.fields).join(" ") || errorDetails.message))}{query.isError && <button type="button" className="ml-2 underline" onClick={() => void query.refetch()}>Try again</button>}</div>}
  </section>;
}
