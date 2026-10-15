"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { platformClient } from "@/api/client";
import { useAuthStore } from "@/store/authStore";

type Event = {id: number; actor_name: string; status: string; note: string; created_at: string};
type Incident = {id: string; title: string; severity: string; status: string; assigned_name: string | null; updated_at: string; events: Event[]};
const transitions: Record<string,string[]> = {OPEN:["INVESTIGATING","RESOLVED"], INVESTIGATING:["CONTAINED","RESOLVED"], CONTAINED:["INVESTIGATING","RESOLVED"], RESOLVED:["INVESTIGATING"]};
const label = (value: string) => value.charAt(0) + value.slice(1).toLowerCase();
const field = "mt-1 w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3 text-[var(--ink)]";
function failure(error: unknown) {
  const data = (error as {response?: {data?: unknown}})?.response?.data;
  if (data && typeof data === "object") {
    const values = Object.values(data).flat().filter(value => typeof value === "string");
    if (values.length) return values.join(" ");
  }
  return "Unable to save this incident. Check your details and try again.";
}

export default function IncidentsPage() {
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const client = useQueryClient();
  const user = useAuthStore(state => state.user);
  const canManage = user?.capabilities?.includes("MANAGE_PLATFORM_SECURITY");
  const {data, isLoading, isError} = useQuery({queryKey:["platform","incidents",page], queryFn:async () => (await platformClient.get<{results: Incident[]; next: string|null; previous: string|null}>("security/incidents/", {params:{page}})).data});
  const refresh = () => client.invalidateQueries({queryKey:["platform","incidents"]});
  return <div className="space-y-6">
    <header><Link href={user?.capabilities?.includes("VIEW_PLATFORM_SECURITY") ? "/platform/security" : "/platform/audit"} className="text-sm text-teal-700 dark:text-teal-300">Back to {user?.capabilities?.includes("VIEW_PLATFORM_SECURITY") ? "security" : "audit"}</Link><h1 className="mt-3 text-2xl font-semibold">Security incidents</h1><p className="mt-2 text-[var(--muted)]">Track an issue from investigation to resolution. Recording a status does not perform containment actions.</p></header>
    {canManage && <button className="rounded-xl bg-teal-700 px-4 py-3 font-medium text-white" onClick={() => setCreating(!creating)}>{creating ? "Close new incident" : "Record an incident"}</button>}
    {creating && canManage && <CreateIncident saved={() => {setCreating(false);void refresh();}}/>}
    {isLoading ? <p role="status">Loading incidents…</p> : isError ? <p role="alert">Unable to load incidents. Try again shortly.</p> : !data?.results.length ? <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-8"><h2 className="font-semibold">No incidents recorded</h2><p className="mt-2 text-sm text-[var(--muted)]">This is the incident register. An empty register is not proof that the system has no security risks.</p></section> : data.results.map(incident => <IncidentCard key={incident.id} incident={incident} canManage={Boolean(canManage)} saved={refresh}/>)}
    {data && <nav aria-label="Incident pages" className="flex items-center gap-4"><button disabled={!data.previous} onClick={() => setPage(page-1)} className="rounded-xl border border-[var(--line)] px-4 py-2 disabled:opacity-40">Previous</button><span className="text-sm">Page {page}</span><button disabled={!data.next} onClick={() => setPage(page+1)} className="rounded-xl border border-[var(--line)] px-4 py-2 disabled:opacity-40">Next</button></nav>}
  </div>;
}

function CreateIncident({saved}: {saved:()=>void}) {
  const mutation = useMutation({mutationFn: async (values: object) => platformClient.post("security/incidents/",values), onSuccess:saved});
  return <form className="space-y-4 rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5" onSubmit={event => {event.preventDefault();const form=event.currentTarget;const values=new FormData(form);void mutation.mutateAsync(Object.fromEntries(values)).finally(() => {const password=form.elements.namedItem("password") as HTMLInputElement;password.value="";}).catch(()=>{});}}>
    <h2 className="font-semibold">Record an incident</h2><p className="text-sm text-[var(--muted)]">Describe the issue without passwords, verification codes or confidential company records.</p>
    <label className="block text-sm">Title<input required maxLength={200} name="title" className={field}/></label>
    <label className="block text-sm">Severity<select name="severity" defaultValue="WARNING" className={field}><option value="INFO">Information</option><option value="WARNING">Warning</option><option value="CRITICAL">Critical</option></select></label>
    <label className="block text-sm">What happened?<textarea required maxLength={2000} name="note" className={field}/></label>
    <label className="block text-sm">Confirm your password<input required type="password" autoComplete="current-password" maxLength={256} name="password" className={field}/></label>
    {mutation.isError && <p role="alert" className="text-red-700 dark:text-red-300">{failure(mutation.error)}</p>}
    <button type="submit" disabled={mutation.isPending} className="rounded-xl bg-teal-700 px-4 py-3 text-white disabled:opacity-50">{mutation.isPending ? "Saving…" : "Save incident"}</button>
  </form>;
}

function IncidentCard({incident,canManage,saved}: {incident: Incident;canManage:boolean;saved:()=>Promise<unknown>}) {
  const [expanded,setExpanded] = useState(false);
  const mutation = useMutation({mutationFn: async (values: object) => platformClient.post(`security/incidents/${incident.id}/transition/`,values), onSuccess:()=>saved()});
  return <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-medium text-[var(--muted)]">{label(incident.severity)} · {label(incident.status)}</p><h2 className="mt-2 text-lg font-semibold">{incident.title}</h2><p className="mt-2 text-sm text-[var(--muted)]">Assigned to {incident.assigned_name || "Not assigned"} · Updated {new Date(incident.updated_at).toLocaleString()}</p></div><button aria-expanded={expanded} onClick={()=>setExpanded(!expanded)} className="rounded-xl border border-[var(--line)] px-4 py-2">{expanded ? "Close details" : "Review incident"}</button></div>
    {expanded && <div className="mt-5 space-y-5"><ol className="space-y-3" aria-label="Investigation history">{incident.events.map(event => <li key={event.id} className="border-l-2 border-teal-500 pl-4"><p className="text-sm font-medium">{label(event.status)} · {event.actor_name}</p><p className="mt-1 whitespace-pre-wrap text-sm">{event.note}</p><p className="mt-1 text-xs text-[var(--muted)]">{new Date(event.created_at).toLocaleString()}</p></li>)}</ol>
    {canManage && <form key={incident.updated_at} className="space-y-3" onSubmit={event=>{event.preventDefault();const form=event.currentTarget;const values=new FormData(form);void mutation.mutateAsync({...Object.fromEntries(values),updated_at:incident.updated_at}).finally(()=>{const password=form.elements.namedItem("password") as HTMLInputElement;password.value="";}).catch(()=>{});}}><h3 className="font-semibold">Update the investigation</h3><label className="block text-sm">Next status<select name="status" className={field}>{transitions[incident.status].map(status=><option key={status} value={status}>{label(status)}</option>)}</select></label><label className="block text-sm">Reason and actions taken<textarea required name="note" maxLength={2000} className={field}/></label><label className="block text-sm">Confirm your password<input required type="password" autoComplete="current-password" name="password" maxLength={256} className={field}/></label>{mutation.isError && <p role="alert" className="text-red-700 dark:text-red-300">{failure(mutation.error)}</p>}<button type="submit" disabled={mutation.isPending} className="rounded-xl bg-teal-700 px-4 py-3 text-white disabled:opacity-50">{mutation.isPending ? "Saving…" : "Save status"}</button></form>}</div>}
  </section>;
}
