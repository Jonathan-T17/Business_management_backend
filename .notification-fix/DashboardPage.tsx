"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FileText, ClipboardCheck, FolderOpen, ArrowUpRight, Network, Users, Settings, ChartColumn } from "lucide-react";
import { companySetupApi } from "@/api/companySetupApi";
import CompanyStructureMap from "@/components/company/CompanyStructureMap";
import { ResponsibilityGuide } from "@/components/company/ResponsibilityGuide";
import { PersonalWork } from "@/components/dashboard/PersonalWork";
import { useAuthStore } from "@/store/authStore";
import { workspaceAccess } from "@/utils/workspace";
import { useAnalytics } from "@/hooks/useAnalytics";
import { AnalyticsUnavailable } from "@/components/analytics/AnalyticsUnavailable";
import { AnalyticsOverview } from "@/components/analytics/AnalyticsOverview";
import { CAPABILITIES, hasAnyCapability } from "@/utils/capabilities";

function CompanyInsights() {
  const query = useAnalytics({});
  return <section id="company-performance" className="scroll-mt-24 space-y-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="sb-eyebrow">Understand the activity</p><h2 className="mt-1 text-xl font-semibold">Performance & charts</h2></div><Link className="sb-text-link" href="/analytics">Explore analytics <ArrowUpRight size={16}/></Link></div>{query.isPending ? <p role="status">Loading activity…</p> : query.isError ? <AnalyticsUnavailable error={query.error} onRetry={() => void query.refetch()}/> : query.data ? <AnalyticsOverview overview={query.data}/> : <p>No activity yet.</p>}</section>;
}

export default function DashboardPage() {
  const user = useAuthStore(state => state.user);
  const access = workspaceAccess(user);
  const company = useQuery({queryKey: ["company-setup", "access", user?.id], queryFn: companySetupApi.access, enabled: Boolean(user?.company), staleTime: 60000});
  const [showMap, setShowMap] = useState(false);
  const name = company.data?.company_name || user?.company_name || "Your workspace";
  const actions = [
    {href: "/reporting/obligations", title: "My reports", detail: "Complete assigned reports or check their progress.", icon: FileText},
    ...(access.forms ? [{href: "/materials", title: "Materials & deliveries", detail: "Follow requests, deliveries and receipts.", icon: FileText}] : []),
    ...(access.forms ? [{href: "/forms", title: "Complete a form", detail: "Find the right form for your work.", icon: FileText}] : []),
    {href: "/approvals", title: "Review approvals", detail: "Open work assigned to you for a decision.", icon: ClipboardCheck},
    {href: "/requests", title: "Track a request", detail: "Follow your requests and their progress.", icon: ArrowUpRight},
    {href: "/documents", title: "Find a document", detail: "Open the documents available to you.", icon: FolderOpen},
  ];
  return <div className="space-y-7">
    <header className="sb-overview-header"><div><p className="sb-eyebrow">{name}</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Your work, at a glance</h1><p className="mt-2 text-sm text-[var(--muted)]">Welcome back{user?.full_name ? `, ${user.full_name}` : ""}. Pick up your work or explore your company.</p>{(user?.branch_name || user?.position_name) && <div className="mt-4 flex flex-wrap gap-2">{user.position_name && <span className="sb-soft-badge">{user.position_name}</span>}{user.branch_name && <span className="sb-soft-badge">{user.branch_name}</span>}</div>}</div><div className="flex flex-wrap gap-2">{access.analytics && <Link href="#company-performance" className="sb-action-link"><ChartColumn size={17}/>Performance & charts</Link>}{access.invite && <Link href="/employees/invite" className="sb-action-link"><Users size={17}/>Invite employees</Link>}</div></header>
    <section aria-label="Start your work" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{actions.map(action => <Link key={action.href} href={action.href} className="sb-explore-card"><action.icon size={23} className="text-[var(--accent-text)]"/><h2 className="mt-4 font-semibold">{action.title}</h2><p className="mt-1 text-sm text-[var(--muted)]">{action.detail}</p></Link>)}</section>
    {!access.forms && user && ["EMPLOYEE", "MANAGER"].includes(user.role) && <section className="sb-context-note" aria-labelledby="work-access-title"><Users size={23} className="shrink-0 text-[var(--accent-text)]" aria-hidden="true"/><div><h2 id="work-access-title" className="font-semibold">Your work access needs to be configured</h2><p className="mt-1 text-sm text-[var(--muted)]">{user.position_name ? `Your position is ${user.position_name}. ` : ""}Ask your company administrator to confirm the forms and permissions for your position. Assigned approvals and reports will appear in their workspaces. Position titles alone do not give access to company information.</p><Link href="/settings/profile" className="sb-text-link mt-3 inline-block">Check my profile <ArrowUpRight size={16}/></Link></div></section>}
    <PersonalWork/>
    {(access.setup || access.people || access.formManagement || access.organization) && <section className="sb-workspace-panel" aria-labelledby="manage-workspace"><div className="flex items-center gap-2"><Settings size={19} className="text-[var(--accent-text)]"/><h2 id="manage-workspace" className="text-lg font-semibold">Manage your workspace</h2></div><p className="mt-2 text-sm text-[var(--muted)]">Keep your people, forms and company arrangements up to date.</p><div className="mt-4 flex flex-wrap gap-3">{access.people && <Link className="sb-action-link" href="/employees">People directory →</Link>}{access.formManagement && <Link className="sb-action-link" href="/settings/forms">Company form library →</Link>}{access.organization && <Link className="sb-action-link" href="/settings">Company settings →</Link>}</div></section>}
    {access.setup ? <section className="sb-company-explorer"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="sb-eyebrow">Your company, connected</p><h2 className="mt-1 text-xl font-semibold">Explore your company structure</h2><p className="mt-2 text-sm text-[var(--muted)]">Head office, branches and the people responsible, together.</p></div><Network size={34} className="text-[var(--accent-text)]" aria-hidden="true"/></div><div className="mt-4 flex flex-wrap gap-3"><button className="sb-action-link" aria-expanded={showMap} aria-controls="overview-company-map" onClick={() => setShowMap(open => !open)}>{showMap ? "Close map" : "Explore the map"}</button><Link className="sb-text-link" href="/company">Open company structure <ArrowUpRight size={16}/></Link></div><div id="overview-company-map">{showMap && <div className="mt-5"><CompanyStructureMap companyName={name}/></div>}</div></section> : access.structure ? <Link className="sb-explore-card block" href="/company"><h2 className="font-semibold">Explore company structure →</h2><p className="mt-2 text-sm text-[var(--muted)]">Find the offices, departments and people available to you.</p></Link> : null}
    {access.analytics && <CompanyInsights/>}
    {access.setup && <details className="sb-disclosure"><summary>Administrator, owner and CEO: who does what?</summary><div className="mt-4"><ResponsibilityGuide/></div></details>}
    <div className="flex flex-wrap justify-between gap-4 text-sm"><Link className="sb-text-link" href="/support">Need a hand? Help & support →</Link><details><summary className="cursor-pointer text-[var(--muted)]">Optional planning tools</summary><div className="mt-3 flex flex-wrap gap-4"><Link className="underline" href="/projects">Projects</Link><Link className="underline" href="/tasks">Tasks</Link>{hasAnyCapability(user?.capabilities, [CAPABILITIES.VIEW_COMPANY_PLANS, CAPABILITIES.MANAGE_COMPANY_PLANS]) && <Link className="underline" href="/planning">Planning</Link>}</div></details></div>
  </div>;
}
