import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { BusinessRequest } from "@/types/request";
import { formatDate, formatEnumLabel } from "@/utils/format";
export function RequestCard({request}:{request:BusinessRequest}) {
 return <Link href={`/requests/${request.id}`} className="sb-explore-card block"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs text-[var(--muted)]">{request.request_number} · {formatEnumLabel(request.request_type)}</p><h2 className="mt-1 break-words font-semibold text-[var(--ink)]">{request.title}</h2></div><span className="sb-soft-badge">{request.status==="UNDER_REVIEW"?"Being reviewed":formatEnumLabel(request.status)}</span></div><div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm"><p className="text-[var(--muted)]">{formatDate(request.created_at)} · {formatEnumLabel(request.priority)} priority</p><span className="sb-text-link">{request.status==="DRAFT"||request.status==="RETURNED"?"Continue request":"View progress"}<ArrowUpRight size={16}/></span></div></Link>;
}