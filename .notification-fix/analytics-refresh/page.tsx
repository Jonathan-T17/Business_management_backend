"use client";
import { useState } from "react";
import Link from "next/link";
import { BrainCircuit } from "lucide-react";
import { AnalyticsUnavailable } from "@/components/analytics/AnalyticsUnavailable";
import { RequireCapability } from "@/components/auth/RequireCapability";
import { AnalyticsOverview } from "@/components/analytics/AnalyticsOverview";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { useAnalytics } from "@/hooks/useAnalytics";
import type { AnalyticsParams } from "@/api/analyticsApi";
import { CAPABILITIES } from "@/utils/capabilities";

const localDate = (date: Date) => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}`;
const recent = (days: number) => { const end = new Date(); const start = new Date(end); start.setDate(start.getDate()-days+1); return {start_date:localDate(start),end_date:localDate(end)}; };
export default function AnalyticsPage() {
  return <RequireCapability capabilities={[CAPABILITIES.VIEW_COMPANY_ANALYTICS, CAPABILITIES.VIEW_EXECUTIVE_DASHBOARD]} fallback={<div className="sb-workspace-panel">You need analytics access to view company charts.</div>}><AnalyticsContent /></RequireCapability>;
}
function AnalyticsContent() {
  const [range, setRange] = useState<AnalyticsParams>(() => recent(30));
  const [startDate, setStartDate] = useState(range.start_date ?? "");
  const [endDate, setEndDate] = useState(range.end_date ?? "");
  const [branch, setBranch] = useState("");
  const invalidRange = Boolean(startDate && endDate && startDate > endDate);
  const {data: overview, isLoading, isFetching, error, refetch} = useAnalytics(range);
  const {data: available} = useAnalytics({});
  const input = "mt-1 block min-h-11 w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-[var(--ink)]";
  const applyPeriod = (days?: number) => { const dates = days ? recent(days) : {}; setStartDate(dates.start_date ?? ""); setEndDate(dates.end_date ?? ""); setRange({...dates,...(branch ? {branch} : {})}); };
  return <div className="space-y-6">
    <PageHeader title="Charts & insights" description="Understand recorded work, branch activity and the decisions waiting for attention." action={<Link href="/analytics/insights"><Button variant="outline" iconLeft={<BrainCircuit size={16} />}>Insights</Button></Link>} />
    <form className="sb-workspace-panel space-y-4" onSubmit={event => {event.preventDefault(); if (!invalidRange) setRange({...(startDate ? {start_date:startDate} : {}),...(endDate ? {end_date:endDate} : {}),...(branch ? {branch} : {})});}}>
      <div className="flex flex-wrap items-center gap-2"><span className="mr-1 text-sm font-medium">Quick periods</span>{[7,30,90].map(days => <Button key={days} type="button" variant="outline" disabled={isFetching} onClick={() => applyPeriod(days)}>Last {days} days</Button>)}<Button type="button" variant="outline" disabled={isFetching} onClick={() => applyPeriod()}>All dates</Button></div>
      <div className="grid items-end gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm font-medium">From<input type="date" value={startDate} onChange={event => setStartDate(event.target.value)} className={input} /></label>
        <label className="text-sm font-medium">To<input type="date" value={endDate} min={startDate || undefined} onChange={event => setEndDate(event.target.value)} className={input} /></label>
        <label className="text-sm font-medium">Branch<select value={branch} onChange={event => setBranch(event.target.value)} className={input}><option value="">All available branches</option>{(available?.branch_activity ?? []).filter(item => item.branch_id !== null).map(item => <option key={item.branch_id} value={String(item.branch_id)}>{item.name}</option>)}</select></label>
        <div className="flex flex-wrap gap-2"><Button type="submit" disabled={invalidRange || isFetching}>Apply filters</Button><Button type="button" variant="outline" disabled={isFetching} onClick={() => void refetch()}>{isFetching ? "Refreshing…" : "Refresh"}</Button></div>
      </div>
      {invalidRange && <p role="alert" className="text-sm text-[var(--danger-text)]">Choose an end date on or after the start date.</p>}
      <p role="status" className="text-xs text-[var(--muted)]">Showing entries created from {range.start_date || "the beginning"} to {range.end_date || "today"}. The daily chart shows the last 30 days within this period. Branch choices include recorded work you can access.</p>
    </form>
    {isLoading ? <div role="status" className="sb-workspace-panel animate-pulse">Preparing your charts…</div> : error ? <AnalyticsUnavailable error={error} onRetry={() => void refetch()} /> : overview ? <AnalyticsOverview overview={overview} detailed /> : <div className="sb-workspace-panel text-sm text-[var(--muted)]">No activity summaries are available yet.</div>}
  </div>;
}
