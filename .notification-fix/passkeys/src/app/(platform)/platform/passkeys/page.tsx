"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { apiClient } from "@/api/client";
import { enrollPasskey } from "@/utils/passkeys";
import { tokenStorage } from "@/utils/tokens";
import { useAuthStore } from "@/store/authStore";

type Key={id:string;name:string;created_at:string;last_used_at:string|null};
const field="mt-2 w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3 text-[var(--text)]";
function message(error:unknown) {
 if(axios.isAxiosError(error)) return error.response?.data?.error?.message ?? error.response?.data?.detail ?? "Unable to update your passkeys. Try again.";
 if(error instanceof DOMException) return "Passkey setup was cancelled or unavailable. Try again using your own device.";
 return error instanceof Error ? error.message : "Unable to update your passkeys.";
}
export default function MyPasskeysPage() {
 const router=useRouter();const [adding,setAdding]=useState(false);const [removing,setRemoving]=useState<string|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState("");const [notice,setNotice]=useState("");
 const query=useQuery({queryKey:["my-administrator-passkeys"],queryFn:async()=> (await apiClient.get<{enabled:boolean;can_enroll:boolean;passkeys:Key[]}>("security/passkeys/")).data});
 async function add(event:React.FormEvent<HTMLFormElement>) {
  event.preventDefault();const form=event.currentTarget;const values=new FormData(form);setBusy(true);setError("");setNotice("");
  try {await enrollPasskey(String(values.get("name")),String(values.get("password")));setAdding(false);setNotice("Passkey added. Next time, enter your password and choose Sign in with a passkey.");await query.refetch();}
  catch(error){setError(message(error));}finally{const password=form.elements.namedItem("password") as HTMLInputElement;if(password)password.value="";setBusy(false);}
 }
 async function remove(event:React.FormEvent<HTMLFormElement>,id:string) {
  event.preventDefault();const form=event.currentTarget;setBusy(true);setError("");
  try{await apiClient.post(`security/passkeys/${id}/revoke/`,{password:String(new FormData(form).get("password"))});tokenStorage.clear();useAuthStore.getState().setUser(null);router.replace("/login");}
  catch(error){setError(message(error));}finally{const password=form.elements.namedItem("password") as HTMLInputElement;if(password)password.value="";setBusy(false);}
 }
 return <div className="space-y-6 text-[var(--text)]"><header><h1 className="text-2xl font-semibold">My administrator passkeys</h1><p className="mt-2 text-[var(--muted)]">Use your device lock, fingerprint or security key to verify administrator sign-in after entering your password. These passkeys belong only to your account.</p></header>
 <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-6"><h2 className="font-semibold">Keep a recovery option</h2><p className="mt-2 text-sm text-[var(--muted)]">Email verification remains available if you lose your device. Use a device you control and keep your email account protected. Adding or removing a passkey requires a verified sign-in within the past 15 minutes and your current password.</p></section>
 {error&&<p role="alert" className="text-red-700 dark:text-red-300">{error}</p>}{notice&&<p role="status" className="text-teal-700 dark:text-teal-300">{notice}</p>}
 {query.isLoading?<p role="status">Loading your passkeys…</p>:query.isError?<p role="alert">Unable to load your passkeys. Refresh and try again.</p>:!query.data?.enabled?<p role="alert">Passkeys are not configured for this site yet. Continue using email verification.</p>:<>
 {!query.data.can_enroll&&<p role="alert" className="rounded-xl border border-amber-600 p-4">For your security, <Link href="/login" className="font-semibold underline">sign in again</Link> before managing passkeys.</p>}
 <button disabled={busy||!query.data.can_enroll} onClick={()=>{setAdding(!adding);setRemoving(null);setError("");}} className="rounded-xl bg-teal-700 px-4 py-3 font-semibold text-white disabled:opacity-50">{adding?"Cancel setup":"Add a passkey"}</button>
 {adding&&<form onSubmit={add} className="space-y-4 rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-6"><h2 className="font-semibold">Name your device</h2><p className="text-sm text-[var(--muted)]">Your browser will ask you to verify with your device. SmartBiz does not receive your fingerprint, face scan or device PIN.</p><label className="block text-sm">Passkey name<input required name="name" maxLength={80} placeholder="For example, my work laptop" className={field}/></label><label className="block text-sm">Confirm your password<input required type="password" autoComplete="current-password" name="password" maxLength={256} className={field}/></label><button disabled={busy} className="rounded-xl bg-teal-700 px-4 py-3 text-white disabled:opacity-50">{busy?"Waiting for your device…":"Continue on my device"}</button></form>}
 <section className="space-y-3"><h2 className="font-semibold">Your saved passkeys</h2>{!query.data.passkeys.length&&<p className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-6 text-[var(--muted)]">No passkeys added yet. Email verification continues to protect your sign-in.</p>}{query.data.passkeys.map(key=><article key={key.id} className="space-y-3 rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-6"><h3 className="font-semibold">{key.name}</h3><p className="text-sm text-[var(--muted)]">Added {new Date(key.created_at).toLocaleDateString()} · {key.last_used_at?`Last used ${new Date(key.last_used_at).toLocaleString()}`:"Not used for sign-in yet"}</p><button disabled={busy||!query.data?.can_enroll} onClick={()=>{setRemoving(removing===key.id?null:key.id);setAdding(false);setError("");}} className="font-medium text-red-700 dark:text-red-300 disabled:opacity-50">{removing===key.id?"Cancel removal":"Remove passkey"}</button>{removing===key.id&&<form onSubmit={event=>void remove(event,key.id)} className="space-y-3"><p className="text-sm">Removing this passkey ends all your administrator sessions. You can sign in again with another passkey or email verification.</p><label className="block text-sm">Confirm your password<input required type="password" name="password" autoComplete="current-password" maxLength={256} className={field}/></label><button disabled={busy} className="rounded-xl bg-red-700 px-4 py-3 text-white disabled:opacity-50">Remove and sign out</button></form>}</article>)}</section></>}
 </div>;
}
