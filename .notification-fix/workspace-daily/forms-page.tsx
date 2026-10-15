"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ClipboardList, ArrowRight } from "lucide-react";
import { CompanyFormsWorkspace } from "@/components/forms/CompanyFormsWorkspace";
import { FormsSubmissions } from "@/components/forms/FormsSubmissions";
import { Button } from "@/components/ui/Button";
import { workspaceApi } from "@/api/workspaceApi";
import { useAuthStore } from "@/store/authStore";
import { workspaceAccess } from "@/utils/workspace";
import { formatEnumLabel } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { CollectionPager } from "@/components/ui/CollectionPager";
import { Skeleton } from "@/components/ui/Skeleton";
import { FORM_TEMPLATE_ACTIONS, hasAllowedAction } from "@/utils/allowedActions";

export default function FormsPage() {
  const user = useAuthStore(state => state.user);
  const access = workspaceAccess(user);
  const [entries,setEntries]=useState(false);
  const [page, setPage] = useState(1);
  const query = useQuery({queryKey: ["forms", "workspace-library", user?.company, user?.id, page], queryFn: () => workspaceApi.forms(page), enabled: access.forms && !access.formManagement && !entries, retry: false});
  const available = query.data?.results.filter(template => (template.lifecycle_status ?? template.status) === "PUBLISHED" && template.is_active !== false) ?? [];
  if(access.formManagement)return <CompanyFormsWorkspace/>;
  if(entries)return <FormsSubmissions onBack={()=>setEntries(false)}/>;
  return <div className="space-y-6"><PageHeader title="Company forms" description="Choose a form to record your work." action={access.forms&&<Button variant="outline" onClick={()=>setEntries(true)}>Saved entries</Button>}/>
    {!access.forms ? <EmptyState title="Your forms access is being arranged" description="Your company administrator can assign the forms you need for your work."/>
      : query.isPending ? <Skeleton className="h-44 w-full"/>
      : query.isError ? <ErrorState title="We couldn’t load your forms" description="Please try again to see the forms available to you." onRetry={() => query.refetch()}/>
      : available.length === 0 ? <EmptyState icon={<ClipboardList size={28}/>} title="No forms ready to complete" description={access.formManagement ? "Open the company form library to prepare and publish a form." : "Published forms will appear here when your company makes them available to you."} action={access.formManagement && <Link className="sb-action-link" href="/settings/forms">Open form library →</Link>}/>
      : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{available.map(template => <section key={template.id} className="sb-form-choice"><div className="flex items-center justify-between gap-2"><p className="sb-eyebrow">{formatEnumLabel(template.category)}</p><span className="sb-soft-label">Ready to use</span></div><h2 className="mt-4 text-lg font-semibold">{template.name}</h2><p className="mt-2 line-clamp-2 text-sm text-[var(--muted)]">{template.description || "Record your work using your company’s prepared fields."}</p><div className="mt-auto pt-5">{(!template.allowed_actions || hasAllowedAction(template.allowed_actions, FORM_TEMPLATE_ACTIONS.START)) ? <Link href={`/forms/templates/${template.id}`} className="sb-primary-link">Open form <ArrowRight size={16}/></Link> : <p className="text-sm text-[var(--muted)]">Available for viewing. Submission access is managed by your company.</p>}</div></section>)}</div>}
    {query.data && <CollectionPager {...query.data} page={page} busy={query.isFetching} onChange={setPage}/>}
  </div>;
}

