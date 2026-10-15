"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formsApi } from "@/api/formsApi";
import { Button } from "@/components/ui/Button";
import { normalizeApiError } from "@/utils/apiError";
import { formatEnumLabel } from "@/utils/format";
import type { FormTemplatePayload } from "@/types/forms";

const groups = ["All forms", "Reporting", "Materials and deliveries", "Collections", "Expenses and purchasing", "People", "Stock and assets", "Inspections and incidents", "Other"];
function group(code: string, category: string) {
  if (code.startsWith("material-")) return "Materials and deliveries";
  if (["leave-request", "attendance-correction", "employee-service"].includes(code)) return "People";
  if (["expense-request", "purchase-request", "reimbursement"].includes(code)) return "Expenses and purchasing";
  if (code.startsWith("stock-") || code === "equipment-issue") return "Stock and assets";
  if (category.includes("REPORT")) return "Reporting";
  if (category === "COLLECTION") return "Collections";
  if (["INSPECTION", "INCIDENT", "MAINTENANCE"].includes(category)) return "Inspections and incidents";
  return "Other";
}
export function FormTemplateLibrary({ onChoose, onSaved }: { onChoose?: (form: FormTemplatePayload) => void; onSaved?: () => void }) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All forms");
  const [selected, setSelected] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["forms", "starters"], queryFn: formsApi.starters });
  const saved = useQuery({ queryKey: ["forms", "setup-library"], queryFn: formsApi.builderTemplates, enabled: !onChoose });
  const add = useMutation({ mutationFn: formsApi.selectStarters, onSuccess: async result => {
    setSelected([]);
    setMessage(`${result.created.length} company drafts saved. ${result.existing.length ? `${result.existing.length} forms were already saved. ` : ""}Review each form before publishing.`);
    await qc.invalidateQueries({ queryKey: ["forms"] });
    onSaved?.();
  }});
  const error = add.error ? normalizeApiError(add.error) : null;
  const visible = (query.data ?? []).filter(form => (category === "All forms" || group(form.code, form.category) === category) && `${form.name} ${form.description ?? ""}`.toLowerCase().includes(search.toLowerCase()));
  return <section className="space-y-5">
    <div><h2 className="text-xl font-semibold">Ready-made form library</h2><p className="mt-2 text-sm text-[var(--muted)]">Choose useful forms, adjust your company copies, then preview and publish. No business-sector selection is required.</p></div>
    <div className="grid gap-3 sm:grid-cols-2"><label className="text-sm font-medium">Search forms<input className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3" value={search} onChange={e => setSearch(e.target.value)} placeholder="For example: materials, leave, collections" /></label><label className="text-sm font-medium">Form category<select className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3" value={category} onChange={e => setCategory(e.target.value)}>{groups.map(name => <option key={name}>{name}</option>)}</select></label></div>
    {query.isPending ? <p role="status">Loading templates…</p> : query.isError ? <p role="alert">Unable to load templates. <button className="underline" onClick={() => query.refetch()}>Try again</button></p> : <>
      {!onChoose && <div className="sb-context-note flex-wrap"><p className="flex-1 text-sm">{selected.length} selected · Saved as drafts, never published automatically.</p><Button loading={add.isPending} disabled={!selected.length || saved.isPending || saved.isError} onClick={() => add.mutate(selected)}>Add selected forms</Button></div>}
      {saved.isError && !onChoose && <p role="alert">Unable to check saved company forms. <button className="underline" onClick={() => saved.refetch()}>Try again</button></p>}
      {message && <p role="status" className="sb-notice">{message}</p>}
      {error && <p role="alert" className="sb-notice">{Object.values(error.fields).join(" ") || error.message}</p>}
      {!visible.length && <p className="rounded-xl border border-dashed p-6">No matching forms. Try a different search or category.</p>}
      <div className="grid gap-4 md:grid-cols-2">{visible.map(form => {
        const existing = saved.data?.some(item => item.code === form.code);
        return <article key={form.code} className="sb-form-choice">
          <p className="sb-eyebrow">{group(form.code, form.category)}</p><h3 className="mt-2 text-lg font-semibold">{form.name}</h3>
          <p className="mt-2 text-sm text-[var(--muted)]">{form.description || "Record your company’s work using prepared questions. Choose access and reviewers before publishing."}</p>
          <details className="mt-4 text-sm"><summary className="cursor-pointer font-medium">Preview {form.fields.length} questions</summary><ul className="mt-3 space-y-2">{form.fields.map(field => <li key={field.key}><span className="font-medium">{field.label}</span><span className="text-[var(--muted)]"> · {field.required ? "Required" : "Optional"} · {formatEnumLabel(field.field_type)}</span></li>)}</ul></details>
          <div className="mt-auto pt-4">{onChoose ? <Button variant="outline" onClick={() => onChoose(form)}>Adjust this template →</Button> : existing ? <p className="sb-soft-label">Already in your company library</p> : <label className="inline-flex items-center gap-2 font-medium"><input type="checkbox" checked={selected.includes(form.code)} disabled={add.isPending} onChange={e => setSelected(previous => e.target.checked ? [...previous, form.code] : previous.filter(code => code !== form.code))}/>Choose this form</label>}</div>
        </article>;
      })}</div>
    </>}
  </section>;
}
