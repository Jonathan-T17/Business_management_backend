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
    <header className="flex items-center gap-4 border-b border-[var(--line)] bg-[var(--accent-soft)] px-5 py-4 text-[var(--ink)] sm:px-8">
      <Icon className="h-8 w-8 shrink-0 text-[var(--accent-text)] sm:h-10 sm:w-10" aria-hidden="true" />
      <Heading className="text-2xl font-bold leading-tight sm:text-3xl">{title}</Heading>
    </header>
    <div className="px-5 py-3 sm:px-8">
      {description && <p className="mb-2 text-sm leading-relaxed text-[var(--muted)]">{description}</p>}
      <p className="text-xs text-[var(--muted)]">Fields marked * are required.{preview && " Preview only: answers are not saved."}</p>
      {children}
      {footer && <div className="border-t border-[var(--line)] py-4">{footer}</div>}
    </div>
  </section>;
}
