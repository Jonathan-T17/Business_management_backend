"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { Button } from "@/components/ui/Button";
import { normalizeApiError } from "@/utils/apiError";
import { RequireCapability } from "@/components/auth/RequireCapability";
import { CAPABILITIES } from "@/utils/capabilities";
export function FormReviewRoute({id, onSaved}:{id:string;onSaved:(id:string)=>void}) {
 const [route,setRoute]=useState("SUPERVISOR"); const [position,setPosition]=useState("");
 const query=useQuery({queryKey:["forms","choices"],queryFn:formsApi.choices});
 const save=useMutation({mutationFn:()=>formsApi.configureReview(id,route,position?Number(position):undefined),onSuccess:form=>onSaved(form.id)});
 const error=save.error?normalizeApiError(save.error):null;
 return <RequireCapability capabilities={[CAPABILITIES.MANAGE_WORKFLOWS]}><RequireCapability capabilities={[CAPABILITIES.PUBLISH_WORKFLOWS]}><details className="rounded-xl border p-5"><summary className="cursor-pointer font-semibold">Set who reviews this form</summary><form className="mt-4 space-y-4" onSubmit={e=>{e.preventDefault();save.mutate();}}>
 <p className="text-sm text-[var(--muted)]">Routine reports normally go to the assigned supervisor. Branch summaries go to headquarters. Requests can require both stages. Saving replaces the review route on this draft; published forms receive a new draft revision.</p>
 <label className="block text-sm">Review route<select className="mt-1 w-full rounded-lg border bg-[var(--surface)] p-3" value={route} onChange={e=>setRoute(e.target.value)}><option value="SUPERVISOR">Employee → assigned supervisor</option><option value="HEADQUARTERS">Submitter → headquarters</option><option value="SUPERVISOR_HEADQUARTERS">Employee → supervisor → headquarters</option></select></label>
 {route!=="SUPERVISOR"&&<label className="block text-sm">Headquarters responsibility<select className="mt-1 w-full rounded-lg border bg-[var(--surface)] p-3" required value={position} onChange={e=>setPosition(e.target.value)}><option value="">Choose a headquarters position</option>{query.data?.headquarters_positions.map(item=><option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}
 <p className="text-sm text-[var(--muted)]">Direct reporting to headquarters must be limited to the intended people using the form’s access settings. This route does not grant access to other headquarters information.</p>
 {query.isError&&<p role="alert">Unable to load headquarters positions. <button type="button" className="underline" onClick={()=>query.refetch()}>Retry</button></p>}
 {route!=="SUPERVISOR"&&!query.isPending&&!query.isError&&!query.data?.headquarters_positions.length&&<p className="sb-notice">Set up a headquarters position with company-wide responsibility first.</p>}
 {error&&<p role="alert" className="sb-notice">{Object.values(error.fields).join(" ")||error.message}</p>}
 <Button type="submit" loading={save.isPending} disabled={query.isPending||query.isError}>Save review route</Button>
 </form></details></RequireCapability></RequireCapability>;
}
