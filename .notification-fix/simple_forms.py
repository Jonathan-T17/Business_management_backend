from pathlib import Path
src=Path('C:/Users/1213/Desktop/Jonathan/business_management_frontend');stage=Path('.notification-fix/simple-forms')
def put(p,s):
 f=stage/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s,encoding='utf-8')
def read(p):return (src/p).read_text(encoding='utf-8-sig')
put('src/components/forms/CompanyFormsWorkspace.tsx','''"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { useAuthStore } from "@/store/authStore";
import { workspaceAccess } from "@/utils/workspace";
import { formatEnumLabel } from "@/utils/format";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { FormTemplateLibrary } from "./FormTemplateLibrary";
import { FormDetail } from "./FormDetail";
import { FormsSubmissions } from "./FormsSubmissions";

export function CompanyFormsWorkspace() {
 const user=useAuthStore(state=>state.user);
 const access=workspaceAccess(user);
 const [tab,setTab]=useState<"company"|"library">("company");
 const [opened,setOpened]=useState<string|null>(null);
 const [entries,setEntries]=useState(false);
 const [search,setSearch]=useState("");
 const [showRetired,setShowRetired]=useState(false);
 const query=useQuery({queryKey:["forms","company-workspace",user?.company,user?.id],queryFn:formsApi.builderTemplates});
 if(entries)return <FormsSubmissions onBack={()=>setEntries(false)}/>;
 if(opened)return <FormDetail key={opened} id={opened} onOpen={setOpened} onBack={()=>setOpened(null)}/>;
 const visible=(query.data??[]).filter(form=>(showRetired||form.lifecycle_status!=="ARCHIVED")&&`${form.name} ${form.description??""}`.toLowerCase().includes(search.toLowerCase()));
 return <div className="space-y-5"><PageHeader title="Forms" description="Choose a company form or add one from the library." action={<Button variant="outline" onClick={()=>setEntries(true)}>Submissions</Button>}/>
 <div role="tablist" aria-label="Forms workspace" className="flex gap-2 border-b border-[var(--line)] pb-3"><Button role="tab" id="company-forms-tab" aria-controls="forms-panel" aria-selected={tab==="company"} variant={tab==="company"?"primary":"outline"} onClick={()=>setTab("company")}>Company forms</Button>{access.formManagement&&<Button role="tab" id="library-forms-tab" aria-controls="forms-panel" aria-selected={tab==="library"} variant={tab==="library"?"primary":"outline"} onClick={()=>setTab("library")}>Ready-made library</Button>}</div>
 <section role="tabpanel" id="forms-panel" aria-labelledby={tab==="company"?"company-forms-tab":"library-forms-tab"}>
 {tab==="library"?<FormTemplateLibrary onOpen={id=>{setTab("company");setOpened(id);}} onSaved={()=>setTab("company")}/>:<div className="space-y-5">
 <div className="flex flex-wrap items-end justify-between gap-3"><label className="w-full text-sm font-medium sm:max-w-sm">Find a company form<input className="mt-1 w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search by form name"/></label><details className="rounded-lg border border-[var(--line)] p-3 text-sm"><summary className="cursor-pointer font-medium">More options</summary><div className="mt-3 space-y-3">{access.formManagement&&<Link href="/settings/forms/new" className="sb-text-link">Create a custom form</Link>}<label className="flex items-center gap-2"><input type="checkbox" checked={showRetired} onChange={e=>setShowRetired(e.target.checked)}/>Show retired versions</label></div></details></div>
 {query.isPending?<p role="status">Loading company forms…</p>:query.isError?<p role="alert">Unable to load forms. <button className="underline" onClick={()=>query.refetch()}>Try again</button></p>:!visible.length?<div className="rounded-xl border border-dashed p-6"><p>{search?"No matching forms.":"No company forms yet."}</p>{!search&&access.formManagement&&<Button className="mt-3" onClick={()=>setTab("library")}>Choose from the library</Button>}</div>:<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{visible.map(form=><article key={form.id} className="sb-form-choice"><div className="flex items-center justify-between gap-3"><p className="sb-eyebrow">{formatEnumLabel(form.category)}</p><span className="sb-soft-label">{form.lifecycle_status==="PUBLISHED"?"Published":form.lifecycle_status==="ARCHIVED"?"Retired":"Draft"}</span></div><h2 className="mt-3 text-lg font-semibold">{form.name}</h2>{form.description&&<p className="mt-2 line-clamp-2 text-sm text-[var(--muted)]">{form.description}</p>}{form.library_update?.available&&<p className="mt-3 text-xs text-[var(--accent-text)]">Template update available</p>}<Button variant="outline" className="mt-auto self-start pt-2" onClick={()=>setOpened(form.id)}>Open form →</Button></article>)}</div>}
 </div>}
 </section></div>;
}
''')
put('src/components/forms/FormsSubmissions.tsx','''"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { useAuthStore } from "@/store/authStore";
import { CollectionPager } from "@/components/ui/CollectionPager";
import PageHeader from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { formatEnumLabel } from "@/utils/format";
export function FormsSubmissions({onBack}:{onBack:()=>void}){
 const [page,setPage]=useState(1);const user=useAuthStore(state=>state.user);
 const query=useQuery({queryKey:["forms","entries",user?.company,user?.id,page],queryFn:()=>formsApi.submissions(page)});
 return <div className="space-y-5"><Button variant="ghost" onClick={onBack}>← Back to forms</Button><PageHeader title="Submissions" description="Saved entries you have access to."/>{query.isPending?<p role="status">Loading entries…</p>:query.isError?<p role="alert">Unable to load entries. <button className="underline" onClick={()=>query.refetch()}>Try again</button></p>:!query.data?.results.length?<p className="rounded-xl border border-dashed p-6">No saved entries yet.</p>:<div className="grid gap-3 md:grid-cols-2">{query.data.results.map(entry=><Link key={entry.id} href={`/forms/submissions/${entry.id}`} className="sb-form-choice"><span className="sb-soft-label self-start">{formatEnumLabel(entry.status)}</span><h2 className="mt-3 font-semibold">{entry.title || entry.schema_snapshot.name || "Form entry"}</h2><p className="mt-2 text-sm text-[var(--muted)]">{new Intl.DateTimeFormat(undefined,{dateStyle:"medium"}).format(new Date(entry.created_at))}</p><span className="mt-4 text-sm font-semibold">Open entry →</span></Link>)}</div>}{query.data&&<CollectionPager {...query.data} page={page} busy={query.isFetching} onChange={setPage}/>}</div>;
}
''')
put('src/app/(dashboard)/settings/forms/page.tsx','''"use client";
import { FormBuilderGuard } from "@/components/forms/FormBuilderGuard";
import { CompanyFormsWorkspace } from "@/components/forms/CompanyFormsWorkspace";
export default function SetupFormsPage(){return <FormBuilderGuard><CompanyFormsWorkspace/></FormBuilderGuard>;}
''')
p='src/app/(dashboard)/forms/page.tsx';s=read(p).replace('ClipboardList, ArrowRight, LibraryBig','ClipboardList, ArrowRight').replace('import { workspaceApi }','import { CompanyFormsWorkspace } from "@/components/forms/CompanyFormsWorkspace";\nimport { FormsSubmissions } from "@/components/forms/FormsSubmissions";\nimport { Button } from "@/components/ui/Button";\nimport { workspaceApi }')
s=s.replace('  const [page, setPage]', '  const [entries,setEntries]=useState(false);\n  const [page, setPage]').replace('enabled: access.forms','enabled: access.forms && !access.formManagement && !entries')
a=s.index('  return <div');b=s.index('    {!access.forms',a)
s=s[:a]+'''  if(access.formManagement)return <CompanyFormsWorkspace/>;
  if(entries)return <FormsSubmissions onBack={()=>setEntries(false)}/>;
  return <div className="space-y-6"><PageHeader title="Company forms" description="Choose a form to record your work." action={access.forms&&<Button variant="outline" onClick={()=>setEntries(true)}>Submissions</Button>}/>
'''+s[b:]
s=s.replace('<p className="mt-4 text-xs text-[var(--muted)]">{template.allow_drafts ? "You can save a draft and continue later." : "Review your answers before submitting."}</p>','').replace('mt-2 text-sm text-[var(--muted)]','mt-2 line-clamp-2 text-sm text-[var(--muted)]');put(p,s)
p='src/api/formsApi.ts';s=read(p).replace('import { extractResults }','import { collectionPage } from "./workspaceApi";\nimport { extractResults }');s=s.replace('export const formsApi = {','''export const formsApi = {
  async submissions(page=1) {const data=collectionPage<FormSubmission & {data?:Record<string,unknown>}>((await api.get("form-submissions/",{params:{page}})).data);return {...data,results:data.results.map(submissionResult)};},''');put(p,s)
