"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { DynamicForm, isFieldVisible } from "@/components/forms/DynamicForm";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
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
  const hasAutomatic = template.fields.some(field=>field.validation_rules?.default_source);
  const collection=template.category==="COLLECTION";
  return <div className="mx-auto max-w-3xl space-y-6"><PageHeader title={template.name} description={template.description || "Complete this company form, check your answers and submit when ready."}/>
    <Link href="/forms" className="sb-text-link">← Company forms</Link>
    <section className="sb-context-note"><p>{hasAutomatic ? "Automatic fields use your signed-in profile and company settings. Editable dates and locations can be changed when needed." : "Complete the fields prepared by your company and check your answers before submitting."} Opening this form does not save an entry.</p></section>
    {defaults.isPending?<p role="status">Preparing your automatic details…</p>:defaults.isError?<p role="alert" className="sb-notice">Unable to prepare your automatic details. <button type="button" className="underline" onClick={()=>defaults.refetch()}>Try again</button></p>:<section className="sb-workspace-panel"><DynamicForm template={template} values={values} errors={errors} disabled={action.isPending} onChange={(key,value)=>{setChanged(previous=>({...previous,[key]:value}));setErrors(previous=>({...previous,[key]:""}));}}/></section>}
    {template.review_preview&&<section className="sb-workspace-panel space-y-3"><h2 className="font-semibold">What happens after submission?</h2><p className="text-sm text-[var(--muted)]">{template.review_preview.description}</p><ol>{template.review_preview.steps.map((step,index)=><li key={index} className="text-sm">{index+1}. {step.destination}</li>)}</ol>{template.review_preview.warnings.map(warning=><p key={warning} className="sb-notice">{warning}</p>)}</section>}
    {Object.keys(errors).length>0&&<p role="alert" className="sb-notice">Complete the required fields marked above before submitting.</p>}
    {error&&<p role="alert" className="sb-notice">{Object.values(error.fields).join(" ")||error.message}{savedId&&" Your draft is saved; you can correct it and try again."}</p>}
    <div className="flex flex-wrap gap-3">{template.allow_drafts&&<Button variant="outline" loading={action.isPending} disabled={!defaults.data} onClick={()=>send(false)}>Save draft</Button>}<Button loading={action.isPending} disabled={!defaults.data} onClick={()=>send(true)}>{collection?"Submit collection":"Submit form"}</Button></div>
  </div>;
}
