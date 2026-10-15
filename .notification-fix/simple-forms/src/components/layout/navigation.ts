import {
  Activity,
  Bell,
  Building2,
  CalendarClock,
  CheckSquare,
  ClipboardList,
  FileBox,
  FileText,
  FolderKanban,
  LayoutDashboard,
  ListTodo,
  Network,
  Route,
  ReceiptText,
  Settings,
  Sparkles,
  Users,
  CreditCard,
  Blocks,
  BriefcaseBusiness,
  MessageCircle,
  UsersRound,
  UserPlus,
  LifeBuoy,
} from "lucide-react";

import type { LucideIcon } from "lucide-react";
import { CAPABILITIES, type Capability } from "@/utils/capabilities";

export interface NavigationItem {
  label: string;
  href: string;
  icon: LucideIcon;
  capabilities?: Capability[];
  requireAllCapabilities?: boolean;
}

export const navigationItems: NavigationItem[] = [
  {label:"Company setup",href:"/settings/onboarding",icon:Building2,capabilities:[CAPABILITIES.MANAGE_COMPANY_SETUP]},
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  {
    label: "Company map",
    href: "/company",
    icon: Building2,
    capabilities: [CAPABILITIES.MANAGE_COMPANY_SETUP, CAPABILITIES.MANAGE_ORGANIZATION, CAPABILITIES.VIEW_ALL_EMPLOYEES],
  },
  {
    label: "Company Profile",
    href: "/settings/company-profile",
    icon: FileText,
    capabilities: [CAPABILITIES.MANAGE_COMPANY_SETUP],
  },
  { label: "Branches", href: "/branches", icon: Network, capabilities: [CAPABILITIES.MANAGE_ORGANIZATION, CAPABILITIES.VIEW_ALL_EMPLOYEES] },
  { label: "Departments", href: "/departments", icon: Blocks, capabilities: [CAPABILITIES.MANAGE_ORGANIZATION, CAPABILITIES.VIEW_ALL_EMPLOYEES] },
  { label: "Teams", href: "/teams", icon: UsersRound, capabilities: [CAPABILITIES.MANAGE_ORGANIZATION, CAPABILITIES.VIEW_ALL_EMPLOYEES] },
  {
    label: "Directory",
    href: "/employees",
    icon: BriefcaseBusiness,
    capabilities: [
      CAPABILITIES.VIEW_ALL_EMPLOYEES,
      CAPABILITIES.MANAGE_EMPLOYEES,
    ],
  },
  {
    label: "Accounts",
    href: "/users",
    icon: Users,
    capabilities: [
      CAPABILITIES.VIEW_ALL_EMPLOYEES,
      CAPABILITIES.MANAGE_EMPLOYEES,
    ],
  },
  {
    label: "Invite employees",
    href: "/employees/invite",
    icon: UserPlus,
    capabilities: [CAPABILITIES.MANAGE_EMPLOYEES],
  },
  { label: "Positions", href: "/employees/positions", icon: BriefcaseBusiness, capabilities: [CAPABILITIES.MANAGE_ORGANIZATION] },
  { label: "My account", href: "/settings/profile", icon: Users },
  { label: "Projects", href: "/projects", icon: FolderKanban },
  { label: "Tasks", href: "/tasks", icon: ListTodo },
  { label: "Reports", href: "/reports", icon: ReceiptText },
  { label: "Forms", href: "/forms", icon: ClipboardList },
  { label: "Materials & deliveries", href: "/materials", icon: ClipboardList, capabilities: [CAPABILITIES.USE_FORMS, CAPABILITIES.SUBMIT_FORMS] },
  {
    label: "Reports due",
    href: "/reporting/obligations",
    icon: CalendarClock,
  },
  { label: "Approvals", href: "/approvals", icon: CheckSquare },
  { label: "Requests", href: "/requests", icon: FileText },
  {
    label: "Planning",
    href: "/planning",
    icon: Route,
    capabilities: [
      CAPABILITIES.VIEW_COMPANY_PLANS,
      CAPABILITIES.MANAGE_COMPANY_PLANS,
    ],
  },
  {
    label: "Field Operations",
    href: "/field",
    icon: Route,
    capabilities: [
      CAPABILITIES.USE_FIELD_OPERATIONS,
      CAPABILITIES.MANAGE_FIELD_OPERATIONS,
    ],
  },
  { label: "Documents", href: "/documents", icon: FileBox },
  {
    label: "Official Records",
    href: "/records",
    icon: ReceiptText,
    capabilities: [CAPABILITIES.VIEW_OFFICIAL_RECORDS],
  },
  {
    label: "Data Tools",
    href: "/data-tools/import",
    icon: FileText,
    capabilities: [
      CAPABILITIES.IMPORT_EMPLOYEES,
      CAPABILITIES.IMPORT_OPERATIONAL_DATA,
      CAPABILITIES.EXPORT_OPERATIONAL_DATA,
    ],
  },
  { label: "Activity", href: "/activity", icon: Activity },
  {
    label: "Analytics",
    href: "/analytics",
    icon: Sparkles,
    capabilities: [
      CAPABILITIES.VIEW_COMPANY_ANALYTICS,
      CAPABILITIES.VIEW_EXECUTIVE_DASHBOARD,
    ],
  },
  { label: "Notifications", href: "/notifications", icon: Bell },
  { label: "Help & Support", href: "/support", icon: LifeBuoy },
  { label: "Chat", href: "/chat", icon: MessageCircle },
  {
    label: "Subscription",
    href: "/subscriptions",
    icon: CreditCard,
    capabilities: [CAPABILITIES.MANAGE_COMPANY_SETUP],
  },
  { label: "Company settings", href: "/settings", icon: Settings, capabilities: [CAPABILITIES.MANAGE_COMPANY_SETUP, CAPABILITIES.MANAGE_ORGANIZATION] },
];
