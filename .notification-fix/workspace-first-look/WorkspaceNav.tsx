"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { activeNavigation, visibleNavigation, workspaceFor } from "./workspaces";

const localRoutes: Record<string, string[]> = {
  "Forms & reporting": ["/forms", "/materials", "/reporting/obligations", "/reports", "/settings/forms"],
  "Requests & approvals": ["/requests", "/approvals"],
  "Company & people": ["/company", "/employees", "/employees/invite", "/employees/positions", "/users"],
  "Documents & records": ["/documents", "/records"],
};

export function WorkspaceNav() {
  const pathname = usePathname();
  const user = useAuthStore(state => state.user);
  if (!user || user.awaiting_position || pathname === "/dashboard" || pathname === "/settings/onboarding" || pathname === "/settings/roles-permissions" || ["/settings/profile", "/settings/security", "/settings/notifications"].includes(pathname)) return null;
  if(pathname === "/forms" || pathname.startsWith("/forms/") || pathname.startsWith("/settings/forms")) return null;
  const group = workspaceFor(pathname);
  const available = visibleNavigation(user);
  const tabs = (localRoutes[group] ?? []).flatMap(href => available.filter(item => item.href === href));
  const current = activeNavigation(pathname, available);
  const activeTab = activeNavigation(pathname, tabs);
  return <div className="sb-workspace-nav mb-6 space-y-3">
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2 text-sm text-[var(--muted)]">
      <Link className="hover:underline" href="/dashboard">Home</Link><ChevronRight size={14} aria-hidden="true"/>
      <span>{group === "Company settings" ? "Company administration" : group}</span>
      {current && pathname !== current.href && <><ChevronRight size={14} aria-hidden="true"/><Link className="underline" href={current.href}>{current.label}</Link><ChevronRight size={14} aria-hidden="true"/><span>Details</span></>}
    </nav>
    {tabs.length > 1 && <nav aria-label={`${group} pages`} className="sb-local-nav">{tabs.map(item => <Link key={item.href} href={item.href} aria-current={activeTab?.href === item.href ? "page" : undefined}>{item.label}</Link>)}</nav>}
    {group === "Company settings" && pathname !== "/settings" && <Link className="inline-block text-sm text-[var(--accent-text)] underline" href="/settings">Back to company administration</Link>}
  </div>;
}
