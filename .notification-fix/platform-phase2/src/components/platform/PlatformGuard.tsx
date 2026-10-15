"use client";
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
