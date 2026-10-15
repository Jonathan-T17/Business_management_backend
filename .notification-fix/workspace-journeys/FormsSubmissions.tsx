"use client";
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
 return <div className="space-y-5"><Button variant="ghost" onClick={onBack}>← Back to forms</Button><PageHeader title="Saved entries" description="Find your drafts, submitted forms and review progress."/>{query.isPending?<p role="status">Loading entries…</p>:query.isError?<p role="alert">Unable to load entries. <button className="underline" onClick={()=>query.refetch()}>Try again</button></p>:!query.data?.results.length?<p className="rounded-xl border border-dashed p-6">No saved entries yet.</p>:<div className="grid gap-3 md:grid-cols-2">{query.data.results.map(entry=><Link key={entry.id} href={`/forms/submissions/${entry.id}`} className="sb-form-choice"><span className="sb-soft-label self-start">{formatEnumLabel(entry.status)}</span><h2 className="mt-3 font-semibold">{entry.title || entry.schema_snapshot.name || "Form entry"}</h2><p className="mt-2 text-sm text-[var(--muted)]">{new Intl.DateTimeFormat(undefined,{dateStyle:"medium"}).format(new Date(entry.created_at))}</p><span className="mt-4 text-sm font-semibold">Open entry →</span></Link>)}</div>}{query.data&&<CollectionPager {...query.data} page={page} busy={query.isFetching} onChange={setPage}/>}</div>;
}
