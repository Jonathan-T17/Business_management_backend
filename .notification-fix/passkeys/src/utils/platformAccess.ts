export function platformHome(capabilities: string[] = []) {
  if (capabilities.includes("PLATFORM_ADMIN")) return "/platform/dashboard";
  if (capabilities.includes("VIEW_PLATFORM_SECURITY")) return "/platform/security";
  if (capabilities.includes("PLATFORM_SUPPORT")) return "/platform/support";
  if (capabilities.includes("MANAGE_PLATFORM_SUBSCRIPTIONS")) return "/platform/subscriptions";
  if (capabilities.includes("VIEW_PLATFORM_AUDIT")) return "/platform/audit";
  return "/login";
}

export function platformPathAllowed(path: string, capabilities: string[] = []) {
  if (capabilities.includes("PLATFORM_ADMIN")) return true;
  if (path === "/platform/passkeys") return capabilities.some(capability => capability.includes("PLATFORM"));
  const rules: [string, string][] = [
    ["/platform/security/access", "PLATFORM_ADMIN"],
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
