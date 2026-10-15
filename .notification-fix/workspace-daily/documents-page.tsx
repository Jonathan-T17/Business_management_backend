"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FileText, ArrowUpRight } from "lucide-react";
import { workspaceApi } from "@/api/workspaceApi";
import { useAuthStore } from "@/store/authStore";
import { workspaceAccess } from "@/utils/workspace";
import { formatEnumLabel } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { CollectionPager } from "@/components/ui/CollectionPager";

export default function DocumentsPage() {
  const user = useAuthStore(state => state.user);
  const access = workspaceAccess(user);
  const [page, setPage] = useState(1);
  const query = useQuery({queryKey: ["documents", "workspace", user?.company, user?.id, page], queryFn: () => workspaceApi.documents(page), retry: false});
  return <div className="space-y-6"><PageHeader title="Documents" description="Open documents shared with you, check the latest version and download when allowed." action={access.documents && <Link href="/documents/new" className="sb-primary-link">Add a document</Link>}/>
    <div className="sb-context-note"><FileText size={22} className="shrink-0 text-[var(--accent-text)]" aria-hidden="true"/><p className="text-sm text-[var(--muted)]">Your library shows documents available to your account. Open a card to view its details and available actions.</p></div>
    {query.isSuccess && query.data && query.data.count > 0 && <p role="status" className="text-sm text-[var(--muted)]">{query.data.count} {query.data.count === 1 ? "document" : "documents"} available to your account</p>}
    {query.isPending ? <Skeleton className="h-48 w-full"/> : query.isError ? <ErrorState title="We couldn’t load your documents" description="Please try again. Your documents have not been changed." onRetry={() => query.refetch()}/> : !query.data?.results.length ? <EmptyState icon={<FileText size={30}/>} title="Your document library starts here" description={access.documents ? "Add a company document and choose who it is shared with." : "Documents will appear here when they are shared with you."} action={access.documents && <Link href="/documents/new" className="sb-action-link">Add your first document →</Link>}/> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{query.data.results.map(document => <Link href={`/documents/${document.id}`} key={document.id} className="sb-explore-card"><div className="flex justify-between gap-3"><FileText size={24} className="text-[var(--accent-text)]"/><span className="sb-soft-label">{formatEnumLabel(document.status)}</span></div><h2 className="mt-4 break-words text-lg font-semibold">{document.title}</h2><p className="mt-2 text-sm text-[var(--muted)]">{({PRIVATE: "Private", COMPANY: "Shared with the company", BRANCH: "Shared with a branch", DEPARTMENT: "Shared with a department", TEAM: "Shared with a team", MANAGEMENT: "Management access"})[document.visibility]} · Version {document.current_version}</p>{document.category && <p className="mt-2 text-sm text-[var(--muted)]">{document.category.name}</p>}<span className="sb-text-link mt-4">Open document <ArrowUpRight size={16}/></span></Link>)}</div>}
    {query.data && <CollectionPager {...query.data} page={page} busy={query.isFetching} onChange={setPage}/>}
  </div>;
}
