"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { formatEnumLabel } from "@/utils/format";
import { normalizeApiError } from "@/utils/apiError";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { FormAttachments } from "@/components/forms/FormAttachments";
import { MaterialJourneyPanel } from "@/components/forms/MaterialJourneyPanel";
import { DynamicForm, isFieldVisible } from "@/components/forms/DynamicForm";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { queryKeys } from "@/lib/queryKeys";
import { MobileActionBar } from "@/components/mobile/MobileActionBar";
import { FORM_SUBMISSION_ACTIONS, hasAllowedAction } from "@/utils/allowedActions";

export default function SubmissionPage() {
  const submissionId = String(useParams().submissionId); const queryClient = useQueryClient();
  const { data: submission, isLoading } = useQuery({ queryKey: queryKeys.forms.submission(submissionId), queryFn: () => formsApi.submission(submissionId) });
  const [notice, setNotice] = useState("");
  const [values, setValues] = useState<Record<string, unknown> | null>(null); const [errors, setErrors] = useState<Record<string, string>>({});
  // Reset local draft state whenever the fetched submission changes.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setValues(null); setErrors({}); }, [submission?.updated_at, submission?.status]);
  const legacyEditable = submission?.status === "DRAFT" || submission?.status === "RETURNED";
  const canEdit = Boolean(submission && (submission.allowed_actions ? hasAllowedAction(submission.allowed_actions, FORM_SUBMISSION_ACTIONS.EDIT) || hasAllowedAction(submission.allowed_actions, FORM_SUBMISSION_ACTIONS.SAVE) : legacyEditable));
  const canSubmit = Boolean(submission && (submission.allowed_actions ? hasAllowedAction(submission.allowed_actions, FORM_SUBMISSION_ACTIONS.SUBMIT) : legacyEditable));
  async function refreshWork() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.forms.submission(submissionId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.reporting.obligations }),
      queryClient.invalidateQueries({ queryKey: ["workspace"] }),
      queryClient.invalidateQueries({ queryKey: ["analytics"] }),
    ]);
  }
  const save = useMutation({ mutationFn: () => formsApi.update(submissionId, values ?? submission?.values ?? {}), onSuccess: async () => { await refreshWork(); setNotice("Draft saved. You can continue later or submit when ready."); } });
  const submit = useMutation({ mutationFn: async () => { if (values !== null) await formsApi.update(submissionId, values); return formsApi.submit(submissionId); }, onSuccess: async () => { await refreshWork(); setNotice("Report submitted. You can check its progress in My reports."); } });
  if (isLoading) return <div className="h-56 animate-pulse rounded-lg bg-neutral-200" />;
  if (!submission) return <div className="rounded-lg bg-red-50 p-5 text-red-700">Unable to load submission.</div>;

  const currentValues = values ?? submission.values ?? {};
  const schemaFields = submission.schema_snapshot.fields ?? [];

  function submitForm() {
    const next: Record<string, string> = {};
    for (const field of schemaFields) {
      if (!isFieldVisible(field, currentValues)) continue;
      const value = currentValues[field.key];
      if (field.required && (value === undefined || value === null || value === "" || (Array.isArray(value) && value.length === 0))) {
        next[field.key] = `${field.label} is required.`;
      }
    }
    setErrors(next);
    if (Object.keys(next).length === 0) submit.mutate();
  }

  return <div className="mx-auto max-w-2xl space-y-6"><PageHeader title={submission.title?.trim() || submission.schema_snapshot.name || submission.template?.name || "Form submission"} description={`${submission.status === "RETURNED" ? "Changes requested" : formatEnumLabel(submission.status)} · Form version ${submission.template_version}`} />
    <Link href="/reporting/obligations" className="sb-text-link">Back to my reports</Link>
    {notice && <p role="status" className="sb-context-note">{notice}</p>}
    {submission.status === "RETURNED" && <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><strong>Returned for correction</strong>{submission.return_note && <p className="mt-1">Reviewer note: {submission.return_note}</p>}</div>}
    <section className="sb-workspace-panel"><DynamicForm template={submission.schema_snapshot} values={currentValues} errors={errors} disabled={!canEdit || save.isPending || submit.isPending} onChange={(key, value) => { setNotice(""); setValues({ ...currentValues, [key]: value }); setErrors((current) => ({ ...current, [key]: "" })); }} /></section>
    <FormAttachments submissionId={submissionId} status={submission.status} />
    {submission.schema_snapshot.source_starter==='material-request'&&!['DRAFT','CANCELLED'].includes(submission.status)&&<MaterialJourneyPanel id={submissionId}/>}
    {(save.isError || submit.isError) && <p role="alert" className="text-sm text-red-600">{normalizeApiError(save.error || submit.error).message}</p>}
    {(canEdit || canSubmit) && <MobileActionBar>{canEdit && <Button className="flex-1" variant="outline" loading={save.isPending} disabled={submit.isPending} onClick={() => save.mutate()}>Save draft</Button>}{canSubmit && <Button className="flex-1" loading={submit.isPending} disabled={save.isPending} onClick={submitForm}>Submit form</Button>}</MobileActionBar>}
  </div>;
}
