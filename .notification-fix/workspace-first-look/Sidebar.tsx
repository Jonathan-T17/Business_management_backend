"use client";
import { useQuery } from "@tanstack/react-query";
import { companySetupApi } from "@/api/companySetupApi";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment, useState } from "react";
import { LogOut, Search, X } from "lucide-react";
import { useNavigationDrawer } from "@/hooks/useNavigationDrawer";
import { workspaceGroups as sections, workspaceFor as sectionFor, visibleNavigation, activeNavigation } from "./workspaces";
import { useAuthStore } from "@/store/authStore";


interface SidebarProps {
  mobileOpen: boolean;
  onMobileOpenChange: (open: boolean) => void;
}

export function Sidebar({ mobileOpen, onMobileOpenChange }: SidebarProps) {
  const pathname = usePathname();
  const drawerRef = useNavigationDrawer(mobileOpen, () => onMobileOpenChange(false));
  const [search, setSearch] = useState("");
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const user = useAuthStore((state) => state.user);
  const {data: workspace} = useQuery({queryKey:["company-setup","access",user?.id],queryFn:companySetupApi.access,enabled:Boolean(user?.company),staleTime:60000});

  if (!user) return null;

  const allNavigation = visibleNavigation(user);
  const selected = activeNavigation(pathname, allNavigation);
  const navigation = allNavigation.filter(item => `${item.label} ${sectionFor(item.href)}`.toLowerCase().includes(search.trim().toLowerCase()))
    .sort((a, b) => sections.indexOf(sectionFor(a.href)) - sections.indexOf(sectionFor(b.href)));
  const navigate = () => { setSearch(""); onMobileOpenChange(false); };
  const primaryRoutes = ["/dashboard", "/forms", "/reporting/obligations", "/materials", "/requests", "/approvals", "/company", "/documents", "/analytics", "/settings", "/support"];
  const primary = primaryRoutes.flatMap(href => allNavigation.filter(item => item.href === href));
  const secondary = navigation.filter(item => !primaryRoutes.includes(item.href));

  const content = (
    <div className="sb-sidebar flex h-full flex-col">
      <div className="flex h-16 items-center justify-between border-b sb-sidebar-divider border-neutral-200 px-5">
        <Link
          href="/dashboard"
          onClick={() => onMobileOpenChange(false)}
          className="flex min-w-0 items-center gap-3"
        >
          <div className="sb-brand flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-neutral-950 font-bold text-white">
            S
          </div>
          <div className="min-w-0">
            <p className="sb-brand-name truncate font-semibold text-neutral-950">SmartBiz AI</p>
            <p className="sb-sidebar-muted truncate text-xs text-neutral-500">
              {user.company_name || workspace?.company_name || "Company workspace"}
            </p>
          </div>
        </Link>

        <button
          type="button"
          onClick={() => onMobileOpenChange(false)}
          className="rounded-md p-2 text-neutral-600 hover:bg-neutral-100 lg:hidden"
          aria-label="Close navigation"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="px-3 pt-4 pb-2">
        <label className="sb-nav-search flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3 focus-within:ring-2 focus-within:ring-teal-600">
          <Search size={16} aria-hidden="true" />
          <input aria-label="Find a workspace page" placeholder="Find a page…" value={search} onChange={(event) => setSearch(event.target.value)} className="h-10 min-w-0 w-full bg-transparent text-sm outline-none" />
        </label>
        {navigation.length === 0 && <p className="p-3 text-sm text-neutral-500" role="status">No matching pages.</p>}
      </div>
      {workspace?.setup_required && !user.awaiting_position && allNavigation.some(item => item.href === "/settings/onboarding") && <Link href="/settings/onboarding" onClick={navigate} className="mx-3 mt-2 rounded-xl border border-teal-400/50 bg-teal-900 px-3 py-3 text-sm font-semibold text-white">Continue company setup →</Link>}
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Primary navigation">
        {!search.trim() && primary.map(item => { const Icon = item.icon; const active = selected?.href === item.href; return <Link key={item.href} href={item.href} onClick={navigate} aria-current={active ? "page" : undefined} className="sb-nav-link flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium"><Icon className="h-5 w-5 shrink-0" aria-hidden="true"/><span>{item.label}</span></Link>; })}
        <details className="pt-2" open={search.trim() || (selected && !primaryRoutes.includes(selected.href)) ? true : undefined}><summary className="sb-nav-heading min-h-11 cursor-pointer">{search.trim() ? "Search results" : "More workspace pages"}</summary>
        {(search.trim() ? navigation : secondary).map((item, index, listed) => {
          const active = selected?.href === item.href;
          const Icon = item.icon;
          const section = sectionFor(item.href);
          const sectionActive = selected && sectionFor(selected.href) === section;
          const expanded = Boolean(search.trim()) || (expandedGroups[section] ?? (sectionActive || section === "Overview"));

          return (
            <Fragment key={item.href}>
            {(index === 0 || sectionFor(listed[index-1].href) !== sectionFor(item.href)) && <button type="button" className="sb-nav-heading flex w-full items-center justify-between" aria-expanded={expanded} onClick={() => setExpandedGroups(current => ({...current, [section]: !expanded}))}>{section}<span aria-hidden="true">{expanded ? "−" : "+"}</span></button>}
            {expanded && <Link
              key={item.href}
              href={item.href}
              onClick={navigate}
              aria-current={active ? "page" : undefined}
              className={[
                "sb-nav-link flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                active
                  ? "bg-teal-700 text-white shadow-sm"
                  : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-950",
              ].join(" ")}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span>{item.label}</span>{item.href === "/settings/onboarding" && workspace?.setup_required && <span className="ml-auto rounded bg-white/15 px-2 py-0.5 text-xs">Next</span>}
            </Link>}
            </Fragment>
          );
        })}
        </details>
      </nav>

      <div className="sb-sidebar-divider border-t border-neutral-200 p-4">
        <div className="sb-brand-name truncate text-sm font-medium text-neutral-950">
          {user.full_name}
        </div>
        <div className="sb-sidebar-muted truncate text-xs text-neutral-500">{user.email}</div>

        <Link
          href="/logout"
          className="mt-4 flex min-h-11 items-center gap-2 rounded-lg px-2 text-sm font-medium text-red-700 hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </Link>
      </div>
    </div>
  );

  return (
    <>
      <aside className="sb-sidebar fixed inset-y-0 left-0 z-40 hidden w-64 border-r lg:block">
        {content}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation overlay"
            className="absolute inset-0 bg-black/40"
            onClick={() => onMobileOpenChange(false)}
          />
          <aside ref={drawerRef} role="dialog" aria-modal="true" aria-label="Workspace navigation" className="sb-sidebar relative h-full w-[min(20rem,85vw)] shadow-xl">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
