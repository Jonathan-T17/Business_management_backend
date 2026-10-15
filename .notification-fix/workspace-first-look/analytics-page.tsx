"use client";

import { useState } from "react";
import { AnalyticsUnavailable } from "@/components/analytics/AnalyticsUnavailable";
import Link from "next/link";
import { BrainCircuit } from "lucide-react";

import { RequireCapability } from "@/components/auth/RequireCapability";
import { AnalyticsOverview } from "@/components/analytics/AnalyticsOverview";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { useAnalytics } from "@/hooks/useAnalytics";
import { CAPABILITIES } from "@/utils/capabilities";

export default function AnalyticsPage() {
  return (
    <RequireCapability
      capabilities={[
        CAPABILITIES.VIEW_COMPANY_ANALYTICS,
        CAPABILITIES.VIEW_EXECUTIVE_DASHBOARD,
      ]}
      fallback={<div className="rounded-lg bg-red-50 p-5 text-red-700">You are not authorized to view analytics.</div>}
    >
      <AnalyticsContent />
    </RequireCapability>
  );
}

function AnalyticsContent() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [range, setRange] = useState<{ start_date?: string; end_date?: string }>({});
  const invalidRange = Boolean(startDate && endDate && startDate > endDate);
  const { data: overview, isLoading, isFetching, error, refetch } = useAnalytics(range);


  return (
    <div className="space-y-7">
      <PageHeader
        title="Charts & insights"
        description="Explore company activity, saved form entries and request decisions available to you."
        action={<Link href="/analytics/insights"><Button variant="outline" iconLeft={<BrainCircuit size={16} />}>Insights</Button></Link>}
      />
      <form className="sb-workspace-panel space-y-3" onSubmit={event => { event.preventDefault(); if (!invalidRange) setRange({ ...(startDate ? {start_date: startDate} : {}), ...(endDate ? {end_date: endDate} : {}) }); }}>
        <p className="text-sm text-neutral-600">Filter by record creation date, including both selected dates. Leave dates blank to include all dates.</p>
        <div className="flex flex-wrap items-end gap-4">
          <label className="text-sm font-medium">From<input type="date" value={startDate} onChange={event => setStartDate(event.target.value)} className="mt-1 block rounded-lg border border-neutral-300 p-2" /></label>
          <label className="text-sm font-medium">To<input type="date" value={endDate} min={startDate || undefined} onChange={event => setEndDate(event.target.value)} className="mt-1 block rounded-lg border border-neutral-300 p-2" /></label>
          <Button type="submit" disabled={invalidRange || isFetching}>Apply dates</Button>
          <Button type="button" variant="outline" disabled={isFetching} onClick={() => { setStartDate(""); setEndDate(""); setRange({}); }}>Clear dates</Button>
          <Button type="button" variant="outline" disabled={isFetching} onClick={() => refetch()}>{isFetching ? "Refreshing..." : "Refresh summaries"}</Button>
        </div>
        {invalidRange && <p role="alert" className="text-sm text-red-700">End date must be on or after start date.</p>}
        <p role="status" className="text-xs text-neutral-500">Showing: {range.start_date || "all earlier dates"} to {range.end_date || "all later dates"}.</p>
      </form>
      {isLoading ? <div className="h-48 animate-pulse rounded-lg bg-neutral-200" /> : error ? <AnalyticsUnavailable error={error} onRetry={() => void refetch()}/> : overview ? <AnalyticsOverview overview={overview} /> : <div className="rounded-lg border border-dashed border-neutral-300 p-10 text-center text-sm text-neutral-600">No activity summaries are available to your account yet.</div>}
    </div>
  );
}