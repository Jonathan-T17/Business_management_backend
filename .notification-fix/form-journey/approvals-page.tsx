"use client";
import Link from "next/link";
import { formatEnumLabel } from "@/utils/format";
import { useQuery } from "@tanstack/react-query";
import { CheckSquare, ChevronRight } from "lucide-react";
import { workflowsApi } from "@/api/workflowsApi";
import PageHeader from "@/components/ui/PageHeader";
import { queryKeys } from "@/lib/queryKeys";
import { WORKFLOW_ACTIONS, hasAnyAllowedAction } from "@/utils/allowedActions";

export default function ApprovalsPage() {
  const { data: items = [], isLoading, isError, refetch } = useQuery({ queryKey: queryKeys.workflows.inbox, queryFn: workflowsApi.inbox });
  const actionable = items.filter((item) => item.allowed_actions ? hasAnyAllowedAction(item.allowed_actions, Object.values(WORKFLOW_ACTIONS)) : item.can_approve || item.can_return || item.can_reject);
  return <div className="space-y-7"><PageHeader title="Reviews" description="Review work assigned to you, then approve it or request changes when needed." />
    {isError ? <div role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950"><p>We could not load this page. Your work has not been changed.</p><button type="button" className="mt-3 font-semibold underline" onClick={() => void refetch()}>Try again</button></div> : isLoading ? <div className="h-32 animate-pulse rounded-lg bg-[var(--surface)]" /> : actionable.length === 0 ? <div className="sb-workspace-panel text-center"><CheckSquare className="mx-auto text-neutral-400" /><p className="mt-3 text-sm text-[var(--muted)]">You are up to date — no decisions are waiting.</p><p className="mt-2 text-sm text-[var(--muted)]">Only reviews assigned to you appear here. Your company administrator sets the review process for each form or request.</p><Link href="/dashboard" className="sb-text-link mt-4 inline-block">Back to Home</Link></div> : <div className="space-y-3"><p className="text-sm text-[var(--muted)]" role="status">{actionable.length} {actionable.length===1?"review needs":"reviews need"} your decision</p>{actionable.map((item) => <Link key={item.instance_id} href={`/approvals/${item.instance_id}`} className="flex items-center justify-between sb-workspace-panel transition hover:border-neutral-400"><div><p className="text-xs font-semibold uppercase text-[var(--muted)]">{item.target_type === "FORM_SUBMISSION" ? "Form entry" : formatEnumLabel(item.target_type)}</p><h2 className="mt-1 font-semibold text-[var(--ink)]">{item.title}</h2><p className="mt-1 text-sm text-[var(--muted)]">Submitted by {item.submitted_by.full_name}</p><p className="mt-1 text-xs text-[var(--muted)]">{item.current_step?.name ?? (item.current_step ? `Step ${item.current_step.order}` : "Review complete")}</p>{item.delegated && item.acting_for && <p className="mt-2 text-sm font-medium text-amber-700">Acting on behalf of {item.acting_for.full_name}</p>}</div><ChevronRight className="shrink-0 text-neutral-400" /></Link>)}</div>}
  </div>;
}
