"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Building2, ChartColumn, ClipboardCheck, FileText, FolderOpen, Package, Settings, Users } from "lucide-react";
import { companySetupApi } from "@/api/companySetupApi";
import { PersonalWork } from "@/components/dashboard/PersonalWork";
import { useAuthStore } from "@/store/authStore";
import { workspaceAccess } from "@/utils/workspace";
import { useAnalytics } from "@/hooks/useAnalytics";
import { AnalyticsUnavailable } from "@/components/analytics/AnalyticsUnavailable";
import { AnalyticsOverview } from "@/components/analytics/AnalyticsOverview";

function CompanyInsights() {
  const query = useAnalytics({});
  return <section id="company-performance" className="scroll-mt-24 space-y-4" aria-labelledby="company-performance-title">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="sb-eyebrow">Company activity</p><h2 id="company-performance-title" className="mt-1 text-xl font-semibold">A clear picture of your work</h2><p className="mt-1 text-sm text-[var(--muted)]">All dates · Forms and requests available to your account.</p></div><Link className="sb-action-link" href="/analytics"><ChartColumn size={18}/>Charts &amp; insights<ArrowUpRight size={16}/></Link></div>
    {query.isPending ? <div className="sb-workspace-panel" role="status">Preparing your activity overview…</div> : query.isError ? <AnalyticsUnavailable error={query.error} onRetry={() => void query.refetch()}/> : query.data ? <AnalyticsOverview overview={query.data}/> : <p>No activity yet.</p>}
  </section>;
}

export default function DashboardPage() {
  const user = useAuthStore(state => state.user);
  const access = workspaceAccess(user);
  const company = useQuery({queryKey: ["company-setup", "access", user?.id], queryFn: companySetupApi.access, enabled: Boolean(user?.company), staleTime: 60000});
  const name = company.data?.company_name || user?.company_name || "Your company workspace";
  const actions = [
    ...(access.forms ? [{href: "/forms", title: "Fill in a form", detail: "Choose a company form and start an entry.", icon: FileText}, {href: "/materials", title: "Materials & deliveries", detail: "Follow supplies from request to receipt.", icon: Package}] : []),
    {href: "/reporting/obligations", title: "My reports", detail: "See what is due and continue saved work.", icon: ClipboardCheck},
    {href: "/requests", title: "My requests", detail: "Send a request or check its progress.", icon: ArrowUpRight},
    {href: "/approvals", title: "Reviews", detail: "Open decisions assigned to you.", icon: ClipboardCheck},
    {href: "/documents", title: "Documents", detail: "Find information shared with you.", icon: FolderOpen},
  ];
  return <div className="space-y-6">
    <header className="sb-home-hero"><div className="relative min-w-0 flex-1"><p className="sb-eyebrow">{name}</p><h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Welcome back{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}.</h1><p className="mt-3 max-w-xl text-sm text-[var(--muted)]">Your people, daily work and company activity, connected in one place.</p><div className="mt-4 flex flex-wrap gap-2"><span className="sb-soft-badge">Company workspace</span>{user?.position_name && <span className="sb-soft-badge">{user.position_name}</span>}{user?.branch_name && <span className="sb-soft-badge">{user.branch_name}</span>}</div></div><div className="relative flex flex-wrap items-start gap-2">{access.setup ? <Link className="sb-primary-link" href={company.data?.setup_required ? "/settings/onboarding" : "/settings"}><Settings size={18}/>{company.data?.setup_required ? "Continue company setup" : "Company administration"}<ArrowUpRight size={16}/></Link> : access.forms ? <Link className="sb-primary-link" href="/forms"><FileText size={18}/>Open company forms</Link> : <Link className="sb-action-link" href="/settings/profile">My profile<ArrowUpRight size={16}/></Link>}</div></header>
    {access.analytics && <CompanyInsights/>}
    <div className="grid items-start gap-5 xl:grid-cols-[1.1fr_1fr]"><PersonalWork/><section className="sb-workspace-panel" aria-labelledby="quick-work-title"><p className="sb-eyebrow">Everyday work</p><h2 id="quick-work-title" className="mt-1 text-xl font-semibold">Where would you like to start?</h2><div className="mt-4 grid gap-2 sm:grid-cols-2">{actions.map(action => <Link key={action.href} href={action.href} className="sb-home-shortcut"><span className="sb-home-shortcut-icon"><action.icon size={20}/></span><div className="min-w-0"><h3 className="text-sm font-semibold">{action.title}</h3><p className="mt-1 text-xs leading-5 text-[var(--muted)]">{action.detail}</p></div><ArrowUpRight size={15} className="shrink-0 text-[var(--muted)]" aria-hidden="true"/></Link>)}</div></section></div>
    {!access.forms && user && ["EMPLOYEE", "MANAGER"].includes(user.role) && <section className="sb-context-note"><Users size={24} className="shrink-0 text-[var(--accent-text)]"/><div><h2 className="font-semibold">Your work access is being prepared</h2><p className="mt-1 text-sm text-[var(--muted)]">Ask your company administrator to confirm your position and the work available to you.</p><Link href="/settings/profile" className="sb-text-link mt-2">Check my profile<ArrowUpRight size={16}/></Link></div></section>}
    {(access.structure || access.people || access.formManagement || access.organization) && <section className="space-y-3" aria-labelledby="company-explore-title"><div className="flex flex-wrap items-center justify-between gap-3"><h2 id="company-explore-title" className="text-xl font-semibold">Your company, organised</h2>{access.organization && <Link className="sb-text-link" href="/settings">Company administration<ArrowUpRight size={16}/></Link>}</div><div className="grid gap-3 md:grid-cols-3">{access.structure && <Link href="/company" className="sb-explore-card"><Building2 size={25} className="text-[var(--accent-text)]"/><h3 className="mt-3 font-semibold">Head office &amp; branches</h3><p className="mt-1 text-sm text-[var(--muted)]">Explore your company structure and responsibilities.</p><span className="sb-text-link mt-3">Open company map<ArrowUpRight size={16}/></span></Link>}{access.people && <Link href="/employees" className="sb-explore-card"><Users size={25} className="text-[var(--accent-text)]"/><h3 className="mt-3 font-semibold">People</h3><p className="mt-1 text-sm text-[var(--muted)]">Find colleagues and manage permitted assignments.</p><span className="sb-text-link mt-3">Open people<ArrowUpRight size={16}/></span></Link>}{access.formManagement && <Link href="/forms" className="sb-explore-card"><FileText size={25} className="text-[var(--accent-text)]"/><h3 className="mt-3 font-semibold">Company forms</h3><p className="mt-1 text-sm text-[var(--muted)]">Choose, review and publish forms for your people.</p><span className="sb-text-link mt-3">Open forms<ArrowUpRight size={16}/></span></Link>}</div></section>}
    <Link href="/support" className="sb-text-link">Need a hand? Help &amp; support<ArrowUpRight size={16}/></Link>
  </div>;
}