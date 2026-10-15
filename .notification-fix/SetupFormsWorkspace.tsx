"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { CreateForm } from "@/components/forms/CreateForm";
import { FormDetail } from "@/components/forms/FormDetail";
import { FormBuilderGuard } from "@/components/forms/FormBuilderGuard";
import { Button } from "@/components/ui/Button";
import { FormTemplateLibrary } from "@/components/forms/FormTemplateLibrary";
export default function SetupFormsWorkspace(){
 const [selected,setSelected]=useState<string | null>(null);
 const query=useQuery({queryKey:["forms","setup-library"],queryFn:formsApi.builderTemplates});
 return <FormBuilderGuard><div className="space-y-5">{selected===null?<><h3 className="text-xl font-semibold">Prepare your working forms</h3><p className="text-sm">Choose a ready-made template and adjust its questions for your company. Save a draft, preview it, then publish. Your forms stay in this library.</p><FormTemplateLibrary/><Button variant="outline" onClick={()=>setSelected("new")}>Adjust one template or create your own form</Button><h3 className="text-lg font-semibold">Saved company forms — review and publish</h3>{query.isPending?<p role="status">Loading saved forms…</p>:query.isError?<p role="alert">Unable to load saved forms. <button className="underline" onClick={()=>query.refetch()}>Retry</button></p>:<div className="grid gap-3 sm:grid-cols-2">{query.data?.map(form=><button type="button" key={form.id} onClick={()=>setSelected(form.id)} className="rounded-xl border p-4 text-left"><strong>{form.name}</strong><span className="mt-2 block text-sm">{{ DRAFT: "Draft", PUBLISHED: "Published", ARCHIVED: "Archived" }[form.lifecycle_status || form.status || "DRAFT"]} · Open to review or edit</span></button>)}</div>}</>:<><Button variant="outline" onClick={()=>{setSelected(null);void query.refetch();}}>Back to form library</Button><p className="sb-help">Save your current form before leaving this editor.</p>{selected==="new"?<CreateForm onCreated={setSelected}/>:<FormDetail key={selected} id={selected} onOpen={setSelected}/>}</>}</div></FormBuilderGuard>;
}

