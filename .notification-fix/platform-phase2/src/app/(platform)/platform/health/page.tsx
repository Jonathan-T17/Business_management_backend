"use client";
import { useQuery } from "@tanstack/react-query";
import { getPlatformHealth } from "@/api/platformApi";
const labels: Record<string, string> = {database: "Database", cache: "Cache", email_delivery: "Email delivery", reporting: "Reporting automation", storage: "Private storage", backups: "Backups & restore"};
const statusLabel: Record<string, string> = {healthy: "Healthy", unhealthy: "Needs attention", degraded: "Needs attention", partially_monitored: "Partially monitored", not_monitored: "Not monitored"};
export default function PlatformHealthPage() {
  const {data, isLoading, isError} = useQuery({queryKey: ["platform", "health"], queryFn: getPlatformHealth, refetchInterval: 30000});
  if (isLoading) return <p role="status">Checking services…</p>;
  if (isError || !data) return <p role="alert">Unable to retrieve service health. Try again shortly.</p>;
  const services: Record<string, {status:string;detail?:string;last_run?:string}> = data.services || {database:data.database,cache:data.cache};
  return <div className="space-y-6">
    <header><h1 className="text-2xl font-semibold">System health</h1><p className="mt-2 text-[var(--muted)]">See what is working, what needs attention, and what still needs monitoring.</p></header>
    <section className="rounded-2xl border border-amber-300/40 bg-[var(--surface)] p-5"><h2 className="font-semibold">{statusLabel[data.status] || data.status}</h2><p className="mt-2 text-sm text-[var(--muted)]">A healthy check covers that service only. Unmonitored services have no verified health evidence.</p><p className="mt-2 text-xs text-[var(--muted)]">Last checked {new Date(data.timestamp).toLocaleString()}</p></section>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Object.entries(services).map(([key, service]) => <section key={key} className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5"><h2 className="font-semibold">{labels[key] || key}</h2><p className={`mt-3 font-medium ${service.status === "healthy" ? "text-teal-700 dark:text-teal-300" : service.status === "unhealthy" ? "text-red-700 dark:text-red-300" : "text-amber-700 dark:text-amber-300"}`}>{statusLabel[service.status] || service.status}</p>{service.detail && <p className="mt-2 text-sm text-[var(--muted)]">{service.detail}</p>}{service.last_run && <p className="mt-2 text-xs text-[var(--muted)]">Last run {new Date(service.last_run).toLocaleString()}</p>}</section>)}</div>
  </div>;
}
