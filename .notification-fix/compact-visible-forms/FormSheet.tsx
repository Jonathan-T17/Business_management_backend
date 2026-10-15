import type { ReactNode } from "react";
import { ClipboardList, Package, Wallet, Truck, Users, ShieldCheck } from "lucide-react";

export function FormSheet({ title, category, description, preview = false, heading = "h2", children, footer }: {
  title: string;
  category?: string;
  description?: string;
  preview?: boolean;
  heading?: "h1" | "h2";
  children: ReactNode;
  footer?: ReactNode;
}) {
  const Icon = category === "COLLECTION" ? Package : category === "DELIVERY" ? Truck : category === "EXPENSE" ? Wallet : category === "HR" ? Users : category === "INSPECTION" ? ShieldCheck : ClipboardList;
  const Heading = heading;
  return <section className="overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)] shadow-sm">
    <header className="flex items-center gap-3 border-b border-[var(--line)] bg-[var(--accent-soft)] px-5 py-3 text-[var(--ink)] sm:px-8">
      <Icon className="h-7 w-7 shrink-0 text-[var(--accent-text)] sm:h-8 sm:w-8" aria-hidden="true" />
      <Heading className="text-xl font-bold leading-tight sm:text-2xl">{title}</Heading>
    </header>
    <div className="px-5 py-3 sm:px-8">
      {description && <p className="mb-1 text-sm leading-5 text-[var(--muted)]">{description}</p>}
      <p className="text-xs text-[var(--muted)]">* Required{preview && " · Preview: answers are not saved."}</p>
      {children}
      {footer && <div className="border-t border-[var(--line)] py-3">{footer}</div>}
    </div>
  </section>;
}
