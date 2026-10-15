"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { navigationItems } from "./navigation";
import { useAuthStore } from "@/store/authStore";
import { canSeeNavigationItem } from "@/utils/navigation";

const preferredRoutes = ["/dashboard", "/forms", "/reporting/obligations", "/approvals"];

export function MobileBottomNav({ onMore }: { onMore: () => void }) {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);

  const items = user
    ? preferredRoutes
        .map((href) => navigationItems.find((item) => item.href === href))
        .filter((item): item is NonNullable<typeof item> => Boolean(item))
        .filter((item) => canSeeNavigationItem(user, item))
        .slice(0, 4)
    : [];

  return (
    <nav
      className="sb-mobile-nav fixed inset-x-0 bottom-0 z-40 border-t border-neutral-200 bg-white pb-[env(safe-area-inset-bottom)] md:hidden"
      aria-label="Mobile navigation"
    >
      <div className="grid" style={{ gridTemplateColumns: `repeat(${items.length + 1}, minmax(0, 1fr))` }}>
        {items.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex min-h-16 flex-col items-center justify-center gap-1 text-xs ${
                active ? "font-semibold text-neutral-950" : "text-neutral-500"
              }`}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </Link>
          );
        })}

        <button
          type="button"
          onClick={onMore}
          className="flex min-h-16 flex-col items-center justify-center gap-1 text-xs text-neutral-500"
          aria-label="Open workspace menu"
        >
          <Menu size={20} />
          <span>Menu</span>
        </button>
      </div>
    </nav>
  );
}