p='src/components/layout/navigation.ts';s=read(p);s='\n'.join(line for line in s.split('\n') if not ('label: "Form library"' in line));put(p,s)
p='src/components/layout/WorkspaceNav.tsx';s=read(p).replace('  const group = workspaceFor(pathname);','  if(pathname === "/forms" || pathname.startsWith("/forms/") || pathname.startsWith("/settings/forms")) return null;\n  const group = workspaceFor(pathname);');put(p,s)
p='src/components/layout/workspaces.ts';s=read(p).replace('  return items.filter(item => pathname === item.href || pathname.startsWith(item.href + "/"))','  const effectivePath = pathname.startsWith("/settings/forms") ? "/forms" : pathname;\n  return items.filter(item => effectivePath === item.href || effectivePath.startsWith(item.href + "/"))');put(p,s)
p='src/components/forms/FormTemplateLibrary.tsx';s=read(p)
s=s.replace('onChoose, onSaved }: { onChoose?', 'onChoose, onSaved, onOpen }: { onOpen?: (id:string)=>void; onChoose?')
s=s.replace('Choose complete forms for your company. Try a preview, add your choices to Company forms, then review who can use them and publish. You can adjust fields or create a custom form when needed.','Preview a form, then add a company draft.')
s=s.replace(' selected · Saved as drafts, never published automatically.',' selected · Added as drafts.')
s=s.replace('Add selected to Company forms','Add selected').replace('Preview the complete form','Preview form').replace('Use this prepared form →','Use this form →').replace('Add to Company forms','Add form')
s=s.replace('Record your company’s work using prepared fields. Choose access and reviewers before publishing.','Prepared fields for your company.')
s=s.replace('className="mt-2 text-sm text-[var(--muted)]">{form.description','className="mt-2 line-clamp-2 text-sm text-[var(--muted)]">{form.description')
s=s.replace(' prepared fields · Private company copy',' fields')
s=s.replace('Name, company and date start automatically when you use this form. Location can be adjusted.','Automatic details included')
a=s.index(' : existing ? <div>');b=s.index(' : <div className="flex flex-wrap',a)
s=s[:a]+''' : existing ? <div>{onOpen?<Button variant="outline" onClick={()=>onOpen(existing.id)}>Open company form →</Button>:<Link href={`/settings/forms/${existing.id}`} className="sb-action-link">Open company form →</Link>}</div>'''+s[b:]
put(p,s)
p='src/components/forms/FormDetail.tsx';s=read(p).replace('({id,onOpen}:{id:string;onOpen?:(id:string)=>void})','({id,onOpen,onBack}:{id:string;onOpen?:(id:string)=>void;onBack?:()=>void})')
s=s.replace('return <div className="mx-auto max-w-4xl space-y-6"><PageHeader','return <div className="mx-auto max-w-4xl space-y-6">{onBack?<Button variant="ghost" onClick={onBack}>← Back to forms</Button>:<Link href="/forms" className="sb-text-link">← Back to forms</Link>}<PageHeader')
a=s.index(' <section className="rounded-xl border p-4 text-sm">');b=s.index(' {!editing&&template.library_update',a);s=s[:a]+s[b:]
s=s.replace('To change a published form, create a draft revision and review it before publishing. Previously submitted answers keep the form as it was when they were submitted.','Changes are saved as a draft revision. Previous entries stay unchanged.')
s=s.replace('Check how employees will fill in each field. Answers entered in this preview are not saved or submitted.','Preview only. Answers are not saved.')
s=s.replace('&&<FormReviewRoute id={id}', '&&<details className="rounded-xl border border-[var(--line)] p-4"><summary className="cursor-pointer font-semibold">Approval settings</summary><div className="mt-4"><FormReviewRoute id={id}')
s=s.replace('router.replace(`/settings/forms/${nextId}`);}}/>}', 'router.replace(`/settings/forms/${nextId}`);}}/></div></details>}')
s=s.replace('{allowed.includes("COPY")&&<form', '{allowed.includes("COPY")&&<details className="rounded-xl border border-[var(--line)] p-4"><summary className="cursor-pointer font-semibold">More options · Copy this form</summary><form')
s=s.replace('Create company copy</Button></form>}', 'Create company copy</Button></form></details>}');put(p,s)
