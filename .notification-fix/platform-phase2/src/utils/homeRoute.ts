import { platformHome } from "./platformAccess";
import type { CurrentUser } from "@/types/user";

export function isPlatformIdentity(user?: CurrentUser | null) {
  return Boolean(user && (user.context === "PLATFORM" || (!user.context && user.role === "SUPERUSER")));
}

export function homeRouteForUser(user?: CurrentUser | null) {
  return isPlatformIdentity(user) ? platformHome(user?.capabilities) : "/dashboard";
}
