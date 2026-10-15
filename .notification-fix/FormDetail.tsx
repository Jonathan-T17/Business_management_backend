"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation,useQuery,useQueryClient } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { FormDesigner } from "@/components/forms/FormDesigner";
import { FormReviewRoute } from "@/components/forms/FormReviewRoute";
import { DynamicForm } from "@/components/forms/DynamicForm";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { normalizeApiError } from "@/utils/apiError";
import type { FormTemplatePayload } from "@/types/forms";
export function FormDetail({id,onOpen}:{id:string;onOpen?:(id:string)=>void}){
 const router=useRouter();const qc=useQueryClient();const [editing,setEditing]=useState(false);const [copyName,setCopyName]=useState("");const [copyCode,setCopyCode]=useState("");
 const {data:template,isLoading}=useQuery({queryKey:["forms","template",id],queryFn:()=>formsApi.template(id)});
 const refresh=async()=>{await qc.invalidateQueries({queryKey:["forms"]});setEditing(false);};
 const publish=useMutation({mutationFn:()=>formsApi.publishTemplate(id),onSuccess:refresh});
 const archive=useMutation({mutationFn:()=>formsApi.archiveTemplate(id),onSuccess:refresh});
 const save=useMutation({mutationFn:(payload:FormTemplatePayload)=>formsApi.updateTemplate(id,payload),onSuccess:async next=>{await refresh();if(onOpen)onOpen(next.id);else router.replace(`/settings/forms/${next.id}`);}});
 const copy=useMutation({mutationFn:()=>formsApi.copyTemplate(id,copyName,copyCode),onSuccess:async next=>{await refresh();if(onOpen)onOpen(next.id);else router.push(`/settings/forms/${next.id}`);}});
 if(isLoading)return <div className="h-48 animate-pulse bg-neutral-100"/>;
 if(!template)return <p role="alert">Unable to load this form.</p>;
 const allowed=template.allowed_actions??[];const raw=publish.error||archive.error||save.error||copy.error;const error=raw?normalizeApiError(raw):null;
 return <div className="mx-auto max-w-4xl space-y-6"><PageHeader title={template.name} description={`${template.lifecycle_status} - Version ${template.version}`}/>{template.lifecycle_status!=="DRAFT"&&<p className="rounded-xl bg-blue-50 p-4 text-sm text-blue-900">This version is frozen. Changes create a separate draft revision. Existing submissions retain their original schema.</p>}{error&&<p role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{Object.values(error.fields).join(" ")||error.message}</p>}
 <section className="rounded-xl border p-4 text-sm"><Link className="font-semibold underline" href="/settings/forms">← All saved company forms</Link><p className="mt-3">{template.lifecycle_status==="DRAFT"?"Draft saved. Review the questions below and use Edit draft to check who may submit and whether approval is needed. Publish only when the form meets your company requirements.":"This form is saved in your company library. Eligible users can use published versions; answers are stored separately as submissions."}</p></section>
 {template.review_preview&&<section className="sb-workspace-panel space-y-3"><h2 className="font-semibold">Where this form goes</h2><p className="text-sm text-[var(--muted)]">{template.review_preview.description}</p><ol className="space-y-2">{template.review_preview.steps.map((step,index)=><li key={index} className="text-sm">{index+1}. {step.destination}</li>)}</ol>{template.review_preview.warnings.map(warning=><p key={warning} className="sb-notice text-sm">{warning}</p>)}</section>}
 {editing?<FormDesigner key={id} initial={template} revision pending={save.isPending} onSave={payload=>save.mutate(payload)}/>:<section className="rounded-xl border bg-white p-5"><h2 className="mb-4 font-semibold">Preview</h2><DynamicForm template={template} values={{}} disabled onChange={()=>undefined}/></section>}
 <div className="flex flex-wrap gap-3">{allowed.includes("UPDATE")&&<Button variant="outline" onClick={()=>setEditing(!editing)}>{editing?"Close editor":template.lifecycle_status==="DRAFT"?"Edit draft":"Create revision"}</Button>}{!editing&&allowed.includes("PUBLISH")&&<Button loading={publish.isPending} onClick={()=>publish.mutate()}>Publish version</Button>}{allowed.includes("ARCHIVE")&&<Button variant="outline" loading={archive.isPending} onClick={()=>archive.mutate()}>Retire version</Button>}</div>
 {!editing&&["material-dispatch","material-receipt","material-return"].includes(template.source_starter??"")&&<p className="sb-notice text-sm">These confirmations stay connected to the approved request. In Edit draft, choose the positions or people who may record this action.</p>}
 {!editing&&!["material-dispatch","material-receipt","material-return"].includes(template.source_starter??"")&&allowed.includes("UPDATE")&&<FormReviewRoute id={id} onSaved={async nextId=>{await refresh();if(onOpen)onOpen(nextId);else router.replace(`/settings/forms/${nextId}`);}}/>}
 {allowed.includes("COPY")&&<form className="space-y-3 rounded-xl border bg-white p-5" onSubmit={e=>{e.preventDefault();copy.mutate();}}><h2 className="font-semibold">Copy as a new form</h2><p className="text-sm text-neutral-600">Copies the questions only. Audience restrictions and approval assignments must be configured for the new form.</p><label className="block">New name<input className="mt-1 block w-full rounded-lg border p-2" required value={copyName} onChange={e=>setCopyName(e.target.value)}/></label><label className="block">New code<input className="mt-1 block w-full rounded-lg border p-2" required pattern="[a-zA-Z0-9_-]+" value={copyCode} onChange={e=>setCopyCode(e.target.value)}/></label><Button type="submit" loading={copy.isPending}>Create company copy</Button></form>}
 </div>;
}
