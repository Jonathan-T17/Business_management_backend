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
 return <FormBuilderGuard><div className="space-y-5">{selected===null?<><h3 className="text-xl font-semibold">Prepare your working forms</h3><p className="text-sm">1. Choose complete forms from the library below. 2. Open each saved company form to review its fields, access and reviewer. 3. Publish when it is ready for employees. Saved drafts stay here until you publish them.</p><FormTemplateLibrary/><Button variant="outline" onClick={()=>setSelected("new")}>Create a custom form</Button><h3 className="text-lg font-semibold">Your saved company forms</h3>{query.isPending?<p role="status">Loading saved forms…</p>:query.isError?<p role="alert">Unable to load saved forms. <button className="underline" onClick={()=>query.refetch()}>Retry</button></p>:!query.data?.length?<p className="rounded-xl border border-dashed border-[var(--line)] p-5 text-sm text-[var(--muted)]">No forms saved yet. Choose forms above, then select “Save selected forms to company library”. They will appear here for review.</p>:<div className="grid gap-3 sm:grid-cols-2">{query.data?.map(form=><button type="button" key={form.id} onClick={()=>setSelected(form.id)} className="rounded-xl border p-4 text-left"><strong>{form.name}</strong><span className="mt-2 block text-sm">{{ DRAFT: "Ready for review", PUBLISHED: "Available to permitted employees", ARCHIVED: "Retired" }[form.lifecycle_status || form.status || "DRAFT"]} · Open form</span></button>)}</div>}</>:<><Button variant="outline" onClick={()=>{setSelected(null);void query.refetch();}}>Back to form library</Button><p className="sb-help">Save your current form before leaving this editor.</p>{selected==="new"?<CreateForm onCreated={setSelected}/>:<FormDetail key={selected} id={selected} onOpen={setSelected}/>}</>}</div></FormBuilderGuard>;
}

