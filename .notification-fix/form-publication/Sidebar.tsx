"use client";
import { useQuery } from "@tanstack/react-query";
import { companySetupApi } from "@/api/companySetupApi";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { LogOut, Search, X } from "lucide-react";
import { useNavigationDrawer } from "@/hooks/useNavigationDrawer";
import { workspaceFor as sectionFor, visibleNavigation, activeNavigation } from "./workspaces";
import { useAuthStore } from "@/store/authStore";


interface SidebarProps {
  mobileOpen: boolean;
  onMobileOpenChange: (open: boolean) => void;
}

export function Sidebar({ mobileOpen, onMobileOpenChange }: SidebarProps) {
  const pathname = usePathname();
  const drawerRef = useNavigationDrawer(mobileOpen, () => onMobileOpenChange(false));
  const [search, setSearch] = useState("");
  const user = useAuthStore((state) => state.user);
  const {data: workspace} = useQuery({queryKey:["company-setup","access",user?.id],queryFn:companySetupApi.access,enabled:Boolean(user?.company),staleTime:60000});

  if (!user) return null;

  const allNavigation = visibleNavigation(user);
  const selected = activeNavigation(pathname, allNavigation);
  const groups = ["Home", "Daily work", "Company", "Administration", "My account & help", "Planning"];
  const groupFor = (href:string) => href === "/dashboard" ? "Home" : ["/analytics", "/company", "/employees", "/documents", "/activity", "/branches", "/departments", "/teams", "/records", "/data-tools"].includes(href) ? "Company" : ["Forms & reporting", "Requests & approvals"].includes(sectionFor(href)) ? "Daily work" : sectionFor(href) === "Optional planning" ? "Planning" : ["My account", "Communication"].includes(sectionFor(href)) ? "My account & help" : "Administration";
  const navigation = allNavigation.filter(item => `${item.label} ${groupFor(item.href)}`.toLowerCase().includes(search.trim().toLowerCase()));
  const navigate = () => { setSearch(""); onMobileOpenChange(false); };

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
        {groups.map(group => {const items=navigation.filter(item=>groupFor(item.href)===group);return !items.length?null:<section key={group} aria-label={group} className="pt-2"><h2 className="sb-nav-heading">{group}</h2>{items.map(item=>{const Icon=item.icon;const active=selected?.href===item.href;return <Link key={item.href} href={item.href} onClick={navigate} aria-current={active?"page":undefined} className="sb-nav-link flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium"><Icon className="h-5 w-5 shrink-0" aria-hidden="true"/><span>{item.label}</span></Link>;})}</section>;})}
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
