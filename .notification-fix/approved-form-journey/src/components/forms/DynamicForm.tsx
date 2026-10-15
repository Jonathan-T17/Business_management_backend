"use client";

import { useId } from "react";
import type { FormField, FormTemplate } from "@/types/forms";

interface DynamicFormProps {
  template: FormTemplate;
  values: Record<string, unknown>;
  errors?: Record<string, string>;
  onChange: (key: string, value: unknown) => void;
  disabled?: boolean;
}

function fieldOptions(field: FormField) {
  return (field.options ?? []).map((option) => {
    if (typeof option === "object" && option !== null) {
      const value = option as { value?: string; label?: string };
      return { value: value.value ?? value.label ?? "", label: value.label ?? value.value ?? "" };
    }

    return { value: String(option), label: String(option) };
  });
}

export function isFieldVisible(field: FormField, values: Record<string, unknown>) {
  const condition = field.validation_rules?.show_when;
  return !condition || String(values[condition.field] ?? "").toLowerCase() === String(condition.equals).toLowerCase();
}

export function DynamicForm({ template, values, errors = {}, onChange, disabled }: DynamicFormProps) {
  const visible = [...template.fields].filter(field => isFieldVisible(field, values)).sort((a,b)=>a.order-b.order);
  const sections = [...new Set(visible.map(field=>field.validation_rules?.section || "Form details"))];
  return <div className="space-y-6">{sections.map(section=><section key={section} className="space-y-5"><h2 className="border-b border-[var(--line)] pb-2 text-base font-semibold text-[var(--ink)]">{section}</h2>{visible.filter(field=>(field.validation_rules?.section || "Form details")===section).map(field=><DynamicField key={field.key} field={field} starterCode={template.source_starter || template.starter_code} value={values[field.key]} error={errors[field.key]} disabled={disabled} onChange={value=>onChange(field.key,value)}/>)}</section>)}</div>;
}

