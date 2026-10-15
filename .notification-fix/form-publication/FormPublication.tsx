"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { Button } from "@/components/ui/Button";
import { useAuthorization } from "@/hooks/useAuthorization";
import { CAPABILITIES } from "@/utils/capabilities";
import type { FormPublicationSettings } from "@/types/forms";

export function FormPublication({pending, onPublish, onCancel}: {pending: boolean; onPublish: (settings: FormPublicationSettings) => void; onCancel: () => void}) {
  const {canAny, user} = useAuthorization();
  const canShare = canAny(CAPABILITIES.CONFIGURE_SENSITIVE_FORMS);
  const choices = useQuery({queryKey: ['forms', 'choices', user?.company, user?.id], queryFn: formsApi.choices});
  const [audience, setAudience] = useState<FormPublicationSettings['audience']>('COMPANY');
  const [branches, setBranches] = useState<number[]>([]);
  const [entries, setEntries] = useState<'STANDARD' | 'AUDIENCE'>('STANDARD');
  const [share, setShare] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  return <form className="sb-workspace-panel space-y-4" aria-label="Make form available" onSubmit={event => {event.preventDefault(); onPublish({audience, branch_ids: branches, entry_visibility: entries, share_confidential: share, confirm_confidential_access: confirmed});}}>
    <h2 className="text-lg font-semibold">Make this form available</h2>
    <label className="block text-sm font-medium">Who can see and use this form?<select disabled={pending} className="mt-2 block w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3" value={audience} onChange={event => {setAudience(event.target.value as typeof audience); setConfirmed(false);}}><option value="COMPANY">Entire company</option><option value="HEADQUARTERS">Headquarters only</option><option value="BRANCHES">Selected branches</option></select></label>
    {audience === 'BRANCHES' && <fieldset disabled={pending} className="space-y-2"><legend className="mb-2 text-sm font-medium">Choose one or more branches</legend>{choices.isPending ? <p role="status">Loading locations…</p> : choices.isError ? <p role="alert">Unable to load branches. <button type="button" className="underline" onClick={() => void choices.refetch()}>Try again</button></p> : choices.data?.branches.map(branch => <label className="flex items-center gap-2 text-sm" key={branch.id}><input type="checkbox" checked={branches.includes(Number(branch.id))} onChange={event => {setBranches(current => event.target.checked ? [...current, Number(branch.id)] : current.filter(id => id !== Number(branch.id))); setConfirmed(false);}}/>{branch.name}</label>)}</fieldset>}
    <label className="block text-sm font-medium">Who can read submitted entries and files?<select disabled={pending} value={entries} onChange={event => {setEntries(event.target.value as typeof entries); setShare(false); setConfirmed(false);}} className="mt-2 block w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3"><option value="STANDARD">Author and authorized colleagues</option><option value="AUDIENCE">Published audience too</option></select></label>
    <p className="text-sm text-[var(--muted)]">Entire company includes headquarters and all branches. Existing entry access stays in place; sharing adds the selected audience. Drafts remain restricted. These settings apply to entries created with this form version. Your review route remains separate.</p>
    {entries === 'AUDIENCE' && <div className="rounded-lg border border-[var(--line)] p-3"><label className="flex items-start gap-2 text-sm"><input className="mt-1" type="checkbox" disabled={pending || !canShare} checked={share} onChange={event => {setShare(event.target.checked); setConfirmed(false);}}/>Also share confidential answers and supporting files with this audience</label><p className="mt-2 text-xs text-[var(--muted)]">{canShare ? 'Otherwise existing confidential-field protections stay in effect.' : 'This choice requires confidential form access authority.'}</p>{share && <label className="mt-3 flex items-start gap-2 text-sm"><input className="mt-1" type="checkbox" required disabled={pending} checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/>I confirm that every person in the selected audience may read confidential answers and attached files. This decision is recorded in the audit history.</label>}</div>}
    <p className="text-xs text-[var(--muted)]">The chosen audience replaces ordinary person, position and department restrictions. Special permission for direct headquarters reporting is kept. Restricted confidential forms still require the appropriate clearance unless sharing is explicitly authorized above.</p>
    <div className="flex flex-wrap gap-2"><Button type="submit" loading={pending} disabled={(audience === 'BRANCHES' && (!branches.length || !choices.isSuccess)) || (share && !confirmed)}>Make available</Button><Button type="button" variant="outline" disabled={pending} onClick={onCancel}>Cancel</Button></div>
  </form>;
}



