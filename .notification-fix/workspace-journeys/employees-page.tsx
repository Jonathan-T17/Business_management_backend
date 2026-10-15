"use client";
import { useState } from "react";
import { useAuthorization } from "@/hooks/useAuthorization";
import { CAPABILITIES } from "@/utils/capabilities";
import Link from "next/link";
import { Users, UserPlus } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { workspaceAccess } from "@/utils/workspace";
import { useEmployees } from "@/hooks/useEmployees";
import { EmployeeList } from "@/components/employees/EmployeeList";
import PageHeader from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { FilterBar } from "@/components/ui/FilterBar";
import { Skeleton } from "@/components/ui/Skeleton";
import { CollectionPager } from "@/components/ui/CollectionPager";
import { AccessDenied } from "@/components/ui/AccessDenied";

export default function EmployeesPage() {
  const { canAny } = useAuthorization();
  const canManagePositions = canAny(CAPABILITIES.MANAGE_ORGANIZATION);
  const access = workspaceAccess(useAuthStore(state => state.user));
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const query = useEmployees({page, search: search.trim() || undefined}, access.people);
  function searchFor(value: string) {setSearch(value); setPage(1);}
  if (!access.people) return <AccessDenied/>;
  return <div className="space-y-6"><PageHeader title="People" description="Find your colleagues and see where they work." action={access.invite && <Link href="/employees/invite" className="sb-primary-link"><UserPlus size={17}/>Invite employees</Link>}/>
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold">People in your company</h2>{access.invite && <Link className="sb-text-link" href="/employees/invite?view=progress">Invitation progress →</Link>}</div>
    {canManagePositions && <Link href="/employees/positions" className="sb-action-link">Positions & responsibilities →</Link>}
    <FilterBar search={search} searchPlaceholder="Search by name, email or employee ID" onSearchChange={searchFor} onReset={search ? () => searchFor("") : undefined}/>
    {query.isPending ? <Skeleton className="h-48 w-full"/> : query.isError ? <ErrorState title="We couldn’t load the directory" onRetry={() => query.refetch()}/> : !query.data?.results.length ? <EmptyState icon={<Users size={28}/>} title={search.trim() ? "No matching employees" : "Build your company directory"} description={search.trim() ? "Try a different name, email or employee ID, or clear your search." : "Employees appear here as they join your company."} action={search.trim() ? <button className="sb-action-link" onClick={() => searchFor("")}>Clear search</button> : access.invite && <Link className="sb-action-link" href="/employees/invite">Invite your first employee →</Link>}/> : <><p role="status" className="text-sm text-[var(--muted)]">{query.data.count} {query.data.count === 1 ? "person" : "people"}{search.trim() ? " matching your search" : " in your directory"}</p><EmployeeList employees={query.data.results}/></>}
    {query.data && <CollectionPager {...query.data} page={page} busy={query.isFetching} onChange={setPage}/>}
  </div>;
}
