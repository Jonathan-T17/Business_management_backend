from pathlib import Path
base=Path('.notification-fix/simple-forms/src')
p=base/'api/formsApi.ts';s=p.read_text(encoding='utf-8');old='  async builderTemplates(): Promise<FormTemplate[]> { return extractResults<FormTemplate>((await api.get("form-templates/", {params:{mode:"builder"}})).data); },'
new='''  async builderTemplates(): Promise<FormTemplate[]> {
    const forms:FormTemplate[]=[];let page=1;
    while(true){const result=collectionPage<FormTemplate>((await api.get("form-templates/",{params:{mode:"builder",page}})).data);forms.push(...result.results);if(!result.next)break;page+=1;}
    return forms;
  },'''
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf-8')
p=base/'components/forms/CompanyFormsWorkspace.tsx';s=p.read_text(encoding='utf-8').replace('onSaved={()=>setTab("company")}','onSaved={()=>{setSearch("");setTab("company");}}');s=s.replace('className="flex gap-2 border-b border-[var(--line)] pb-3"','onKeyDown={event=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(event.key)&&access.formManagement){event.preventDefault();const next=event.key==="Home"?"company":event.key==="End"?"library":tab==="company"?"library":"company";setTab(next);event.currentTarget.querySelector<HTMLButtonElement>(next==="company"?"#company-forms-tab":"#library-forms-tab")?.focus();}}} className="flex gap-2 border-b border-[var(--line)] pb-3"');p.write_text(s,encoding='utf-8')
p=base/'components/forms/FormDetail.tsx';s=p.read_text(encoding='utf-8');archive='{allowed.includes("ARCHIVE")&&<Button variant="outline" loading={archive.isPending} onClick={()=>archive.mutate()}>Retire version</Button>}'
s=s.replace(archive,'')
s=s.replace('{allowed.includes("COPY")&&<details','{(allowed.includes("COPY")||allowed.includes("ARCHIVE"))&&<details')
s=s.replace('More options · Copy this form</summary><form','More options</summary>'+archive+'{allowed.includes("COPY")&&<form')
s=s.replace('</Button></form></details>}','</Button></form>}</details>}');p.write_text(s,encoding='utf-8')
