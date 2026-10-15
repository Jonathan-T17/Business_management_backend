"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import PageHeader from "@/components/ui/PageHeader";
import { CollectionPager } from "@/components/ui/CollectionPager";
export default function MaterialsPage() {
 const [page,setPage]=useState(1);
 const query=useQuery({queryKey:['forms','material-list',page],queryFn:()=>formsApi.materialsList(page)});
 return <div className="space-y-6"><PageHeader title="Materials and deliveries" description="Follow your requests from review through dispatch and receipt. Only requests available to your account appear here."/>
 <Link className="sb-action-link" href="/forms">Start a material request from company forms →</Link>
 {query.isPending?<p role="status">Loading material requests…</p>:query.isError?<p role="alert">Unable to load requests. <button className="underline" onClick={()=>query.refetch()}>Retry</button></p>:<><div className="grid gap-4 md:grid-cols-2">{query.data?.results.map(request=><Link key={request.id} href={`/forms/submissions/${request.id}`} className="sb-form-choice"><span className="sb-soft-label">{request.status}</span><h2 className="mt-3 font-semibold">{request.title}</h2><p className="mt-2 text-sm text-[var(--muted)]">{request.reference} · {request.items.length} items</p><span className="mt-4 sb-text-link">Open quantities and next actions →</span></Link>)}</div>{!query.data?.results.length&&<p className="sb-context-note">No connected material requests yet. Submit a published material request to begin.</p>}{query.data&&<CollectionPager {...query.data} page={page} busy={query.isFetching} onChange={setPage}/>}</>}
 </div>;
}
