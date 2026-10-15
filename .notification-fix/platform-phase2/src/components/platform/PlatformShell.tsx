"use client";



import Link from "next/link";

import { usePathname } from "next/navigation";

import { useState } from "react";

import { LogOut, Menu, Search, ShieldCheck, X } from "lucide-react";

import { useNavigationDrawer } from "@/hooks/useNavigationDrawer";

import { useAuthStore } from "@/store/authStore";
import { platformPathAllowed } from "@/utils/platformAccess";
import { platformNavigation } from "./platformNavigation";

import { ThemeControl } from "@/components/theme/ThemeControl";

import { AppFooter } from "@/components/layout/AppFooter";



export function PlatformShell({ children }: { children: React.ReactNode }) {

  const pathname = usePathname();
  const user = useAuthStore(state => state.user);

  const [mobileOpen, setMobileOpen] = useState(false);

  const [search, setSearch] = useState("");

  const drawerRef = useNavigationDrawer(mobileOpen, () => setMobileOpen(false));

  const filtered = platformNavigation.filter(item => platformPathAllowed(item.href, user?.capabilities) && item.label.toLowerCase().includes(search.trim().toLowerCase()));

  const sections = ["Overview", "Customers", "Security", "Operations", "Configuration"].filter(section => filtered.some(item => item.section === section));



  const navigationContent = (

    <nav className="space-y-3 p-3" aria-label="Platform navigation">

      <label className="sb-nav-search flex items-center gap-2 rounded-xl px-3"><Search size={16} aria-hidden="true"/><input className="h-11 min-w-0 w-full text-sm outline-none" aria-label="Find a platform page" placeholder="Find a page…" value={search} onChange={event => setSearch(event.target.value)} /></label>

      {!filtered.length && <p className="sb-sidebar-muted p-3 text-sm" role="status">No matching pages.</p>}

      {sections.map((section) => (

        <div key={section}>

          <p className="sb-nav-heading px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">

            {section}

          </p>

          {filtered

            .filter((item) => item.section === section)

            .map((item) => {

              const active =

                (pathname === item.href || pathname.startsWith(`${item.href}/`)) && !platformNavigation.some((other) => other.href.length > item.href.length && (pathname === other.href || pathname.startsWith(`${other.href}/`)));

              return (

                <Link

                  key={item.href}

                  href={item.href}

                  onClick={() => setMobileOpen(false)}

                  aria-current={active ? "page" : undefined}

                  className={`sb-nav-link mb-1 flex items-center gap-3 rounded-md px-3 py-2.5 text-sm ${

                    active

                      ? "bg-cyan-400/15 text-cyan-200"

                      : "text-slate-300 hover:bg-slate-800"

                  }`}

                >

                  <item.icon size={17} />

                  {item.label}

                </Link>

              );

            })}

        </div>

      ))}

    </nav>

  );



  return (

    <div className="workspace-shell workspace-platform min-h-screen">

      <header className="sticky top-0 z-30 flex h-16 items-center border-b border-slate-800 bg-slate-950 px-4 text-white sm:px-6 lg:pl-[17.5rem]">

        <button

          type="button"

          aria-label="Open platform navigation"

          onClick={() => setMobileOpen(true)}

          className="mr-3 rounded-md p-2 text-slate-200 transition hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 lg:hidden"

        >

          <Menu size={21} />

        </button>

        <ShieldCheck className="mr-3 text-cyan-300" size={22} />

        <div className="min-w-0">

          <p className="truncate font-semibold">SmartBiz Platform Control Center</p>

          <p className="truncate text-xs text-slate-400">Platform operations and security</p>

        </div>

        <div className="ml-auto flex items-center gap-4">

          <ThemeControl darkSurface />

          <Link

            href="/logout"

            className="flex min-h-11 items-center gap-2 text-sm text-slate-200 transition hover:text-white"

          >

            <LogOut size={17} />

            <span className="hidden sm:inline">Sign out</span>

          </Link>

        </div>

      </header>



      <aside className="sb-sidebar fixed inset-y-0 left-0 z-40 hidden w-64 overflow-y-auto border-r lg:block">

        <div className="flex h-16 items-center border-b border-slate-800 px-4 text-white">

          <ShieldCheck className="mr-3 text-cyan-300" size={22} />

          <span className="text-sm font-semibold">Platform Control</span>

        </div>

        {navigationContent}

      </aside>



      {mobileOpen && (

        <div className="fixed inset-0 z-50 lg:hidden">

          <button

            type="button"

            aria-label="Close platform navigation overlay"

            className="absolute inset-0 bg-black/50"

            onClick={() => setMobileOpen(false)}

          />

          <aside ref={drawerRef} role="dialog" aria-modal="true" aria-label="Platform navigation" className="sb-sidebar relative h-full w-[min(20rem,85vw)] overflow-y-auto shadow-2xl">

            <div className="flex h-16 items-center justify-between border-b border-slate-800 px-4">

              <span className="text-sm font-semibold text-white">Platform navigation</span>

              <button

                type="button"

                aria-label="Close platform navigation"

                onClick={() => setMobileOpen(false)}

                className="rounded-md p-2 text-slate-300 transition hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"

              >

                <X size={20} />

              </button>

            </div>

            {navigationContent}

          </aside>

        </div>

      )}



      <div className="flex min-h-[calc(100vh-4rem)] flex-col lg:pl-64">

        <main id="main-content" tabIndex={-1} className="workspace-content mx-auto w-full max-w-[1600px] flex-1 p-4 sm:p-6 lg:p-8">{children}</main>

        <AppFooter embedded />

      </div>

    </div>

  );

}

