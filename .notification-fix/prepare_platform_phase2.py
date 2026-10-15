from pathlib import Path

source = Path(r'C:\Users\1213\Desktop\Jonathan\business_management_frontend')
stage = Path('.notification-fix/platform-phase2')

def write(name, content):
    path = stage / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

def edit(name, fn):
    write(name, fn((source/name).read_text(encoding='utf-8')))

write('src/utils/platformAccess.ts', '''export function platformHome(capabilities: string[] = []) {
  if (capabilities.includes("PLATFORM_ADMIN")) return "/platform/dashboard";
  if (capabilities.includes("VIEW_PLATFORM_SECURITY")) return "/platform/security";
  if (capabilities.includes("PLATFORM_SUPPORT")) return "/platform/support";
  if (capabilities.includes("MANAGE_PLATFORM_SUBSCRIPTIONS")) return "/platform/subscriptions";
  if (capabilities.includes("VIEW_PLATFORM_AUDIT")) return "/platform/audit";
  return "/login";
}

export function platformPathAllowed(path: string, capabilities: string[] = []) {
  if (capabilities.includes("PLATFORM_ADMIN")) return true;
  const rules: [string, string][] = [
    ["/platform/security/incidents", "VIEW_PLATFORM_AUDIT"],
    ["/platform/security", "VIEW_PLATFORM_SECURITY"],
    ["/platform/failed-logins", "VIEW_PLATFORM_SECURITY"],
    ["/platform/audit", "VIEW_PLATFORM_AUDIT"],
    ["/platform/health", "VIEW_PLATFORM_HEALTH"],
    ["/platform/support", "PLATFORM_SUPPORT"],
    ["/platform/subscriptions", "MANAGE_PLATFORM_SUBSCRIPTIONS"],
  ];
  const rule = rules.find(([prefix]) => path === prefix || path.startsWith(prefix + "/"));
  return Boolean(rule && capabilities.includes(rule[1]));
}
''')

edit('src/utils/homeRoute.ts', lambda s: 'import { platformHome } from "./platformAccess";\n' + s.replace('isPlatformIdentity(user) ? "/platform/dashboard"', 'isPlatformIdentity(user) ? platformHome(user?.capabilities)'))
edit('src/components/platform/PlatformShell.tsx', lambda s: s.replace('import { platformNavigation }', 'import { useAuthStore } from "@/store/authStore";\nimport { platformPathAllowed } from "@/utils/platformAccess";\nimport { platformNavigation }').replace('  const pathname = usePathname();', '  const pathname = usePathname();\n  const user = useAuthStore(state => state.user);').replace('item => item.label.toLowerCase()', 'item => platformPathAllowed(item.href, user?.capabilities) && item.label.toLowerCase()'))
write('src/components/platform/PlatformGuard.tsx', '''"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { isPlatformIdentity } from "@/utils/homeRoute";
import { platformHome, platformPathAllowed } from "@/utils/platformAccess";

export function PlatformGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isInitializing } = useAuthStore();
  const platform = isPlatformIdentity(user);
  const home = platformHome(user?.capabilities);
  const allowed = platformPathAllowed(pathname, user?.capabilities);
  useEffect(() => {
    if (isInitializing) return;
    if (!isAuthenticated) router.replace("/login");
    else if (user?.must_change_password) router.replace("/change-required-password");
    else if (!platform) router.replace("/dashboard");
    else if (!allowed && home !== "/login") router.replace(home);
  }, [isInitializing, isAuthenticated, user?.must_change_password, platform, allowed, home, router]);
  if (isInitializing || !isAuthenticated || user?.must_change_password || !platform) return null;
  if (home === "/login") return <p role="alert" className="p-6">Platform access is not assigned. Contact the platform owner.</p>;
  return allowed ? children : null;
}
''')
edit('src/components/platform/platformNavigation.ts', lambda s: s.replace('  { label: "Advanced administration"', '  { label: "Incidents", href: "/platform/security/incidents", icon: ShieldCheck, section: "Security" },\n  { label: "Advanced administration"'))
edit('src/api/platformApi.ts', lambda s: s + '''
export async function getPlatformSecuritySummary() {
  const { data } = await platformClient.get<{security: PlatformDashboard["security"]; open_incidents: number; authentication: string}>("security/summary/");
  return data;
}
''')
edit('src/app/(platform)/platform/security/page.tsx', lambda s: s.replace('getPlatformDashboard', 'getPlatformSecuritySummary').replace('"dashboard",', '"security-summary",').replace('      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">', '''      <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5">
        <h2 className="font-semibold">Administrator sign-in protection</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">{data.authentication}</p>
        <Link href="/platform/security/incidents" className="mt-4 inline-block font-medium text-teal-700 dark:text-teal-300">Review incidents · {data.open_incidents} open</Link>
      </section>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">'''))
edit('src/types/platform.ts', lambda s: s.replace('export interface PlatformHealth {', '''export interface PlatformHealth {
  services?: Record<string, {status: string; detail?: string; last_run?: string}>;'''))
write('src/app/(platform)/platform/health/page.tsx', '''"use client";
import { useQuery } from "@tanstack/react-query";
import { getPlatformHealth } from "@/api/platformApi";
const labels: Record<string, string> = {database: "Database", cache: "Cache", email_delivery: "Email delivery", reporting: "Reporting automation", storage: "Private storage", backups: "Backups & restore"};
const statusLabel: Record<string, string> = {healthy: "Healthy", unhealthy: "Needs attention", degraded: "Needs attention", partially_monitored: "Partially monitored", not_monitored: "Not monitored"};
export default function PlatformHealthPage() {
  const {data, isLoading, isError} = useQuery({queryKey: ["platform", "health"], queryFn: getPlatformHealth, refetchInterval: 30000});
  if (isLoading) return <p role="status">Checking services…</p>;
  if (isError || !data) return <p role="alert">Unable to retrieve service health. Try again shortly.</p>;
  return <div className="space-y-6">
    <header><h1 className="text-2xl font-semibold">System health</h1><p className="mt-2 text-[var(--muted)]">See what is working, what needs attention, and what still needs monitoring.</p></header>
    <section className="rounded-2xl border border-amber-300/40 bg-[var(--surface)] p-5"><h2 className="font-semibold">{statusLabel[data.status] || data.status}</h2><p className="mt-2 text-sm text-[var(--muted)]">A healthy check covers that service only. Unmonitored services have no verified health evidence.</p><p className="mt-2 text-xs text-[var(--muted)]">Last checked {new Date(data.timestamp).toLocaleString()}</p></section>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Object.entries(data.services || {database:data.database, cache:data.cache}).map(([key, service]) => <section key={key} className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5"><h2 className="font-semibold">{labels[key] || key}</h2><p className={`mt-3 font-medium ${service.status === "healthy" ? "text-teal-700 dark:text-teal-300" : service.status === "unhealthy" ? "text-red-700 dark:text-red-300" : "text-amber-700 dark:text-amber-300"}`}>{statusLabel[service.status] || service.status}</p>{"detail" in service && <p className="mt-2 text-sm text-[var(--muted)]">{service.detail}</p>}{"last_run" in service && service.last_run && <p className="mt-2 text-xs text-[var(--muted)]">Last run {new Date(service.last_run).toLocaleString()}</p>}</section>)}</div>
  </div>;
}
''')
