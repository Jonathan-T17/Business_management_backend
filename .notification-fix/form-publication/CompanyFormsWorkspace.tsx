"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FileText, FolderOpen, Plus } from "lucide-react";
import { formsApi } from "@/api/formsApi";
import { useAuthStore } from "@/store/authStore";
import { CAPABILITIES, hasCapability } from "@/utils/capabilities";
import { formatEnumLabel } from "@/utils/format";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { FormTemplateLibrary } from "./FormTemplateLibrary";
import { FormDetail } from "./FormDetail";
import { FormsSubmissions } from "./FormsSubmissions";
export function CompanyFormsWorkspace() {
 const user=useAuthStore(state=>state.user);
 const canCreate=Boolean(user&&!user.awaiting_position&&hasCapability(user.capabilities,CAPABILITIES.MANAGE_FORM_TEMPLATES));
 const [selectedTab,setTab]=useState<"company"|"library"|null>(null);
 const [opened,setOpened]=useState<string|null>(null);
 const [entries,setEntries]=useState(false);
 const [search,setSearch]=useState("");
 const query=useQuery({queryKey:["forms","company-workspace",user?.company,user?.id],queryFn:formsApi.builderTemplates});
 const companyForms=(query.data??[]).filter(form=>form.lifecycle_status!=="ARCHIVED");
 const tab=selectedTab??(canCreate&&query.isSuccess&&!companyForms.length?"library":"company");
 if(entries)return <FormsSubmissions onBack={()=>setEntries(false)}/>;
 if(opened)return <FormDetail key={opened} id={opened} onOpen={setOpened} onBack={()=>setOpened(null)}/>;
 const visible=(query.data??[]).filter(form=>(form.lifecycle_status!=="ARCHIVED")&&`${form.name} ${form.description??""}`.toLowerCase().includes(search.toLowerCase()));
 return <div className="space-y-5"><PageHeader title="Forms" description="Find a company form, start an entry or return to your saved work." action={<Button variant="outline" iconLeft={<FolderOpen size={18}/>} onClick={()=>setEntries(true)}>Saved entries</Button>}/>
 <div role="tablist" aria-label="Forms workspace" onKeyDown={event=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(event.key)&&canCreate){event.preventDefault();const next=event.key==="Home"?"company":event.key==="End"?"library":tab==="company"?"library":"company";setTab(next);event.currentTarget.querySelector<HTMLButtonElement>(next==="company"?"#company-forms-tab":"#library-forms-tab")?.focus();}}} className="flex flex-wrap gap-2 border-b border-[var(--line)] pb-3"><Button role="tab" id="company-forms-tab" aria-controls="forms-panel" aria-selected={tab==="company"} tabIndex={tab==="company"?0:-1} variant={tab==="company"?"primary":"outline"} onClick={()=>setTab("company")}>Company forms</Button>{canCreate&&<Button role="tab" id="library-forms-tab" aria-controls="forms-panel" aria-selected={tab==="library"} tabIndex={tab==="library"?0:-1} variant={tab==="library"?"primary":"outline"} onClick={()=>setTab("library")}>Form library</Button>}</div>
 <section role="tabpanel" id="forms-panel" aria-labelledby={tab==="company"?"company-forms-tab":"library-forms-tab"}>
 {tab==="library"?<FormTemplateLibrary onOpen={id=>{setTab("company");setOpened(id);}} onSaved={()=>{setSearch("");setTab("company");}}/>:<div className="space-y-4">
 <div className="flex flex-wrap items-end justify-between gap-3"><label className="w-full text-sm font-medium sm:max-w-sm">Find a company form<input className="mt-1 w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search by form name"/></label>{canCreate&&<Link href="/settings/forms/new" className="sb-action-link"><Plus size={18}/>Create a custom form</Link>}</div>
 {query.isPending?<p role="status">Loading company forms…</p>:query.isError?<ErrorState title="Unable to load company forms" onRetry={()=>void query.refetch()}/>:!visible.length?<EmptyState icon={<FileText size={28}/>} title={search?"No matching forms":"Choose the forms your company needs"} description={search?"Try another form name or clear your search.":canCreate?"Preview complete forms in the library, add them to your company, then review and publish them.":"Your company forms will appear here when they are ready for you to use."} action={search?<Button variant="outline" onClick={()=>setSearch("")}>Clear search</Button>:canCreate&&<Button onClick={()=>setTab("library")}>Open form library</Button>}/>:<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{visible.map(form=><article key={form.id} className="sb-form-choice"><div className="flex items-center justify-between gap-3"><p className="sb-eyebrow">{formatEnumLabel(form.category)}</p><span className="sb-soft-label">{form.lifecycle_status==="PUBLISHED"?"Ready to use":"Not available yet"}</span></div><h2 className="mt-3 text-lg font-semibold">{form.name}</h2>{form.description&&<p className="mt-2 line-clamp-2 text-sm text-[var(--muted)]">{form.description}</p>}{form.library_update?.available&&<p className="mt-3 text-xs text-[var(--accent-text)]">Library update available</p>}<Button variant="outline" className="mt-auto self-start" onClick={()=>setOpened(form.id)}>{form.lifecycle_status==="DRAFT"?"Review & make available":"Open form"} →</Button></article>)}</div>}
 </div>}
 </section></div>;
}