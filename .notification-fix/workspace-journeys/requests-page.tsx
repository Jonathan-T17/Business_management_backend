"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, Plus } from "lucide-react";
import { requestsApi } from "@/api/requestsApi";
import { RequestList } from "@/components/requests/RequestList";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { FilterBar } from "@/components/ui/FilterBar";
import { queryKeys } from "@/lib/queryKeys";
export default function RequestsPage() {
 const [search,setSearch]=useState("");
 const params=search.trim()?{search:search.trim()}:{};
 const query=useQuery({queryKey:queryKeys.requests.list(params),queryFn:()=>requestsApi.list(params)});
 const requests=query.data??[];
 return <div className="space-y-5"><PageHeader title="Requests" description="Send a request, continue a draft or follow a decision." action={<Link href="/requests/new" className="sb-primary-link"><Plus size={18}/>New request</Link>}/>
 <div className="sb-context-note"><FileText size={23} className="shrink-0 text-[var(--accent-text)]"/><p className="text-sm text-[var(--muted)]">Your saved requests stay here. For supplies sent between offices, use <Link href="/materials" className="font-semibold text-[var(--accent-text)] underline">Materials &amp; deliveries</Link>.</p></div>
 <FilterBar search={search} searchPlaceholder="Search requests by name or reference" onSearchChange={setSearch} onReset={search?()=>setSearch(""):undefined}/>
 {query.isPending?<div className="sb-workspace-panel" role="status">Loading requests…</div>:query.isError?<ErrorState title="We could not load your requests" description="Your saved work is unchanged. Please try again." onRetry={()=>void query.refetch()}/>:!requests.length?<EmptyState icon={<FileText size={28}/>} title={search.trim()?"No matching requests":"Your requests start here"} description={search.trim()?"Try another name or clear your search.":"Create a request, save a draft and return here to follow its progress."} action={search.trim()?<Button variant="outline" onClick={()=>setSearch("")}>Clear search</Button>:<Link href="/requests/new" className="sb-primary-link">Create a request</Link>}/>:<><p className="text-sm text-[var(--muted)]" role="status">{requests.length} requests shown</p><RequestList requests={requests}/></>}
 </div>;
}