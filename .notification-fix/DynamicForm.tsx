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
  return (
    <div className="space-y-5">
      {[...template.fields].filter(field => isFieldVisible(field, values)).sort((first, second) => first.order - second.order).map((field) => (
        <DynamicField
          key={field.key}
          field={field}
          value={values[field.key]}
          error={errors[field.key]}
          disabled={disabled}
          onChange={(value) => onChange(field.key, value)}
        />
      ))}
    </div>
  );
}

function DynamicField({ field, value, error, onChange, disabled }: {
  field: FormField;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
  disabled?: boolean;
}) {
  const inputId = useId();
  const controlProps = { id: inputId, "aria-required": field.required, "aria-invalid": Boolean(error), "aria-describedby": [field.help_text ? `${inputId}-help` : "", error ? `${inputId}-error` : ""].filter(Boolean).join(" ") || undefined };
  const inputClass = "mt-1.5 w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2.5 text-sm text-[var(--ink)] outline-none focus:border-neutral-700 disabled:bg-[var(--surface-soft)]";
  const options = fieldOptions(field);
  const label = <label htmlFor={inputId} className="text-sm font-medium text-[var(--ink)]">{field.label}{field.required && <span className="ml-1 text-red-600">*</span>}</label>;

  let control: React.ReactNode;
  if (value === "[REDACTED]") {
    control = <p className="mt-2 rounded-lg bg-neutral-100 p-3 text-sm text-neutral-600">Restricted answer. Its saved value will be preserved.</p>;
  } else if (field.field_type === "ITEM_LIST") {
    const items = Array.isArray(value) ? value as Array<{item:string;quantity:string;unit:string}> : [];
    const update = (index:number, key:string, next:string) => onChange(items.map((item,i)=>i===index?{...item,[key]:next}:item));
    control = <fieldset id={inputId} className="mt-2 space-y-3" aria-label={field.label}>{items.map((item,index)=><div key={index} className="grid gap-2 rounded-xl border p-3 sm:grid-cols-3"><label className="text-sm">Item {index+1}<input className={inputClass} value={item.item} disabled={disabled} maxLength={255} onChange={e=>update(index,'item',e.target.value)}/></label><label className="text-sm">Quantity<input className={inputClass} type="number" min="0.000001" step="0.000001" value={item.quantity} disabled={disabled} onChange={e=>update(index,'quantity',e.target.value)}/></label><label className="text-sm">Unit<input className={inputClass} value={item.unit} disabled={disabled} maxLength={255} placeholder="kg, litres, pieces…" onChange={e=>update(index,'unit',e.target.value)}/></label>{!disabled&&<button type="button" className="text-left text-sm underline" onClick={()=>onChange(items.filter((_,i)=>i!==index))}>Remove item {index+1}</button>}</div>)}{!disabled&&<button type="button" className="sb-action-link" disabled={items.length>=100} onClick={()=>onChange([...items,{item:'',quantity:'',unit:''}])}>Add item</button>}{disabled&&!items.length&&<p className="text-sm text-[var(--muted)]">No items entered.</p>}</fieldset>;
  } else if (field.field_type === "LOCATION") {
    const coordinates = value && typeof value === "object" ? value as Record<string, unknown> : {};
    control = <div className="grid grid-cols-2 gap-3">{(["latitude", "longitude"] as const).map(axis => <label key={axis} className="text-sm capitalize">{axis}<input aria-label={`${field.label}: ${axis}`} aria-invalid={Boolean(error)} className={inputClass} type="number" step="any" min={axis === "latitude" ? -90 : -180} max={axis === "latitude" ? 90 : 180} value={String(coordinates[axis] ?? "")} disabled={disabled} onChange={event => onChange({ ...coordinates, [axis]: event.target.value })} /></label>)}</div>;
  } else if (field.field_type === "LONG_TEXT") {
    control = <textarea {...controlProps} className={inputClass} value={String(value ?? "")} placeholder={field.placeholder} disabled={disabled} rows={4} onChange={(event) => onChange(event.target.value)} />;
  } else if (field.field_type === "BOOLEAN") {
    control = <input {...controlProps} type="checkbox" className="mt-2 h-5 w-5 rounded border-neutral-300" checked={Boolean(value)} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />;
  } else if (field.field_type === "SELECT") {
    control = <select {...controlProps} className={inputClass} value={String(value ?? "")} disabled={disabled} onChange={(event) => onChange(event.target.value)}><option value="">Select an option</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>;
  } else if (field.field_type === "MULTISELECT") {
    const selected = Array.isArray(value) ? value.map(String) : [];
    control = <select {...controlProps} className={inputClass} value={selected} disabled={disabled} multiple onChange={(event) => onChange(Array.from(event.target.selectedOptions, (option) => option.value))}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>;
  } else {
    const type = field.field_type === "INTEGER" || field.field_type === "DECIMAL" ? "number" : field.field_type === "DATETIME" ? "datetime-local" : field.field_type === "PHONE" ? "tel" : field.field_type.toLowerCase();
    control = <input {...controlProps} className={inputClass} type={type} inputMode={field.field_type === "DECIMAL" ? "decimal" : field.field_type === "INTEGER" ? "numeric" : field.field_type === "PHONE" ? "tel" : undefined} value={String(value ?? "")} placeholder={field.placeholder} disabled={disabled} onChange={(event) => onChange(event.target.value)} />;
  }

  return <div>{label}{field.help_text && <p id={`${inputId}-help`} className="mt-1 text-xs text-[var(--muted)]">{field.help_text}</p>}{control}{error && <p id={`${inputId}-error`} role="alert" className="mt-1 text-xs text-red-600">{error}</p>}</div>;
}
