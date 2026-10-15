"use client";

import Link from "next/link";

import {
  useQuery,
} from "@tanstack/react-query";

import {
  Activity,
  Building2,
  CreditCard,
  FolderKanban,
  HeartPulse,
  ShieldAlert,
  Users,
} from "lucide-react";

import {
  getPlatformDashboard,
} from "@/api/platformApi";


export default function PlatformDashboardPage() {
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: [
      "platform",
      "dashboard",
    ],

    queryFn:
      getPlatformDashboard,

    refetchInterval:
      60_000,
  });


  if (isLoading) {
    return (
      <PlatformDashboardLoading />
    );
  }


  if (
    isError ||
    !data
  ) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-700">
        <p role="alert">Unable to load platform dashboard.</p><button type="button" className="mt-3 underline" onClick={()=>void refetch()}>Try again</button>
      </div>
    );
  }


  return (
    <div className="space-y-7">

      <div className="sb-overview flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

        <div>
          <h1 className="text-2xl font-bold text-gray-950">
            Platform Control Center
          </h1>

          <p className="mt-1 text-sm text-gray-500">
            Global operational, security and tenant oversight.
          </p>
        </div>


        <HealthBadge
          status={
            data.system_health
              .status
          }
        />
      </div>


      <section aria-labelledby="platform-actions" className="rounded-xl border border-gray-200 bg-white p-5">
        <h2 id="platform-actions" className="text-lg font-semibold">Platform operations</h2>
        <p className="mt-1 text-sm text-gray-500">Choose an area to review. Company business content stays within its authorized scope.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {[
            {href:"/platform/companies",title:"Manage companies",detail:"Review accounts, status and company setup."},
            {href:"/platform/support",title:"Help a customer",detail:"Open the platform support workspace."},
            {href:"/platform/security",title:"Review security",detail:`${data.security.critical_events_24h} critical events in the past 24 hours.`},
            {href:"/platform/subscriptions",title:"Review subscriptions",detail:`${data.subscriptions.expiring_soon} subscriptions expiring soon.`},
          ].map(action=><Link key={action.href} href={action.href} className="rounded-xl border border-gray-200 p-4 transition hover:border-teal-500 focus-visible:outline-2"><h3 className="font-semibold">{action.title}</h3><p className="mt-1 text-sm text-gray-500">{action.detail}</p></Link>)}
        </div>
        <Link href="/platform/health" className="mt-4 inline-block text-sm font-semibold underline">Inspect system health</Link>
      </section>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          icon={
            <Building2
              size={20}
            />
          }
          label="Companies"
          value={
            data.companies.total
          }
          description={`${data.companies.active} active`}
        />

        <MetricCard
          icon={
            <Users size={20} />
          }
          label="Users"
          value={
            data.users.total
          }
          description={`${data.users.active} active`}
        />

        <MetricCard
          icon={
            <FolderKanban
              size={20}
            />
          }
          label="Projects"
          value={
            data.projects.total
          }
          description={`${data.projects.active} active`}
        />

        <MetricCard
          icon={
            <ShieldAlert
              size={20}
            />
          }
          label="Security alerts"
          value={
            data.security
              .critical_events_24h
          }
          description="Critical · 24h"
        />
      </div>


      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          icon={
            <Activity
              size={20}
            />
          }
          label="Active sessions"
          value={
            data.security
              .active_sessions
          }
          description="Current"
        />

        <MetricCard
          icon={
            <ShieldAlert
              size={20}
            />
          }
          label="Failed logins"
          value={
            data.security
              .failed_logins_24h
          }
          description="Past 24 hours"
        />

        <MetricCard
          icon={
            <CreditCard
              size={20}
            />
          }
          label="Subscriptions"
          value={
            data.subscriptions
              .active
          }
          description={`${data.subscriptions.expiring_soon} expiring soon`}
        />

        <MetricCard
          icon={
            <HeartPulse
              size={20}
            />
          }
          label="Reports · past 24h"
          value={
            data.reports.last_24h
          }
          description={`${data.reports.total} total`}
        />
      </div>


      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">

        <section className="rounded-xl border border-gray-200 bg-white shadow-sm">

          <div className="flex items-center justify-between border-b border-gray-200 p-5">

            <div>
              <h2 className="font-semibold text-gray-950">
                Recent audit events
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                Latest platform and tenant audit activity.
              </p>
            </div>

            <Link
              href="/platform/audit"
              className="text-sm font-semibold text-blue-600"
            >
              View all
            </Link>
          </div>


          {data.recent_audit_events.length === 0 ? (
            <p className="p-6 text-sm text-gray-500">
              No audit events available.
            </p>
          ) : (
            <div className="divide-y divide-gray-100">

              {data.recent_audit_events.slice(0, 3).map(
                (event) => (
                  <div
                    key={event.id}
                    className="p-4"
                  >

                    <div className="flex items-start justify-between gap-3">

                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {event.action}
                        </p>

                        <p className="mt-1 text-xs text-gray-500">
                          {event.company_name ??
                            "Platform"}
                          {" · "}
                          {event.user_email ??
                            "System"}
                        </p>
                      </div>

                      <SeverityBadge
                        severity={
                          event.severity
                        }
                      />
                    </div>


                    {event.description && (
                      <p className="mt-2 line-clamp-2 text-sm text-gray-600">
                        {event.description}
                      </p>
                    )}


                    <p className="mt-2 text-xs text-gray-400">
                      {new Date(
                        event.created_at
                      ).toLocaleString()}
                    </p>
                  </div>
                )
              )}
            </div>
          )}
        </section>


        <section className="rounded-xl border border-gray-200 bg-white shadow-sm">

          <div className="flex items-center justify-between border-b border-gray-200 p-5">

            <h2 className="font-semibold text-gray-950">
              Recent companies
            </h2>

            <Link
              href="/platform/companies"
              className="text-sm font-semibold text-blue-600"
            >
              View all
            </Link>
          </div>


          <div className="divide-y divide-gray-100">

            {data.recent_companies.map(
              (company) => (
                <Link
                  key={company.id}
                  href={`/platform/companies/${company.id}`}
                  className="block p-4 hover:bg-gray-50"
                >

                  <div className="flex items-center justify-between gap-4">

                    <div>
                      <p className="font-medium text-gray-900">
                        {company.name}
                      </p>

                      <p className="mt-1 text-xs text-gray-500">
                        {company.users_count} users
                        {" · "}
                        {company.projects_count == null ? "Project count unavailable" : `${company.projects_count} projects`}
                      </p>
                    </div>


                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        company.is_active
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {company.is_active
                        ? "Active"
                        : "Inactive"}
                    </span>
                  </div>
                </Link>
              )
            )}
          </div>
        </section>
      </div>


      <SecurityOverview
        data={data}
      />
    </div>
  );
}

