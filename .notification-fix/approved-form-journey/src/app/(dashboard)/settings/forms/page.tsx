"use client";

import { FormBuilderGuard } from "@/components/forms/FormBuilderGuard";
import { RequireCapability } from "@/components/auth/RequireCapability";
import { CAPABILITIES } from "@/utils/capabilities";
import Link from "next/link";
import { useState } from "react";
import { formatEnumLabel } from "@/utils/format";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { formsApi } from "@/api/formsApi";
import { FormTemplateLibrary } from "@/components/forms/FormTemplateLibrary";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { queryKeys } from "@/lib/queryKeys";

export default function SetupFormsPage() { return <FormBuilderGuard><FormsList /></FormBuilderGuard>; }
function FormsList() {
  const [showRetired,setShowRetired]=useState(false);
  const { data: templates = [], isLoading, isError } = useQuery({ queryKey: [...queryKeys.forms.templates,"builder"], queryFn: formsApi.builderTemplates });
  return <div className="space-y-7"><PageHeader title="Saved company forms" description="Your drafts and published forms are saved here. Open a form to preview, edit or publish it." action={<RequireCapability capabilities={[CAPABILITIES.MANAGE_FORM_TEMPLATES]}><Link href="/settings/forms/new"><Button iconLeft={<Plus size={16} />}>Create a custom form</Button></Link></RequireCapability>} />
    <section className="rounded-xl border p-5"><h2 className="font-semibold">Choose → Review → Publish</h2><p className="mt-2 text-sm">Choose complete forms from the library below. Open your saved company copies to check their fields, access and reviewers, then publish when ready. Employees use the published forms; their completed answers are saved separately.</p><Link className="mt-3 inline-block underline" href="/settings/onboarding?step=forms">Back to forms setup</Link></section>
    <RequireCapability capabilities={[CAPABILITIES.MANAGE_FORM_TEMPLATES]}><details className="rounded-xl border p-5"><summary className="cursor-pointer font-semibold">Add ready-made forms to your company</summary><div className="mt-5"><FormTemplateLibrary/></div></details></RequireCapability>
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={showRetired} onChange={event=>setShowRetired(event.target.checked)}/>Show retired form versions</label>
    {isError ? <p role="alert">Unable to load forms. Please try again.</p> : isLoading ? <div className="h-32 animate-pulse bg-[var(--surface-soft)]" /> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{!templates.length&&<p className="rounded-xl border border-dashed p-6">No company forms saved yet. Open the ready-made library above, preview the forms you need and save your selection here.</p>}{templates.filter(template=>showRetired || template.lifecycle_status !== "ARCHIVED").map((template) => <Link key={template.id} href={`/settings/forms/${template.id}`} className="sb-form-choice transition-colors hover:border-[var(--accent-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"><div><p className="text-xs font-semibold uppercase text-[var(--muted)]">{formatEnumLabel(template.category)} · Version {template.version}</p><h2 className="mt-1 font-semibold text-[var(--ink)]">{template.name}</h2><p className="mt-2 text-sm text-[var(--muted)]">{template.description || "A private form prepared for your company."}</p><p className="mt-3 text-xs text-[var(--muted)]">{template.fields.length} fields · {template.allow_drafts ? "Drafts allowed" : "Submit only"}</p></div><span className="text-xs font-semibold text-[var(--muted)]">{template.lifecycle_status === "PUBLISHED" ? "Published" : template.lifecycle_status === "ARCHIVED" ? "Retired" : "Ready for review"}</span>{template.library_update?.available&&<p className="mt-3 text-sm text-[var(--accent-text)]">Updated template available · Review changes →</p>}<p className="mt-auto pt-4 text-sm font-semibold">Open and review form →</p></Link>)}</div>}
  </div>;
}
