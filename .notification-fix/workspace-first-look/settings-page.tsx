"use client";
import Link from "next/link";
import { Building2, Users, ClipboardList, Route, Bell, FolderOpen, Settings, ArrowUpRight, UserRound, ShieldCheck } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { CAPABILITIES as C, hasAnyCapability } from "@/utils/capabilities";
import { workspaceAccess } from "@/utils/workspace";
import PageHeader from "@/components/ui/PageHeader";
import { ResponsibilityGuide } from "@/components/company/ResponsibilityGuide";

export default function SettingsPage() {
  const user = useAuthStore(state => state.user);
  const access = workspaceAccess(user);
  const has = (...caps: Parameters<typeof hasAnyCapability>[1][number][]) => hasAnyCapability(user?.capabilities, caps);
  const groups = [
    {title: "Company & people", icon: Building2, description: "Your identity, locations and responsibilities.", items: [
      {label: "Company profile", href: "/settings/company-profile", show: access.setup},
      {label: "Head office & branches", href: "/company", show: access.structure},
      {label: "People & invitations", href: "/employees", show: access.people},
      {label: "Positions & access", href: "/settings/roles-permissions", show: access.setup},
    ]},
    {title: "Forms & decisions", icon: ClipboardList, description: "Prepare forms, reporting schedules and review steps.", items: [
      {label: "Company forms & library", href: "/settings/forms", show: access.formManagement},
      {label: "Reporting processes", href: "/settings/reporting", show: access.setup},
      {label: "Approval routes", href: "/settings/approval-routes", show: access.setup},
      {label: "Request types", href: "/settings/request-types", show: has(C.MANAGE_REQUEST_TYPES)},
    ]},
    {title: "Documents & field work", icon: FolderOpen, description: "Organise documents, official records and field requirements.", items: [
      {label: "Document categories", href: "/settings/documents", show: access.documents},
      {label: "Official record rules", href: "/settings/official-records", show: access.setup},
      {label: "Field operations", href: "/settings/field-operations", show: has(C.MANAGE_FIELD_OPERATIONS)},
    ]},
    {title: "Company preferences", icon: Settings, description: "Company notifications, starting templates and subscription.", items: [
      {label: "Company notifications", href: "/settings/notifications/policies", show: access.setup},
      {label: "Industry templates", href: "/settings/templates", show: access.setup},
      {label: "Subscription & usage", href: "/subscriptions", show: access.setup},
    ]},
  ].map(group => ({...group, items: group.items.filter(item => item.show)})).filter(group => group.items.length);
  if (!access.organization) return <div className="space-y-6"><PageHeader title="My account" description="Manage your profile, preferences and account security."/><div className="grid gap-4 sm:grid-cols-3">{[{title: "Profile", href: "/settings/profile", icon: UserRound}, {title: "Notifications", href: "/settings/notifications", icon: Bell}, {title: "Security", href: "/settings/security", icon: ShieldCheck}].map(item => <Link key={item.href} href={item.href} className="sb-explore-card"><item.icon size={24}/><h2 className="mt-3 font-semibold">{item.title} →</h2></Link>)}</div></div>;
  return <div className="space-y-6"><PageHeader title="Company administration" description="Manage your company structure, people, forms and preferences in one place." action={<Link href="/settings/profile" className="sb-action-link"><UserRound size={17}/>My account</Link>}/>
    {access.setup && <section className="sb-context-note"><Route size={25} className="shrink-0 text-[var(--accent-text)]"/><div className="flex-1"><h2 className="font-semibold">Need the step-by-step route?</h2><p className="mt-1 text-sm text-[var(--muted)]">Guided setup keeps your saved company structure, access and forms together.</p><Link className="sb-text-link mt-2" href="/settings/onboarding">Review company setup <ArrowUpRight size={16}/></Link></div></section>}
    <div className="grid gap-4 md:grid-cols-2">{groups.map(group => <section className="sb-workspace-panel" key={group.title}><group.icon size={24} className="text-[var(--accent-text)]"/><h2 className="mt-3 text-lg font-semibold">{group.title}</h2><p className="mt-1 text-sm text-[var(--muted)]">{group.description}</p><ul className="mt-4 divide-y divide-[var(--line)]">{group.items.map(item => <li key={item.href}><Link href={item.href} className="flex items-center justify-between gap-3 rounded-lg py-3 text-sm font-medium hover:text-[var(--accent-text)]">{item.label}<ArrowUpRight size={16} aria-hidden="true"/></Link></li>)}</ul></section>)}</div>
    {access.setup && <details className="sb-disclosure"><summary>Administrator, owner and CEO: who does what?</summary><div className="mt-4"><ResponsibilityGuide/></div></details>}
    <Link href="/support" className="sb-text-link"><Users size={17}/>Need help configuring your company? →</Link>
  </div>;
}
