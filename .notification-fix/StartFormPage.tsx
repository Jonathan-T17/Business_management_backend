"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { DynamicForm } from "@/components/forms/DynamicForm";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { FORM_TEMPLATE_ACTIONS, hasAllowedAction } from "@/utils/allowedActions";

function statusOf(template: { status?: string; lifecycle_status?: string }) { return template.lifecycle_status ?? template.status ?? "DRAFT"; }
export default function StartFormPage() {
  const templateId = String(useParams().templateId); const router = useRouter();
  const [values, setValues] = useState<Record<string, unknown>>({}); const [errors, setErrors] = useState<Record<string, string>>({});
  const { data: template, isLoading } = useQuery({ queryKey: ["forms", "template", templateId], queryFn: () => formsApi.template(templateId), enabled: Boolean(templateId) });
  const canStart = useMemo(() => Boolean(template && statusOf(template) === "PUBLISHED" && template.is_active !== false && (!template.allowed_actions || hasAllowedAction(template.allowed_actions, FORM_TEMPLATE_ACTIONS.START))), [template]);
  const create = useMutation({ mutationFn: () => formsApi.createDraft(templateId, values), onSuccess: (submission) => router.replace(`/forms/submissions/${submission.id}`) });
  if (isLoading) return <div className="h-56 animate-pulse rounded-lg bg-[var(--surface)]" />;
  if (!template || !canStart) return <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-amber-900">This form is not currently available for new submissions.</div>;
  if (["material-dispatch","material-receipt","material-return"].includes(template.source_starter??"")) return <div className="sb-workspace-panel space-y-4"><h1 className="text-xl font-semibold">{template.name}</h1><p>Open the approved material request to record this action. Its reference and quantities will stay connected.</p><Link className="sb-action-link" href="/materials">Open materials and deliveries →</Link></div>;
  function save() { create.mutate(); }
  return <div className="mx-auto max-w-2xl space-y-6"><PageHeader title={template.name} description={`Complete the questions below. Save a draft to review your answers before submitting. Form version ${template.version}.`} />{template.review_preview&&<section className="sb-workspace-panel space-y-3"><h2 className="font-semibold">Where this form goes</h2><p className="text-sm text-[var(--muted)]">{template.review_preview.description}</p><ol className="space-y-2">{template.review_preview.steps.map((step,index)=><li key={index} className="text-sm">{index+1}. {step.destination}</li>)}</ol>{template.review_preview.warnings.map(warning=><p key={warning} className="sb-notice text-sm">{warning}</p>)}</section>}<section className="sb-workspace-panel"><DynamicForm template={template} values={values} errors={errors} onChange={(key, value) => { setValues((current) => ({ ...current, [key]: value })); setErrors((current) => ({ ...current, [key]: "" })); }} /></section>{create.isError && <p className="text-sm text-red-600">We couldn’t save your draft. Please try again. If this continues, contact your company administrator.</p>}<Button loading={create.isPending} onClick={save}>Save draft</Button></div>;
}

