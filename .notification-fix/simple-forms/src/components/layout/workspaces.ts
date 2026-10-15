import { navigationItems, type NavigationItem } from "./navigation";
import { canSeeNavigationItem } from "@/utils/navigation";
import type { CurrentUser } from "@/types/user";

export const workspaceGroups = ["Overview", "Forms & reporting", "Requests & approvals", "Company & people", "Documents & records", "Communication", "Company settings", "My account", "Optional planning"];

export function workspaceFor(href: string): string {
  if (["/settings/profile", "/settings/security", "/settings/notifications"].includes(href)) return "My account";
  if (href.startsWith("/settings/forms") || href.startsWith("/settings/reporting") || href.startsWith("/reporting/") || ["/forms", "/reports", "/materials"].some(path => href === path || href.startsWith(path + "/"))) return "Forms & reporting";
  const root = href.split("/")[1];
  if (["dashboard", "analytics", "activity"].includes(root)) return "Overview";
  if (["requests", "approvals"].includes(root)) return "Requests & approvals";
  if (["company", "branches", "departments", "teams", "employees", "users"].includes(root)) return "Company & people";
  if (["documents", "records", "data-tools"].includes(root)) return "Documents & records";
  if (["notifications", "chat", "support"].includes(root)) return "Communication";
  if (["projects", "tasks", "planning"].includes(root)) return "Optional planning";
  return "Company settings";
}

export function visibleNavigation(user: CurrentUser): NavigationItem[] {
  return navigationItems.filter(item => canSeeNavigationItem(user, item));
}

export function activeNavigation(pathname: string, items: NavigationItem[]): NavigationItem | undefined {
  const effectivePath = pathname.startsWith("/settings/forms") ? "/forms" : pathname;
  return items.filter(item => effectivePath === item.href || effectivePath.startsWith(item.href + "/"))
    .sort((a, b) => b.href.length - a.href.length)[0];
}
