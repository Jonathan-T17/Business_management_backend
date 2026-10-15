"use client";

import Link from "next/link";

import {
  useQuery,
} from "@tanstack/react-query";

import {
  History,
  KeyRound,
  MonitorSmartphone,
  ShieldAlert,
} from "lucide-react";

import {
  getPlatformSecuritySummary,
} from "@/api/platformApi";


export default function PlatformSecurityPage() {
  const {
    data,
    isLoading,
    isError,
  } = useQuery({
    queryKey: [
      "platform",
      "security-summary",
    ],

    queryFn:
      getPlatformSecuritySummary,
  });


  if (isLoading) {
    return (
      <div className="h-64 animate-pulse rounded-xl bg-gray-200" />
    );
  }

  if (isError || !data) {
    return <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-700">Unable to load security metrics.</div>;
  }


  return (
    <div className="space-y-7">

      <div>
        <h1 className="text-2xl font-bold text-gray-950">
          Security Center
        </h1>

        <p className="mt-1 text-sm text-gray-500">
          Investigate authentication activity and respond to account-security incidents.
        </p>
      </div>


      <section className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5">
        <h2 className="font-semibold">Administrator sign-in protection</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">{data.authentication}</p>
        <Link href="/platform/security/incidents" className="mt-4 inline-block font-medium text-teal-700 dark:text-teal-300">Review incidents · {data.open_incidents} open</Link>
      </section>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <SecurityCard
          icon={
            <MonitorSmartphone
              size={20}
            />
          }
          label="Active sessions"
          value={
            data.security
              .active_sessions
          }
          href="/platform/security/sessions"
        />

        <SecurityCard
          icon={
            <History size={20} />
          }
          label="Failed logins"
          value={
            data.security
              .failed_logins_24h
          }
          href="/platform/failed-logins"
        />

        <SecurityCard
          icon={
            <KeyRound size={20} />
          }
          label="Locked records"
          value={
            data.security
              .locked_records
          }
          href="/platform/failed-logins"
        />

        <SecurityCard
          icon={
            <ShieldAlert
              size={20}
            />
          }
          label="Critical events"
          value={
            data.security
              .critical_events_24h
          }
          href="/platform/audit"
        />
      </div>


      <div className="grid gap-4 md:grid-cols-3">

        <SecurityLink
          title="Active Sessions"
          description="Inspect devices, IP addresses and terminate compromised sessions."
          href="/platform/security/sessions"
        />

        <SecurityLink
          title="Login History"
          description="Review successful and failed authentication events."
          href="/platform/security/login-history"
        />

        <SecurityLink
          title="Failed Logins"
          description="Review lockouts and clear legitimate user login locks."
          href="/platform/failed-logins"
        />
      </div>
    </div>
  );
}


function SecurityCard({
  icon,
  label,
  value,
  href,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md"
    >
      <div className="flex items-center gap-2 text-gray-500">
        {icon}
        <span className="text-sm">
          {label}
        </span>
      </div>

      <p className="mt-3 text-3xl font-bold text-gray-950">
        {value}
      </p>
    </Link>
  );
}


function SecurityLink({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300"
    >
      <h2 className="font-semibold text-gray-950">
        {title}
      </h2>

      <p className="mt-2 text-sm leading-6 text-gray-500">
        {description}
      </p>
    </Link>
  );
}