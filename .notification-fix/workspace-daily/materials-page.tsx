"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Package, ArrowUpRight, ClipboardCheck, Truck, PackageCheck } from "lucide-react";
import { formsApi } from "@/api/formsApi";
import { useAuthStore } from "@/store/authStore";
import { formatEnumLabel } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader";
import { CollectionPager } from "@/components/ui/CollectionPager";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";

const journey = [
  { title: "Request & review", description: "Ask for supplies and get a decision.", icon: ClipboardCheck },
  { title: "Dispatch & delivery", description: "Record approved items sent.", icon: Truck },
  { title: "Confirm receipt", description: "Check what arrived and any differences.", icon: PackageCheck },
];

export default function MaterialsPage() {
  const user = useAuthStore(state => state.user);
  const [page, setPage] = useState(1);
  const query = useQuery({queryKey: ["forms", "material-list", user?.company, user?.id, page], queryFn: () => formsApi.materialsList(page)});
  return <div className="space-y-6">
    <PageHeader title="Materials & deliveries" description="Follow supplies from a request to their arrival. Open a request to see its items and available next actions." action={<Link className="sb-primary-link" href="/forms">Find a material request form</Link>}/>
    <section aria-label="How materials move" className="sb-workspace-panel !p-4"><ol className="grid gap-3 md:grid-cols-3">
      {journey.map(({title, description, icon: Icon}, index) => <li key={title} className="flex items-start gap-3"><Icon size={20} className="mt-0.5 shrink-0 text-[var(--accent-text)]" aria-hidden="true"/><div><h2 className="text-sm font-semibold">{index + 1}. {title}</h2><p className="mt-1 text-xs text-[var(--muted)]">{description}</p></div></li>)}
    </ol></section>
    {query.isPending ? <Skeleton className="h-48 w-full"/> : query.isError ? <ErrorState title="We couldn’t load material requests" description="Please try again. Your saved requests have not changed." onRetry={() => void query.refetch()}/> : !query.data?.results.length ? <EmptyState icon={<Package size={30}/>} title="Your material requests start here" description="Use a published material request form from Company forms. After submitting, return here to follow review and delivery." action={<Link className="sb-action-link" href="/forms">Browse company forms →</Link>}/> : <>
      <p role="status" className="text-sm text-[var(--muted)]">{query.data.count} material {query.data.count === 1 ? "request" : "requests"} available to your account</p>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{query.data.results.map(request => <Link key={request.id} href={`/forms/submissions/${request.id}`} className="sb-explore-card"><div className="flex items-center justify-between gap-3"><Package size={24} className="shrink-0 text-[var(--accent-text)]" aria-hidden="true"/><span className="sb-soft-badge">{formatEnumLabel(request.status)}</span></div><h2 className="mt-4 break-words text-lg font-semibold">{request.title || "Material request"}</h2><p className="mt-2 break-words text-sm text-[var(--muted)]">{request.reference}</p><p className="mt-3 text-sm">{request.items.length} {request.items.length === 1 ? "item" : "items"}</p><p className="mt-1 break-words text-sm text-[var(--muted)]">{request.items.slice(0, 3).map(item => item.item).join(", ")}{request.items.length > 3 ? ` and ${request.items.length - 3} more` : ""}</p><span className="sb-text-link mt-4">View items & delivery progress <ArrowUpRight size={16} aria-hidden="true"/></span></Link>)}</div>
    </>}
    {query.data && <CollectionPager {...query.data} page={page} busy={query.isFetching} onChange={setPage}/>}
  </div>;
}
