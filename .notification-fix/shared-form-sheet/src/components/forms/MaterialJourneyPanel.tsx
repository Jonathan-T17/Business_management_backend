"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formsApi, type MaterialProgress } from "@/api/formsApi";
import { Button } from "@/components/ui/Button";
import { FormSheet } from "@/components/forms/FormSheet";
import { DynamicForm } from "@/components/forms/DynamicForm";
import { normalizeApiError } from "@/utils/apiError";
import { formatDateTime } from "@/utils/format";
type Movement = MaterialProgress['history'][number];
const displayQuantity = (amount:number) => Number(amount.toFixed(6));
function outstanding(data:MaterialProgress,event:Movement,key:string) {
 const confirmed=data.history.filter(next=>next.related_reference===event.reference).reduce((sum,next)=>sum+Number(next.quantities[key]??0),0);
 return Math.max(0,displayQuantity(Number(event.quantities[key]??0)-confirmed));
}
function openMovements(data:MaterialProgress,stage:string) {
 return data.history.filter(event=>event.stage===(stage==='RECEIPT'?'DISPATCH':'RECEIPT')&&data.items.some(item=>outstanding(data,event,item.id)>0));
}
function availableAmount(data:MaterialProgress,stage:string,key:string,related?:Movement) {
 const item=data.items.find(item=>item.id===key)!;
 return stage==='DISPATCH'?Math.max(0,displayQuantity(Number(item.approved)-Number(item.dispatched)+Number(item.returned))):related?outstanding(data,related,key):0;
}
export function MaterialJourneyPanel({id}:{id:string}) {
 const qc=useQueryClient(); const [stage,setStage]=useState('DISPATCH'); const [templateId,setTemplateId]=useState('');
 const [quantities,setQuantities]=useState<Record<string,string>>({}); const [answers,setAnswers]=useState<Record<string,unknown>>({});
 const [note,setNote]=useState(''); const [reference,setReference]=useState(()=>crypto.randomUUID()); const [message,setMessage]=useState('');
 const query=useQuery({queryKey:['forms','materials',id],queryFn:()=>formsApi.materialJourney(id)});
 const availableStages=Object.keys(query.data?.stages??{}).filter(key=>query.data?.stages[key]?.length&&(key==='DISPATCH'?query.data.items.some(item=>availableAmount(query.data!,key,item.id)>0):openMovements(query.data!,key).length>0));
 const activeStage=availableStages.includes(stage)?stage:availableStages[0]||stage;
 const [relatedReference,setRelatedReference]=useState('');
 const linkedEvents=query.data?openMovements(query.data,activeStage):[];
 const related=linkedEvents.find(event=>event.reference===relatedReference);
 const selectedId=query.data?.stages[activeStage]?.some(form=>form.id===templateId)?templateId:query.data?.stages[activeStage]?.[0]?.id||'';
 const template=useQuery({queryKey:['forms','template',selectedId],queryFn:()=>formsApi.template(selectedId),enabled:Boolean(selectedId)});
 const refresh=async()=>{await qc.invalidateQueries({queryKey:['forms']});setReference(crypto.randomUUID());setQuantities({});setAnswers({});setNote('');setRelatedReference('');setMessage('Material action saved. Quantities and progress have been updated.');};
 const move=useMutation({mutationFn:()=>formsApi.moveMaterials(id,{stage:activeStage,related_reference:related?.reference,template_id:selectedId,quantities,reference,note,answers}),onSuccess:refresh});
 const approve=useMutation({mutationFn:()=>formsApi.approveMaterials(id,Object.fromEntries((query.data?.items??[]).map(item=>[item.id,quantities[item.id]??item.quantity])),note),onSuccess:refresh});
 const error=move.error||approve.error; const normalizedError=error?normalizeApiError(error):null; const busy=move.isPending||approve.isPending;
 if(query.isPending)return <p role="status">Loading material progress…</p>;
 if(query.isError)return <p role="alert">Unable to load material progress. <button className="underline" onClick={()=>query.refetch()}>Retry</button></p>;
 const data=query.data!;
 return <section className="sb-workspace-panel space-y-5"><div><h2 className="text-xl font-semibold">Material request progress</h2><p className="mt-2 text-sm text-[var(--muted)]">{data.reference} · {data.status}</p><p className="mt-1 text-sm text-[var(--muted)]">Approval authorizes quantities. Delivery is complete after the branch confirms receipt. Received totals include returned items: received minus returned is the quantity kept.</p></div>
 <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">Requested, approved, dispatched, received and returned materials</caption><thead><tr>{['Item','Requested','Approved','Sent','Received','Returned'].map(label=><th className="p-2" key={label}>{label}</th>)}</tr></thead><tbody>{data.items.map(item=><tr key={item.id} className="border-t"><th scope="row" className="p-2 font-medium">{item.item}<span className="block text-xs text-[var(--muted)]">{item.unit}</span></th>{[item.quantity,item.approved,item.dispatched,item.received,item.returned].map((amount,index)=><td key={index} className="p-2">{amount}</td>)}</tr>)}</tbody></table></div>
 <ul className="grid gap-3 sm:grid-cols-2" aria-label="Materials remaining">{data.items.map(item=>{const kept=displayQuantity(Number(item.received)-Number(item.returned));const due=Math.max(0,displayQuantity(Number(item.approved)-kept));return <li key={item.id} className="rounded-xl border p-3 text-sm"><p className="font-medium">{item.item}</p><p className="mt-1 text-[var(--muted)]">{kept} {item.unit} kept · {due} {item.unit} still due from the approved amount</p></li>;})}</ul>
 {message&&<p role="status" className="sb-notice">{message}</p>}
 {error&&<p role="alert" className="sb-notice">{Object.values(normalizedError?.fields??{}).join(" ")||normalizedError?.message}</p>}
 {data.can_approve?<form className="space-y-3 rounded-xl border p-4" onSubmit={e=>{e.preventDefault();approve.mutate();}}><h3 className="font-semibold">Approve requested quantities</h3><p className="text-sm text-[var(--muted)]">Reduce an amount for partial approval. Enter zero for an item you cannot approve.</p>{data.items.map(item=><label key={item.id} className="block text-sm">{item.item} ({item.unit})<input className="mt-1 w-full rounded-lg border bg-[var(--surface)] p-3" type="number" min="0" max={item.quantity} step="0.000001" value={quantities[item.id]??item.quantity} disabled={busy} onChange={e=>setQuantities({...quantities,[item.id]:e.target.value})}/></label>)}<label className="block text-sm">Review note<textarea className="mt-1 w-full rounded-lg border bg-[var(--surface)] p-3" value={note} maxLength={4000} onChange={e=>setNote(e.target.value)}/></label><Button type="submit" loading={approve.isPending} disabled={busy}>Approve quantities</Button></form>:availableStages.length?<form className="space-y-4 rounded-xl border p-4" onSubmit={e=>{e.preventDefault();move.mutate();}}><h3 className="font-semibold">Record the next materials action</h3>
 <label className="block text-sm">Action<select className="mt-1 w-full rounded-lg border bg-[var(--surface)] p-3" value={activeStage} onChange={e=>{setStage(e.target.value);setRelatedReference('');setTemplateId('');setAnswers({});setQuantities({});setReference(crypto.randomUUID());}}>{['DISPATCH','RECEIPT','RETURN'].map(value=><option key={value} value={value} disabled={!availableStages.includes(value)}>{{DISPATCH:'Record dispatch / delivery',RECEIPT:'Confirm materials received',RETURN:'Return materials'}[value]}</option>)}</select></label>
 {availableStages.includes(activeStage)?<><label className="block text-sm">Company form<select className="mt-1 w-full rounded-lg border bg-[var(--surface)] p-3" value={selectedId} onChange={e=>{setTemplateId(e.target.value);setAnswers({});setReference(crypto.randomUUID());}}>{data.stages[activeStage].map(form=><option key={form.id} value={form.id}>{form.name}</option>)}</select></label>
 {activeStage!=='DISPATCH'&&<label className="block text-sm">{activeStage==='RECEIPT'?'Delivery being received':'Receipt being returned'}<select required className="mt-1 w-full rounded-lg border bg-[var(--surface)] p-3" value={related?.reference??''} onChange={e=>{setRelatedReference(e.target.value);setReference(crypto.randomUUID());}}><option value="">Choose a recorded {activeStage==='RECEIPT'?'delivery':'receipt'}</option>{linkedEvents.map((event,index)=><option key={event.reference} value={event.reference}>{index+1} · {formatDateTime(event.created_at)} · {data.items.filter(item=>outstanding(data,event,item.id)>0).map(item=>`${item.item}: ${outstanding(data,event,item.id)} ${item.unit} remaining`).join(', ')}</option>)}</select></label>}
 {data.items.map(item=><label key={item.id} className="block text-sm">{item.item} · quantity for this action ({item.unit})<input className="mt-1 w-full rounded-lg border bg-[var(--surface)] p-3" type="number" min="0" max={availableAmount(data,activeStage,item.id,related)} step="0.000001" value={quantities[item.id]??''} disabled={busy||availableAmount(data,activeStage,item.id,related)===0} onChange={e=>setQuantities({...quantities,[item.id]:e.target.value})}/><span className="mt-1 block text-xs text-[var(--muted)]">Available: {availableAmount(data,activeStage,item.id,related)} {item.unit}</span></label>)}
 {template.data&&<FormSheet title={template.data.name} category={template.data.category}><DynamicForm template={{...template.data,fields:template.data.fields.filter(field=>!['items','request_reference','original_reference','delivery_reference'].includes(field.key))}} values={answers} disabled={busy} onChange={(key,value)=>setAnswers({...answers,[key]:value})}/></FormSheet>}
 {template.isError&&<p role="alert">Unable to load the company form. <button type="button" className="underline" onClick={()=>template.refetch()}>Retry</button></p>}
 <label className="block text-sm">Action note<textarea className="mt-1 w-full rounded-lg border bg-[var(--surface)] p-3" maxLength={4000} value={note} onChange={e=>setNote(e.target.value)}/></label><Button type="submit" loading={move.isPending} disabled={busy||!template.data||template.isError||(activeStage!=='DISPATCH'&&!related)}>Save materials action</Button></>:<p className="text-sm text-[var(--muted)]">Nothing is outstanding for this action. Available actions appear when a delivery is sent or items can be returned.</p>}</form>:<p className="text-sm text-[var(--muted)]">{Object.values(data.stages).some(forms=>forms.length)?'No materials actions are outstanding for your account.':'Materials actions appear after approval and when your company publishes the stage forms for your position.'}</p>}
 <div><h3 className="font-semibold">Delivery history</h3>{data.history.length?<ol className="mt-3 space-y-3">{data.history.map((event,index)=><li key={event.reference} className="rounded-xl border p-3 text-sm"><p className="font-medium">{{DISPATCH:'Dispatched',RECEIPT:'Received',RETURN:'Returned'}[event.stage]} · {formatDateTime(event.created_at)}</p><p className="mt-1 text-xs text-[var(--muted)]">Action {index+1}{event.related_reference&&` · Linked to action ${data.history.findIndex(source=>source.reference===event.related_reference)+1}`}</p><p className="mt-2">{data.items.filter(item=>Number(event.quantities[item.id])>0).map(item=>`${item.item}: ${event.quantities[item.id]} ${item.unit}`).join(', ')}</p>{event.note&&<p className="mt-2">{event.note}</p>}</li>)}</ol>:<p className="mt-2 text-sm text-[var(--muted)]">No delivery actions recorded yet.</p>}</div>
 </section>;
}
