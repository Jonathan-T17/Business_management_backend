"use client";
import { useId } from "react";
import { ChartColumn, Clock3, TrendingUp, Building2 } from "lucide-react";
import type { AnalyticsOverview } from "@/types/analytics";
import { formatEnumLabel } from "@/utils/format";

const colors: Record<string, string> = { draft: "#94a3b8", submitted: "#38bdf8", under_review: "#f59e0b", approved: "#34d399", fulfilled: "#2dd4bf", rejected: "#fb7185", returned: "#a78bfa", cancelled: "#94a3b8", closed: "#818cf8" };
const colorFor = (key: string) => colors[key] ?? "#818cf8";
const labelFor = (key: string) => key === "under_review" ? "Being reviewed" : formatEnumLabel(key);
const number = (value: number) => value.toLocaleString();
const dateLabel = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

function Bars({ items }: { items: { label: string; value: number; color: string }[] }) {
  const maximum = Math.max(1, ...items.map(item => item.value));
  return <dl className="mt-5 space-y-3">{items.map(item => <div key={item.label}><div className="mb-1 flex justify-between gap-3 text-sm"><dt>{item.label}</dt><dd className="font-semibold tabular-nums">{number(item.value)}</dd></div><div aria-hidden="true" className="h-3 overflow-hidden rounded-full bg-[var(--surface-soft)]"><div className="h-full rounded-full" style={{ width: `${item.value / maximum * 100}%`, background: item.color }} /></div></div>)}</dl>;
}
function Empty({ title, help }: { title: string; help: string }) {
  return <div className="sb-chart-empty"><ChartColumn size={27} aria-hidden="true" /><p>{title}</p><span>{help}</span></div>;
}

