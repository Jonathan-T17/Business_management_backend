"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardList } from "lucide-react";
import { reportingSchedulesApi } from "@/api/reportingSchedulesApi";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import PageHeader from "@/components/ui/PageHeader";
import { useAuthStore } from "@/store/authStore";
import { queryKeys } from "@/lib/queryKeys";
import { formatDateTime, formatEnumLabel } from "@/utils/format";

const needsWork = new Set(["PENDING", "DRAFT", "MISSED", "RETURNED"]);
const statusLabels: Record<string, string> = {PENDING: "To do", DRAFT: "Draft", MISSED: "Overdue", RETURNED: "Changes requested", LATE: "Submitted late", SUBMITTED: "Submitted", APPROVED: "Approved", REJECTED: "Rejected", CANCELLED: "Cancelled"};

export default function ReportingObligationsPage() {
  const user = useAuthStore(state => state.user);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [view, setView] = useState<"attention" | "history">("attention");
  const query = useQuery({queryKey: [...queryKeys.reporting.obligations, "mine", user?.company, user?.id], queryFn: reportingSchedulesApi.obligations});
  const start = useMutation({mutationFn: reportingSchedulesApi.startObligation, onSuccess: (result) => {
    void queryClient.invalidateQueries({queryKey: queryKeys.reporting.obligations});
    router.push(`/forms/submissions/${result.submission_id}`);
  }});
  const items = (query.data ?? []).filter(item => needsWork.has(item.status) === (view === "attention"))
    .sort((a,b) => Date.parse(a.due_at) - Date.parse(b.due_at));
  return <div className="space-y-6">
    <PageHeader title="Reports due" description="Your assigned reports, with a clear next step for each one."/>
    <div className="sb-context-note"><ClipboardList size={22} className="shrink-0" aria-hidden="true"/><div><h2 className="font-semibold">Complete your company’s prepared report</h2><p className="mt-1 text-sm text-[var(--muted)]">Start a draft, fill in the fields and review your answers before submitting. Returned reports will explain what needs changing.</p></div></div>
    <div className="sb-local-nav" role="group" aria-label="Report views">{(["attention", "history"] as const).map(tab => <button key={tab} className={`sb-action-link ${view === tab ? "bg-[var(--accent-soft)] text-[var(--accent-text)]" : ""}`} aria-pressed={view === tab} onClick={() => setView(tab)}>{tab === "attention" ? `To complete${query.isSuccess ? ` (${(query.data ?? []).filter(item => needsWork.has(item.status)).length})` : ""}` : `Submitted & closed${query.isSuccess ? ` (${(query.data ?? []).filter(item => !needsWork.has(item.status)).length})` : ""}`}</button>)}</div>
    {start.isError && <p role="alert" className="sb-workspace-panel">We couldn’t start this report. Please try again. If the deadline has passed, ask your company administrator whether late reporting is allowed.</p>}
    {query.isError ? <ErrorState title="Unable to load your reports" description="Please try again. Your saved work has not changed." onRetry={() => void query.refetch()}/> : query.isPending ? <div className="h-32 animate-pulse rounded-xl bg-[var(--surface)]" role="status" aria-label="Loading reports"/> : items.length === 0 ? <EmptyState icon={<ClipboardList size={28}/>} title={view === "attention" ? "No reports need your attention" : "No submitted reports yet"} description={view === "attention" ? "Reports assigned to you will appear here with their due dates." : "Once you submit a scheduled report, you can check its progress here."} action={<Link href="/forms" className="sb-action-link">Browse company forms →</Link>}/> : <div className="grid gap-4 lg:grid-cols-2">{items.map(item => <section key={item.id} className="sb-explore-card flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold">{item.template.name}</h2><p className="mt-1 text-sm text-[var(--muted)]">{item.schedule.name} · Due {formatDateTime(item.due_at)}</p><span className="sb-soft-badge mt-3">{statusLabels[item.status] ?? formatEnumLabel(item.status)}</span></div>{item.submission ? <Link className="sb-action-link" href={`/forms/submissions/${item.submission}`}>{needsWork.has(item.status) ? "Continue report →" : "View report →"}</Link> : needsWork.has(item.status) ? <Button disabled={start.isPending} loading={start.isPending && start.variables === item.id} onClick={() => start.mutate(item.id)}>Start report</Button> : null}</section>)}</div>}
  </div>;
}
