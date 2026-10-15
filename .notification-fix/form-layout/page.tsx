"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { DynamicForm, isFieldVisible } from "@/components/forms/DynamicForm";
import { Button } from "@/components/ui/Button";
import { ClipboardList } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { normalizeApiError } from "@/utils/apiError";
import { FORM_TEMPLATE_ACTIONS, hasAllowedAction } from "@/utils/allowedActions";

export default function StartFormPage() {
  const templateId = String(useParams().templateId); const router = useRouter();
  const user = useAuthStore(state=>state.user);
  const [openedAt] = useState(()=>Date.now());
  const [changed, setChanged] = useState<Record<string, unknown>>({});
  const [errors,setErrors] = useState<Record<string,string>>({});
  const [savedId,setSavedId] = useState<string|null>(null);
  const {data:template,isLoading} = useQuery({queryKey:["forms","template",templateId,user?.id],queryFn:()=>formsApi.template(templateId)});
  const canStart = Boolean(template && (template.lifecycle_status ?? template.status)==="PUBLISHED" && template.is_active!==false && hasAllowedAction(template.allowed_actions,FORM_TEMPLATE_ACTIONS.START));
  const connected = ["material-dispatch","material-receipt","material-return"].includes(template?.source_starter || "");
  const defaults = useQuery({queryKey:["forms","initial-values",templateId,user?.id,openedAt],queryFn:()=>formsApi.initialValues(templateId),enabled:canStart&&!connected,refetchOnWindowFocus:false,staleTime:Infinity});
  const values = useMemo(()=>({...defaults.data?.values,...changed}),[defaults.data,changed]);
  const action = useMutation({mutationFn:async (submit:boolean)=>{
    const draft = savedId ? await formsApi.update(savedId,values) : await formsApi.createDraft(templateId,values);
    setSavedId(draft.id);
    return submit ? formsApi.submit(draft.id) : draft;
  },onSuccess:result=>router.replace(`/forms/submissions/${result.id}`)});
  if(isLoading) return <p role="status">Opening your form…</p>;
  if(!template||!canStart) return <p role="alert" className="sb-notice">This form is not available for new entries. <Link href="/forms" className="underline">Back to company forms</Link></p>;
  if(connected) return <section className="sb-workspace-panel space-y-4"><h1 className="text-xl font-semibold">{template.name}</h1><p>Open the approved material request to record this action. Its reference and quantities will stay connected.</p><Link className="sb-action-link" href="/materials">Open materials and deliveries →</Link></section>;
  const send=(submit:boolean)=>{
    const missing:Record<string,string>={};
    if(submit) for(const field of template.fields) if(isFieldVisible(field,values)&&field.required&&(values[field.key]===undefined||values[field.key]===null||values[field.key]===""||Array.isArray(values[field.key])&&!(values[field.key] as unknown[]).length)) missing[field.key]="Please complete this required field.";
    setErrors(missing); if(!Object.keys(missing).length) action.mutate(submit);
  };
  const error=action.error?normalizeApiError(action.error):null;
  const collection=template.category==="COLLECTION";
  return <div className="mx-auto max-w-3xl space-y-4">
    <Link href="/forms" className="sb-text-link">← Company forms</Link>
    <section className="overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)] shadow-sm">
      <header className="flex items-center gap-4 bg-[#256b3c] px-5 py-6 text-white sm:px-8">
        <ClipboardList className="h-8 w-8 shrink-0" aria-hidden="true" />
        <h1 className="text-2xl font-bold leading-tight sm:text-3xl">{template.name}</h1>
      </header>
      <div className="px-5 py-4 sm:px-8">
        <p className="text-xs text-[var(--muted)]">Fields marked * are required.</p>
        {defaults.isPending?<p role="status" className="py-5">Preparing your automatic details…</p>:defaults.isError?<p role="alert" className="sb-notice">Unable to prepare your automatic details. <button type="button" className="underline" onClick={()=>defaults.refetch()}>Try again</button></p>:<DynamicForm template={template} values={values} errors={errors} disabled={action.isPending} onChange={(key,value)=>{setChanged(previous=>({...previous,[key]:value}));setErrors(previous=>({...previous,[key]:""}));}}/>}
        {template.review_preview&&<div className="border-t border-[var(--line)] py-4"><details><summary className="cursor-pointer text-sm font-medium">Who reviews this form?</summary><p className="mt-2 text-sm text-[var(--muted)]">{template.review_preview.description}</p><ol className="mt-2">{template.review_preview.steps.map((step,index)=><li key={index} className="text-sm">{index+1}. {step.destination}</li>)}</ol></details>{template.review_preview.warnings.map(warning=><p key={warning} className="sb-notice mt-3">{warning}</p>)}</div>}
        {Object.values(errors).some(Boolean)&&<p role="alert" className="sb-notice">Complete the required fields marked above before submitting.</p>}
        {error&&<p role="alert" className="sb-notice">{Object.values(error.fields).join(" ")||error.message}{savedId&&" Your draft is saved; you can correct it and try again."}</p>}
        <div className="flex flex-col-reverse items-stretch justify-center gap-3 border-t border-[var(--line)] py-6 sm:flex-row sm:items-center">{template.allow_drafts&&<Button variant="outline" loading={action.isPending} disabled={!defaults.data} onClick={()=>send(false)}>Save draft</Button>}<Button className="min-h-12 sm:min-w-56" loading={action.isPending} disabled={!defaults.data} onClick={()=>send(true)}>{collection?"Submit collection":"Submit form"}</Button></div>
      </div>
    </section>
  </div>;
}
