interface Draft { id: string }
interface FormTransport<T extends Draft> {
  createDraft(templateId: string, values: Record<string, unknown>): Promise<T>;
  update(id: string, values: Record<string, unknown>): Promise<T>;
  uploadAttachment(id: string, file: File): Promise<unknown>;
  submit(id: string): Promise<T>;
}

// Keep the draft recoverable and stop before submission if any file fails.
export async function saveFormWithFiles<T extends Draft>({transport, templateId, savedId, values, files, submit, onDraftSaved, onFileUploaded}: {
  transport: FormTransport<T>; templateId: string; savedId: string | null;
  values: Record<string, unknown>; files: File[]; submit: boolean;
  onDraftSaved: (id: string) => void; onFileUploaded: (file: File) => void;
}): Promise<T> {
  const draft = savedId ? await transport.update(savedId, values) : await transport.createDraft(templateId, values);
  onDraftSaved(draft.id);
  for (const file of files) {
    await transport.uploadAttachment(draft.id, file);
    onFileUploaded(file);
  }
  return submit ? transport.submit(draft.id) : draft;
}
