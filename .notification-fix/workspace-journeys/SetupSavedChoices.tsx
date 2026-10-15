"use client";
import { useQuery } from "@tanstack/react-query";
import { getMyCompany } from "@/api/companyApi";
import { getCompanyStructure } from "@/api/companyStructureApi";
import { formsApi } from "@/api/formsApi";
import { getInvitationPage } from "@/api/invitesApi";
import { useAuthStore } from "@/store/authStore";
import { ErrorState } from "@/components/ui/ErrorState";

export function SetupSavedChoices({step}:{step:string}) {
 const user=useAuthStore(state=>state.user);
 const query=useQuery({queryKey:["company-setup","saved-choices",user?.company,user?.id,step],queryFn:async()=>{
  if(step==="company") { const company=await getMyCompany(); return company ? [{title:company.name,detail:[company.country,company.timezone,company.default_currency].filter(Boolean).join(" · ")}] : []; }
  if(step==="forms") { const forms=await formsApi.builderTemplates(); return forms.filter(item=>item.lifecycle_status!=="ARCHIVED").map(item=>({title:item.name,detail:item.lifecycle_status==="PUBLISHED"?"Ready to use":"Saved draft"})); }
  if(step==="employees") { const page=await getInvitationPage(1,"active"); return [{title:`${page.count} active invitations`,detail:"Invitations can remain pending while you finish setup."},...page.results.map(item=>({title:item.email,detail:item.status.toLowerCase().replaceAll("_"," ")}))]; }
  const structure=await getCompanyStructure();
  if(step==="organization") return [...structure.branches].sort((a,b)=>Number(b.id===structure.headquarters?.id)-Number(a.id===structure.headquarters?.id)).map(item=>({title:item.name,detail:`${item.id===structure.headquarters?.id?"Head office":"Branch"}${item.location?` · ${item.location}`:""}`}));
  if(step==="departments") return [...structure.departments.map(item=>({title:item.name,detail:"Department"})),...structure.teams.map(item=>({title:item.name,detail:"Team"}))];
  return structure.positions.map(item=>({title:item.title,detail:step==="permissions"?"Saved company position; use Edit to review its access choices.":"Saved company position"}));
 }});
 if(query.isPending)return <p role="status" className="py-4 text-sm text-[var(--muted)]">Loading your saved choices…</p>;
 if(query.isError)return <ErrorState title="Unable to load saved choices" onRetry={()=>void query.refetch()}/>;
 return <div className="mt-4">{!query.data?.length?<p className="rounded-lg bg-[var(--surface-soft)] p-4 text-sm text-[var(--muted)]">No items are currently saved for this step. Use Edit to review your choices.</p>:<ul className="grid gap-2 sm:grid-cols-2" aria-label="Saved setup choices">{query.data.map((item,index)=><li key={`${item.title}-${index}`} className="rounded-lg border border-[var(--line)] p-3"><p className="break-words text-sm font-semibold">{item.title}</p><p className="mt-1 break-words text-xs text-[var(--muted)]">{item.detail}</p></li>)}</ul>}</div>;
}