function SecurityOverview({
  data,
}: {
  data: Awaited<
    ReturnType<
      typeof getPlatformDashboard
    >
  >;
}) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">

      <div className="flex items-center justify-between">

        <div>
          <h2 className="font-semibold text-gray-950">
            Security overview
          </h2>

          <p className="mt-1 text-sm text-gray-500">
            Authentication and platform-security signals.
          </p>
        </div>

        <Link
          href="/platform/security"
          className="text-sm font-semibold text-blue-600"
        >
          Open security center
        </Link>
      </div>


      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <SecurityMetric
          label="Active sessions"
          value={
            data.security
              .active_sessions
          }
        />

        <SecurityMetric
          label="Failed logins"
          value={
            data.security
              .failed_logins_24h
          }
        />

        <SecurityMetric
          label="Locked records"
          value={
            data.security
              .locked_records
          }
        />

        <SecurityMetric
          label="Critical events"
          value={
            data.security
              .critical_events_24h
          }
        />
      </div>
    </section>
  );
}


function MetricCard({
  icon,
  label,
  value,
  description,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  description: string;
}) {
  return (
    <div className="sb-stat sb-card rounded-xl border border-gray-200 bg-white p-5 shadow-sm">

      <div className="flex items-center gap-2 text-gray-500">
        <span className="sb-metric-icon">{icon}</span>
        <span className="text-sm">
          {label}
        </span>
      </div>

      <p className="mt-3 text-3xl font-bold text-gray-950">
        {value}
      </p>

      <p className="mt-1 text-xs text-gray-400">
        {description}
      </p>
    </div>
  );
}


function SecurityMetric({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-lg bg-gray-50 p-4">

      <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
        {label}
      </p>

      <p className="mt-2 text-2xl font-bold text-gray-950">
        {value}
      </p>
    </div>
  );
}


function SeverityBadge({
  severity,
}: {
  severity: string;
}) {
  const classes =
    severity === "CRITICAL"
      ? "bg-red-100 text-red-700"
      : severity === "WARNING"
      ? "bg-amber-100 text-amber-700"
      : "bg-blue-100 text-blue-700";

  return (
    <span
      className={`rounded-full px-2 py-1 text-[10px] font-semibold ${classes}`}
    >
      {severity}
    </span>
  );
}


function HealthBadge({
  status,
}: {
  status: string;
}) {
  const healthy = status === "healthy";
  const degraded = status === "degraded";
  const label = healthy ? "System healthy" : degraded ? "System degraded" : status === "partially_monitored" ? "Partially monitored" : "Health not verified";

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold ${
        healthy
          ? "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200"
          : degraded ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200" : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200"
      }`}
    >
      <span
        className={`h-2 w-2 rounded-full ${
          healthy
            ? "bg-green-600"
            : "bg-amber-600"
        }`}
      />

      {label}
    </div>
  );
}


function PlatformDashboardLoading() {
  return (
    <div className="space-y-6">

      <div className="h-14 w-80 animate-pulse rounded-lg bg-gray-200" />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map(
          (item) => (
            <div
              key={item}
              className="h-28 animate-pulse rounded-xl bg-gray-200"
            />
          )
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="h-96 animate-pulse rounded-xl bg-gray-200" />
        <div className="h-96 animate-pulse rounded-xl bg-gray-200" />
      </div>
    </div>
  );
}