function DynamicField({ field: originalField, starterCode, value, error, onChange, disabled }: {
  starterCode?: string;
  field: FormField;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
  disabled?: boolean;
}) {
  const legacyDifficulties = (starterCode === "daily-report" || originalField.label === "Blockers") && originalField.key === "blockers";
  const field = legacyDifficulties ? {...originalField, label: "Difficulties and support needed", help_text: originalField.help_text || "Describe anything that delayed or prevented your work and the help you need. Leave blank if there were no difficulties.", placeholder: originalField.placeholder || "Example: Work stopped because packaging supplies ran out. Please send more supplies."} : {...originalField};
  if (!field.help_text && field.key === "work_completed" && (starterCode === "daily-report" || field.label === "Work completed")) {
    field.help_text = "Describe what you did today and the result. Include quantities where useful.";
    field.placeholder = field.placeholder || "Example: Packed 120 boxes and delivered 100 to the branch store.";
  }
  const source = field.validation_rules?.default_source;
  const automatic = Boolean(source);
  const readOnly = source === "USER_NAME" || source === "COMPANY_NAME";
  disabled = disabled || readOnly;
  if (readOnly && !field.placeholder) field.placeholder = source === "USER_NAME" ? "Filled from your profile when you use this form" : "Filled from your company workspace";
  const inputId = useId();
  const controlProps = { id: inputId, "aria-required": field.required, "aria-invalid": Boolean(error), "aria-describedby": [field.help_text ? `${inputId}-help` : "", error ? `${inputId}-error` : ""].filter(Boolean).join(" ") || undefined };
  const inputClass = "mt-1.5 w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2.5 text-sm text-[var(--ink)] outline-none focus:border-neutral-700 disabled:bg-[var(--surface-soft)]";
  const options = fieldOptions(field);
  const label = <label htmlFor={inputId} className="text-sm font-medium text-[var(--ink)]">{field.label}<span className="ml-2 text-xs font-normal text-[var(--muted)]">{field.required ? "Required" : "Optional"}</span>{automatic && <span className="ml-2 inline-flex rounded-full bg-[var(--accent-soft)] px-2 py-0.5 text-xs text-[var(--accent-text)]">{readOnly ? "Automatic · read only" : "Starts automatically · editable"}</span>}</label>;

  let control: React.ReactNode;
  if (value === "[REDACTED]") {
    control = <p className="mt-2 rounded-lg bg-[var(--surface-soft)] p-3 text-sm text-[var(--muted)]">Restricted answer. Its saved value will be preserved.</p>;
  } else if (field.field_type === "ITEM_LIST") {
    const items = Array.isArray(value) ? value as Array<{item:string;quantity:string;unit:string}> : [];
    const update = (index:number, key:string, next:string) => onChange(items.map((item,i)=>i===index?{...item,[key]:next}:item));
    control = <fieldset id={inputId} className="mt-2 space-y-3" aria-label={field.label}>{items.map((item,index)=><div key={index} className="grid gap-2 rounded-xl border p-3 sm:grid-cols-3"><label className="text-sm">Item {index+1}<input className={inputClass} placeholder="Example: Cement" value={item.item} disabled={disabled} maxLength={255} onChange={e=>update(index,'item',e.target.value)}/></label><label className="text-sm">Quantity<input className={inputClass} placeholder="Example: 25" type="number" min="0.000001" step="0.000001" value={item.quantity} disabled={disabled} onChange={e=>update(index,'quantity',e.target.value)}/></label><label className="text-sm">Unit<input className={inputClass} value={item.unit} disabled={disabled} maxLength={255} placeholder="kg, litres, pieces…" onChange={e=>update(index,'unit',e.target.value)}/></label>{!disabled&&<button type="button" className="text-left text-sm underline" onClick={()=>onChange(items.filter((_,i)=>i!==index))}>Remove item {index+1}</button>}</div>)}{!disabled&&<button type="button" className="sb-action-link" disabled={items.length>=100} onClick={()=>onChange([...items,{item:'',quantity:'',unit:''}])}>Add item</button>}{disabled&&!items.length&&<p className="text-sm text-[var(--muted)]">No items entered.</p>}</fieldset>;
  } else if (field.field_type === "LOCATION") {
    const coordinates = value && typeof value === "object" ? value as Record<string, unknown> : {};
    control = <div className="grid grid-cols-2 gap-3">{(["latitude", "longitude"] as const).map(axis => <label key={axis} className="text-sm capitalize">{axis}<input aria-label={`${field.label}: ${axis}`} aria-invalid={Boolean(error)} className={inputClass} type="number" step="any" min={axis === "latitude" ? -90 : -180} max={axis === "latitude" ? 90 : 180} value={String(coordinates[axis] ?? "")} disabled={disabled} onChange={event => onChange({ ...coordinates, [axis]: event.target.value })} /></label>)}</div>;
  } else if (field.field_type === "LONG_TEXT") {
    control = <textarea {...controlProps} className={inputClass} value={String(value ?? "")} placeholder={field.placeholder} disabled={disabled} rows={4} onChange={(event) => onChange(event.target.value)} />;
  } else if (field.field_type === "BOOLEAN") {
    control = <select {...controlProps} className={inputClass} value={value === true ? "yes" : value === false ? "no" : ""} disabled={disabled} onChange={event => onChange(event.target.value === "" ? undefined : event.target.value === "yes")}><option value="">Choose Yes or No</option><option value="yes">Yes</option><option value="no">No</option></select>;
  } else if (field.field_type === "SELECT") {
    control = <select {...controlProps} className={inputClass} value={String(value ?? "")} disabled={disabled} onChange={(event) => onChange(event.target.value)}><option value="">Choose an answer</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>;
  } else if (field.field_type === "MULTISELECT") {
    const selected = Array.isArray(value) ? value.map(String) : [];
    control = <select {...controlProps} className={inputClass} value={selected} disabled={disabled} multiple onChange={(event) => onChange(Array.from(event.target.selectedOptions, (option) => option.value))}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>;
  } else {
    const type = field.field_type === "INTEGER" || field.field_type === "DECIMAL" ? "number" : field.field_type === "DATETIME" ? "datetime-local" : field.field_type === "PHONE" ? "tel" : field.field_type.toLowerCase();
    control = <input {...controlProps} className={inputClass} type={type} inputMode={field.field_type === "DECIMAL" ? "decimal" : field.field_type === "INTEGER" ? "numeric" : field.field_type === "PHONE" ? "tel" : undefined} value={String(value ?? "")} placeholder={field.placeholder} disabled={disabled} onChange={(event) => onChange(event.target.value)} />;
  }

  return <div>{label}{field.help_text && <p id={`${inputId}-help`} className="mt-1 text-xs text-[var(--muted)]">{field.help_text}</p>}{control}{error && <p id={`${inputId}-error`} role="alert" className="mt-1 text-xs text-red-600">{error}</p>}</div>;
}