export default function OperationsCharts({ overview, detailed = false }: { overview: AnalyticsOverview; detailed?: boolean }) {
  const id = useId();
  const requests = Object.entries(overview.requests ?? {}).map(([key, value]) => ({ label: labelFor(key), value, color: colorFor(key) }));
  const entries = Object.entries(overview.submissions ?? {}).filter(([, value]) => value > 0).map(([key, value]) => ({ label: labelFor(key), value, color: colorFor(key) }));
  const total = entries.reduce((sum, item) => sum + item.value, 0);
  const requestTotal = requests.reduce((sum, item) => sum + item.value, 0);
  const trend = overview.submission_trend ?? [];
  const hasActivity = trend.some(item => item.value > 0);
  const peak = Math.max(2, ...trend.map(item => item.value));
  const middle = Math.ceil(peak / 2);
  const points = trend.map((item, index) => ({ x: trend.length === 1 ? 300 : 44 + index / (trend.length - 1) * 512, y: 150 - item.value / peak * 120 }));
  const branches = overview.branch_activity ?? [];
  const branchMax = Math.max(1, ...branches.map(item => item.total));
  const segments = [{ key: "approved", label: "Approved", color: "#34d399" }, { key: "awaiting_review", label: "Awaiting review", color: "#38bdf8" }, { key: "returned", label: "Needs correction", color: "#a78bfa" }, { key: "other", label: "Other decisions", color: "#94a3b8" }] as const;
  const ages = overview.review_age ?? [];
  const waitingTotal = ages.reduce((sum, item) => sum + item.value, 0);
  return <div className="space-y-4">
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="sb-chart-panel" aria-labelledby={`${id}-entries`}><div className="flex items-start justify-between gap-3"><div><h3 id={`${id}-entries`} className="text-base font-semibold">Form entries at a glance</h3><p className="mt-1 text-sm text-[var(--muted)]">{number(total)} saved entries · compare each stage</p></div><span className="sb-chart-icon"><ChartColumn size={21} /></span></div>{total ? <Bars items={entries} /> : <Empty title="No saved entries yet" help="Save or submit a company form to start seeing activity." />}</section>
      <section className="sb-chart-panel" aria-labelledby={`${id}-requests`}><div className="flex items-start justify-between gap-3"><div><h3 id={`${id}-requests`} className="text-base font-semibold">Request decisions</h3><p className="mt-1 text-sm text-[var(--muted)]">Submitted requests and their progress.</p></div><span className="sb-chart-icon"><ChartColumn size={21} /></span></div>{requestTotal ? <Bars items={requests} /> : <Empty title="No submitted requests yet" help="Requests will appear as your team starts using this service." />}</section>
    </div>
    <section className="sb-chart-panel" aria-labelledby={`${id}-trend`}><div className="flex items-start justify-between gap-3"><div><h3 id={`${id}-trend`} className="text-base font-semibold">Daily form activity</h3><p className="mt-1 text-sm text-[var(--muted)]">Entries created each day · last {trend.length || 30} days of the selected period</p></div><span className="sb-chart-icon"><TrendingUp size={21} /></span></div>
      {hasActivity ? <><svg role="img" aria-label="Daily entry counts, including days with no activity. Exact values are available in the chart data table." viewBox="0 0 600 192" className="mt-3 h-48 w-full text-[var(--muted)]"><defs><linearGradient id={`${id}-fill`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--accent-text)" stopOpacity=".2" /><stop offset="100%" stopColor="var(--accent-text)" stopOpacity=".02" /></linearGradient></defs>{[0, middle, peak].map(value => <g key={value}><line x1="44" y1={150-value/peak*120} x2="556" y2={150-value/peak*120} stroke="currentColor" opacity=".16" strokeDasharray="4 5" /><text x="32" y={154-value/peak*120} textAnchor="end" fill="currentColor" fontSize="12">{value}</text></g>)}{points.length > 1 && <polygon points={`44,150 ${points.map(p => `${p.x},${p.y}`).join(" ")} 556,150`} fill={`url(#${id}-fill)`} />}<polyline fill="none" stroke="var(--accent-text)" strokeWidth="3" strokeLinejoin="round" points={points.map(p => `${p.x},${p.y}`).join(" ")} />{points.map((p, index) => <circle key={trend[index].date} cx={p.x} cy={p.y} r="3.5" fill="var(--accent-text)" stroke="var(--surface)" strokeWidth="1.5"><title>{`${dateLabel(trend[index].date)}: ${number(trend[index].value)} entries`}</title></circle>)}<text x="44" y="180" fill="currentColor" fontSize="12">{dateLabel(trend[0].date)}</text>{trend.length > 1 && <text x="556" y="180" textAnchor="end" fill="currentColor" fontSize="12">{dateLabel(trend[trend.length-1].date)}</text>}</svg><details className="text-sm"><summary className="min-h-11 cursor-pointer py-3 font-medium text-[var(--accent-text)]">View daily counts</summary><table className="w-full text-left"><caption className="sr-only">Entries created by date</caption><thead><tr><th scope="col" className="py-2">Date</th><th scope="col">Entries</th></tr></thead><tbody>{trend.map(item => <tr key={item.date} className="border-t border-[var(--line)]"><td className="py-2">{dateLabel(item.date)}</td><td className="tabular-nums">{number(item.value)}</td></tr>)}</tbody></table></details></> : <Empty title="No entries created in this period" help="Choose another period or start recording work with your company forms." />}
    </section>
    {detailed && <div className="grid gap-4 lg:grid-cols-2">
      <section className="sb-chart-panel" aria-labelledby={`${id}-branches`}><div className="flex items-start justify-between gap-3"><div><h3 id={`${id}-branches`} className="text-base font-semibold">Activity by branch</h3><p className="mt-1 text-sm text-[var(--muted)]">Recorded work and decisions · drafts and cancellations excluded</p></div><span className="sb-chart-icon"><Building2 size={21} /></span></div>{branches.length ? <><div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-[var(--muted)]">{segments.map(segment => <span key={segment.key} className="flex items-center gap-1.5"><span aria-hidden="true" className="h-2.5 w-2.5 rounded-sm" style={{background:segment.color}} />{segment.label}</span>)}</div><dl className="mt-5 space-y-4">{branches.map(branch => <div key={branch.branch_id ?? "none"}><div className="mb-1 flex justify-between gap-3 text-sm"><dt className="break-words font-medium">{branch.name}</dt><dd className="shrink-0 tabular-nums">{number(branch.total)} entries</dd></div><div aria-hidden="true" className="h-4 overflow-hidden rounded bg-[var(--surface-soft)]"><div className="flex h-full" style={{width:`${branch.total/branchMax*100}%`}}>{segments.map(segment => <span key={segment.key} className="h-full" style={{width:`${branch[segment.key]/branch.total*100}%`,background:segment.color}} />)}</div></div><div className="mt-1 flex flex-wrap gap-x-3 text-xs text-[var(--muted)]">{segments.map(segment => <span key={segment.key}>{segment.label}: {number(branch[segment.key])}</span>)}</div></div>)}</dl><p className="mt-4 text-xs text-[var(--muted)]">Entry counts reflect recorded activity, not branch quality or profitability.</p></> : <Empty title="No branch activity yet" help="Branch comparisons appear when employees submit forms with a branch recorded." />}</section>
      <section className="sb-chart-panel" aria-labelledby={`${id}-waiting`}><div className="flex items-start justify-between gap-3"><div><h3 id={`${id}-waiting`} className="text-base font-semibold">How long reviews have waited</h3><p className="mt-1 text-sm text-[var(--muted)]">{number(waitingTotal)} entries awaiting review · time since submission</p></div><span className="sb-chart-icon"><Clock3 size={21} /></span></div>{waitingTotal ? <Bars items={ages.map((item, index) => ({...item, color:["#38bdf8", "#f59e0b", "#fb7185", "#94a3b8"][index] ?? "#94a3b8"}))} /> : <Empty title="No reviews waiting" help="Pending entries will be grouped by how long they have been waiting." />}</section>
    </div>}
    <p className="text-xs text-[var(--muted)]">Charts include only records you can access. Dates use the system timezone; activity counts are separate from financial results.</p>
  </div>;
}
