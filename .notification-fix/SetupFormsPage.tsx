"use client";

import { FormBuilderGuard } from "@/components/forms/FormBuilderGuard";
import { RequireCapability } from "@/components/auth/RequireCapability";
import { CAPABILITIES } from "@/utils/capabilities";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { formsApi } from "@/api/formsApi";
import { FormTemplateLibrary } from "@/components/forms/FormTemplateLibrary";
import { Button } from "@/components/ui/Button";
import PageHeader from "@/components/ui/PageHeader";
import { queryKeys } from "@/lib/queryKeys";

export default function SetupFormsPage() { return <FormBuilderGuard><FormsList /></FormBuilderGuard>; }
function FormsList() {
  const { data: templates = [], isLoading, isError } = useQuery({ queryKey: [...queryKeys.forms.templates,"builder"], queryFn: formsApi.builderTemplates });
  return <div className="space-y-7"><PageHeader title="Saved company forms" description="Your drafts and published forms are saved here. Open a form to preview, edit or publish it." action={<RequireCapability capabilities={[CAPABILITIES.MANAGE_FORM_TEMPLATES]}><Link href="/settings/forms/new"><Button iconLeft={<Plus size={16} />}>Create form</Button></Link></RequireCapability>} />
    <section className="rounded-xl border p-5"><h2 className="font-semibold">From an idea to a working form</h2><p className="mt-2 text-sm">Choose a purpose → add questions and who can submit → save a draft → review the preview → publish. Only eligible users can use published forms. Their answers are saved separately as submissions.</p><Link className="mt-3 inline-block underline" href="/settings/onboarding?step=forms">Back to forms setup</Link></section>
    <RequireCapability capabilities={[CAPABILITIES.MANAGE_FORM_TEMPLATES]}><details className="rounded-xl border p-5"><summary className="cursor-pointer font-semibold">Add ready-made forms to your company</summary><div className="mt-5"><FormTemplateLibrary/></div></details></RequireCapability>
    {isError ? <p role="alert">Unable to load forms. Please try again.</p> : isLoading ? <div className="h-32 animate-pulse bg-neutral-200" /> : <div className="space-y-3">{!templates.length&&<p className="rounded-xl border border-dashed p-6">No saved forms yet. Choose Create form to start with a reporting, collections or other company form.</p>}{templates.map((template) => <Link key={template.id} href={`/settings/forms/${template.id}`} className="flex items-center justify-between border border-neutral-200 bg-white p-5 hover:border-neutral-400"><div><p className="text-xs font-semibold uppercase text-neutral-500">{template.category} · Version {template.version}</p><h2 className="mt-1 font-semibold text-neutral-950">{template.name}</h2><p className="mt-1 text-sm text-neutral-600">{template.fields.length} fields · {template.allow_drafts ? "Drafts allowed" : "Submit only"}</p></div><span className="text-xs font-semibold text-neutral-600">{template.lifecycle_status ?? "DRAFT"}</span></Link>)}</div>}
  </div>;
}
