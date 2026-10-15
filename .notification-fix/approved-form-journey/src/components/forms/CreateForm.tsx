"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { FormDesigner } from "@/components/forms/FormDesigner";
import { FormTemplateLibrary } from "@/components/forms/FormTemplateLibrary";
import { Button } from "@/components/ui/Button";
import { normalizeApiError } from "@/utils/apiError";
import PageHeader from "@/components/ui/PageHeader";
import type { FormTemplatePayload } from "@/types/forms";
export function CreateForm({onCreated}:{onCreated?:(id:string)=>void}){
 const router=useRouter(); const qc=useQueryClient();
 const [starter,setStarter]=useState<FormTemplatePayload | null>(null);
 const create=useMutation({mutationFn:(payload:FormTemplatePayload)=>formsApi.createTemplate(payload),onSuccess:async template=>{await qc.invalidateQueries({queryKey:["forms"]});if(onCreated)onCreated(template.id);else router.replace(`/settings/forms/${template.id}`);}});
 const error=create.error?normalizeApiError(create.error):null;
 return <div className="mx-auto max-w-4xl space-y-6"><PageHeader title="Prepare a company form" description="Choose a complete template, adjust its fields and access, then save a draft to review before publishing."/>
 <Link href="/settings/forms" className="sb-text-link">← Saved company forms</Link>
 <ol className="grid gap-3 rounded-xl border p-4 text-sm sm:grid-cols-4"><li>1. Choose a template</li><li>2. Adjust fields and access</li><li>3. Save and preview</li><li>4. Publish when ready</li></ol>
 {starter===null?<><FormTemplateLibrary onChoose={form=>setStarter({...form,starter_code:form.code,code:`${form.code}-${crypto.randomUUID().slice(0,8)}`})}/><section className="sb-context-note"><div><h2 className="font-semibold">Need something different?</h2><p className="mt-1 text-sm text-[var(--muted)]">Create your own form when the ready-made fields do not fit your work.</p><Button variant="outline" onClick={()=>setStarter({name:"",code:"",category:"CUSTOM",allow_drafts:true,audience_roles:[],fields:[]})}>Create your own form</Button></div></section></>:<>
 <p className="sb-notice">Adjusting <strong>{starter.name || "a custom form"}</strong>. This becomes a private company form. Other companies cannot see your changes.</p>
 {error&&<p role="alert" className="sb-notice">{Object.values(error.fields).join(" ")||error.message}</p>}
 <FormDesigner initial={starter} pending={create.isPending} onSave={payload=>create.mutate(payload)}/></>}
 </div>;
}
