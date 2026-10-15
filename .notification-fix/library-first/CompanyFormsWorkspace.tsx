"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { useAuthStore } from "@/store/authStore";
import { CAPABILITIES, hasCapability } from "@/utils/capabilities";
import { formatEnumLabel } from "@/utils/format";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { FormTemplateLibrary } from "./FormTemplateLibrary";
import { FormDetail } from "./FormDetail";
import { FormsSubmissions } from "./FormsSubmissions";

export function CompanyFormsWorkspace() {
 const user=useAuthStore(state=>state.user);
 const canCreate=Boolean(user&&!user.awaiting_position&&hasCapability(user.capabilities,CAPABILITIES.MANAGE_FORM_TEMPLATES));
 const [tab,setTab]=useState<"company"|"library">(canCreate?"library":"company");
 const [opened,setOpened]=useState<string|null>(null);
 const [entries,setEntries]=useState(false);
 const [search,setSearch]=useState("");
 const [showRetired,setShowRetired]=useState(false);
 const query=useQuery({queryKey:["forms","company-workspace",user?.company,user?.id],queryFn:formsApi.builderTemplates});
 if(entries)return <FormsSubmissions onBack={()=>setEntries(false)}/>;
 if(opened)return <FormDetail key={opened} id={opened} onOpen={setOpened} onBack={()=>setOpened(null)}/>;
 const visible=(query.data??[]).filter(form=>(showRetired||form.lifecycle_status!=="ARCHIVED")&&`${form.name} ${form.description??""}`.toLowerCase().includes(search.toLowerCase()));
 return <div className="space-y-5"><PageHeader title="Forms" description="Choose the forms your company needs from the library." action={<Button variant="outline" onClick={()=>setEntries(true)}>Submissions</Button>}/>
 <div role="tablist" aria-label="Forms workspace" onKeyDown={event=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(event.key)&&canCreate){event.preventDefault();const next=event.key==="Home"?"library":event.key==="End"?"company":tab==="company"?"library":"company";setTab(next);event.currentTarget.querySelector<HTMLButtonElement>(next==="company"?"#company-forms-tab":"#library-forms-tab")?.focus();}}} className="flex flex-wrap gap-2 border-b border-[var(--line)] pb-3">{canCreate&&<Button role="tab" id="library-forms-tab" aria-controls="forms-panel" aria-selected={tab==="library"} variant={tab==="library"?"primary":"outline"} onClick={()=>setTab("library")}>Form library</Button>}<Button role="tab" id="company-forms-tab" aria-controls="forms-panel" aria-selected={tab==="company"} variant={tab==="company"?"primary":"outline"} onClick={()=>setTab("company")}>Chosen company forms</Button></div>
 <section role="tabpanel" id="forms-panel" aria-labelledby={tab==="company"?"company-forms-tab":"library-forms-tab"}>
 {tab==="library"?<FormTemplateLibrary onOpen={id=>{setTab("company");setOpened(id);}} onSaved={()=>{setSearch("");setTab("company");}}/>:<div className="space-y-5">
 <div className="flex flex-wrap items-end justify-between gap-3"><label className="w-full text-sm font-medium sm:max-w-sm">Find a company form<input className="mt-1 w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search by form name"/></label><details className="rounded-lg border border-[var(--line)] p-3 text-sm"><summary className="cursor-pointer font-medium">More options</summary><div className="mt-3 space-y-3">{canCreate&&<Link href="/settings/forms/new" className="sb-text-link">Create a custom form</Link>}<label className="flex items-center gap-2"><input type="checkbox" checked={showRetired} onChange={e=>setShowRetired(e.target.checked)}/>Show retired versions</label></div></details></div>
 {query.isPending?<p role="status">Loading company forms…</p>:query.isError?<p role="alert">Unable to load forms. <button className="underline" onClick={()=>query.refetch()}>Try again</button></p>:!visible.length?<div className="rounded-xl border border-dashed p-6"><p>{search?"No matching forms.":"Your company has not chosen any forms yet."}</p>{!search&&canCreate&&<Button className="mt-3" onClick={()=>setTab("library")}>Choose from the library</Button>}</div>:<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{visible.map(form=><article key={form.id} className="sb-form-choice"><div className="flex items-center justify-between gap-3"><p className="sb-eyebrow">{formatEnumLabel(form.category)}</p><span className="sb-soft-label">{form.lifecycle_status==="PUBLISHED"?"Published":form.lifecycle_status==="ARCHIVED"?"Retired":"Draft"}</span></div><h2 className="mt-3 text-lg font-semibold">{form.name}</h2>{form.description&&<p className="mt-2 line-clamp-2 text-sm text-[var(--muted)]">{form.description}</p>}{form.library_update?.available&&<p className="mt-3 text-xs text-[var(--accent-text)]">Template update available</p>}<Button variant="outline" className="mt-auto self-start pt-2" onClick={()=>setOpened(form.id)}>Open form →</Button></article>)}</div>}
 </div>}
 </section></div>;
}
