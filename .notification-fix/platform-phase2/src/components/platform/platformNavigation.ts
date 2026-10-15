import {
  Activity,
  Building2,
  CreditCard,
  HeartPulse,
  History,
  KeyRound,
  LayoutDashboard,
  LifeBuoy,
  LockKeyhole,
  ScrollText,
  Settings,
  ShieldCheck,
  Users,
} from "lucide-react";


export interface PlatformNavigationItem {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  section: "Overview" | "Customers" | "Security" | "Operations" | "Configuration";
}

export const platformNavigation: PlatformNavigationItem[] = [
  { label: "Platform access", href: "/platform/security/access", icon: ShieldCheck, section: "Configuration" },
  { label: "Incidents", href: "/platform/security/incidents", icon: ShieldCheck, section: "Security" },
  { label: "Advanced administration", href: "/platform/administration", icon: Settings, section: "Configuration" },
  {
    label: "Overview",
    href: "/platform/dashboard",
    icon: LayoutDashboard,
    section: "Overview",
  },

  {
    label: "Companies",
    href: "/platform/companies",
    icon: Building2,
    section: "Customers",
  },

  {
    label: "Users",
    href: "/platform/users",
    icon: Users,
    section: "Customers",
  },

  {
    label: "Subscriptions",
    href: "/platform/subscriptions",
    icon: CreditCard,
    section: "Customers",
  },

  {
    label: "Security",
    href: "/platform/security",
    icon: ShieldCheck,
    section: "Security",
  },

  {
    label: "Support",
    href: "/platform/support",
    icon: LifeBuoy,
    section: "Customers",
  },

  {
    label: "Audit",
    href: "/platform/audit",
    icon: ScrollText,
    section: "Security",
  },

  {
    label: "Sessions",
    href: "/platform/security/sessions",
    icon: KeyRound,
    section: "Security",
  },

  {
    label: "Failed Logins",
    href: "/platform/failed-logins",
    icon: LockKeyhole,
    section: "Security",
  },

  {
    label: "Login History",
    href: "/platform/security/login-history",
    icon: History,
    section: "Security",
  },

  {
    label: "System Health",
    href: "/platform/health",
    icon: HeartPulse,
    section: "Operations",
  },

  {
    label: "Activity",
    href: "/platform/activity",
    icon: Activity,
    section: "Operations",
  },

  {
    label: "Settings",
    href: "/platform/settings",
    icon: Settings,
    section: "Configuration",
  },
];