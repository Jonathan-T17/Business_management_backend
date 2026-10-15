"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { platformClient } from "@/api/client";

type Operator = {id:string;full_name:string;email:string;platform_duty:string};
const duties: Record<string,{label:string;description:string}> = {
  OWNER:{label:"Platform owner",description:"Full platform administration and recovery. Company confidential-data permissions remain separate."},
  SECURITY:{label:"Security operator",description:"Investigate incidents, inspect sign-ins, end sessions and clear login locks. No subscriptions or recovery administration."},
  SUPPORT:{label:"Customer support",description:"Manage support requests. No security controls, subscriptions or recovery administration."},
  SUBSCRIPTIONS:{label:"Subscription operator",description:"Review subscriptions and change plans. Renewal and reactivation remain with the owner in advanced administration."},
  AUDITOR:{label:"Read-only auditor",description:"Read audit history, incidents and service health. Cannot change records or end sessions."},
};
const field="mt-1 w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3";
export default function PlatformAccessPage() {
  const queryClient=useQueryClient();
  const {data,isLoading,isError}=useQuery({queryKey:["platform","access"],queryFn:async()=>(await platformClient.get<Operator[]>("security/access/")).data});
  return <div className="space-y-6"><header><h1 className="text-2xl font-semibold">Platform access</h1><p className="mt-2 text-[var(--muted)]">Give each administrator the responsibilities they need. Keep at least one active platform owner.</p></header>
    <div className="grid gap-3 sm:grid-cols-2">{Object.entries(duties).map(([key,duty])=><section key={key} className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5"><h2 className="font-semibold">{duty.label}</h2><p className="mt-2 text-sm text-[var(--muted)]">{duty.description}</p></section>)}</div>
    <h2 className="text-lg font-semibold">Current administrators</h2>
    {isLoading ? <p role="status">Loading administrators…</p> : isError ? <p role="alert">Unable to load platform access.</p> : data?.map(operator=><OperatorCard key={operator.id+operator.platform_duty} operator={operator} saved={()=>queryClient.invalidateQueries({queryKey:["platform","access"]})}/>)}
  </div>;
}
function OperatorCard({operator,saved}:{operator:Operator;saved:()=>Promise<unknown>}) {
  const [editing,setEditing]=useState(false);
  const [duty,setDuty]=useState(operator.platform_duty);
  const mutation=useMutation({mutationFn:async(values:object)=>platformClient.post("security/access/",values),onSuccess:()=>{setEditing(false);return saved();}});
  const errorData=(mutation.error as {response?:{data?:unknown}})?.response?.data;
  const error=typeof errorData==="object" && errorData ? Object.values(errorData).flat().filter(value=>typeof value==="string").join(" ") : "Unable to change this duty. Check your details and try again.";
  return <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold">{operator.full_name}</h3><p className="mt-1 text-sm text-[var(--muted)]">{operator.email}</p><p className="mt-2 text-sm font-medium">{duties[operator.platform_duty]?.label || "Unknown duty"}</p></div><button onClick={()=>setEditing(!editing)} className="rounded-xl border border-[var(--line)] px-4 py-2">{editing ? "Cancel" : "Change duty"}</button></div>
    {editing && <form className="mt-5 space-y-4" onSubmit={event=>{event.preventDefault();const form=event.currentTarget;const values=Object.fromEntries(new FormData(form));void mutation.mutateAsync({...values,user_id:operator.id,expected_duty:operator.platform_duty}).finally(()=>{const password=form.elements.namedItem("password") as HTMLInputElement;password.value="";}).catch(()=>{});}}>
      <label className="block text-sm">New duty<select name="duty" value={duty} onChange={event=>setDuty(event.target.value)} className={field}>{Object.entries(duties).map(([key,value])=><option key={key} value={key}>{value.label}</option>)}</select></label>
      <p className="text-sm text-[var(--muted)]">{duties[duty]?.description} Saving ends this person’s active sessions; they will sign in again with their new access.</p>
      <label className="block text-sm">Reason for the change<textarea required maxLength={1000} name="reason" className={field}/></label>
      <label className="block text-sm">Confirm your password<input required type="password" name="password" autoComplete="current-password" maxLength={256} className={field}/></label>
      {mutation.isError && <p role="alert" className="text-red-700 dark:text-red-300">{error}</p>}
      <button type="submit" disabled={mutation.isPending || duty===operator.platform_duty} className="rounded-xl bg-teal-700 px-4 py-3 text-white disabled:opacity-50">{mutation.isPending ? "Saving…" : "Confirm duty change"}</button>
    </form>}
  </section>;
}
