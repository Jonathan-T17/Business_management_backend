"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ClipboardList, ArrowRight, LibraryBig } from "lucide-react";
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
  const [page, setPage] = useState(1);
  const query = useQuery({queryKey: ["forms", "workspace-library", user?.company, user?.id, page], queryFn: () => workspaceApi.forms(page), enabled: access.forms, retry: false});
  const available = query.data?.results.filter(template => (template.lifecycle_status ?? template.status) === "PUBLISHED" && template.is_active !== false) ?? [];
  return <div className="space-y-6"><PageHeader title="Company forms" description="Choose a form for the work you need to record." action={access.formManagement && <Link href="/settings/forms" className="sb-action-link"><LibraryBig size={17}/>Manage company forms</Link>}/>
    <Link href="/materials" className="sb-action-link">Materials and deliveries — follow requests and receipts →</Link><section className="sb-context-note"><ClipboardList size={22} className="shrink-0 text-[var(--accent-text)]"/><div><h2 className="font-semibold">Start with a ready-to-use company form</h2><p className="mt-1 text-sm text-[var(--muted)]">Your company prepares the fields. Open a form, fill in the details, then review before submitting.</p><Link className="sb-text-link mt-2" href="/reporting/obligations">Continue a scheduled report →</Link></div></section>
    {!access.forms ? <EmptyState title="Your forms access is being arranged" description="Your company administrator can assign the forms you need for your work."/>
      : query.isPending ? <Skeleton className="h-44 w-full"/>
      : query.isError ? <ErrorState title="We couldn’t load your forms" description="Please try again to see the forms available to you." onRetry={() => query.refetch()}/>
      : available.length === 0 ? <EmptyState icon={<ClipboardList size={28}/>} title="No forms ready to complete" description={access.formManagement ? "Open the company form library to prepare and publish a form." : "Published forms will appear here when your company makes them available to you."} action={access.formManagement && <Link className="sb-action-link" href="/settings/forms">Open form library →</Link>}/>
      : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{available.map(template => <section key={template.id} className="sb-form-choice"><div className="flex items-center justify-between gap-2"><p className="sb-eyebrow">{formatEnumLabel(template.category)}</p><span className="sb-soft-label">Ready to use</span></div><h2 className="mt-4 text-lg font-semibold">{template.name}</h2><p className="mt-2 text-sm text-[var(--muted)]">{template.description || "Record your work using your company’s prepared fields."}</p><p className="mt-4 text-xs text-[var(--muted)]">{template.allow_drafts ? "You can save a draft and continue later." : "Review your answers before submitting."}</p><div className="mt-auto pt-5">{(!template.allowed_actions || hasAllowedAction(template.allowed_actions, FORM_TEMPLATE_ACTIONS.START)) ? <Link href={`/forms/templates/${template.id}`} className="sb-primary-link">Open form <ArrowRight size={16}/></Link> : <p className="text-sm text-[var(--muted)]">Available for viewing. Submission access is managed by your company.</p>}</div></section>)}</div>}
    {query.data && <CollectionPager {...query.data} page={page} busy={query.isFetching} onChange={setPage}/>}
  </div>;
}

