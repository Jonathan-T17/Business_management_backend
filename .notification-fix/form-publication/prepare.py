from pathlib import Path
front = Path('C:/Users/1213/Desktop/Jonathan/business_management_frontend/src')
stage = Path(__file__).parent
def save(name, path, transform):
    text = (front/path).read_text(encoding='utf-8-sig')
    (stage/name).write_text(transform(text), encoding='utf-8')

def types(s):
    s = s.replace('export interface FormTemplate {', 'export interface FormPublicationSettings {audience: "COMPANY" | "HEADQUARTERS" | "BRANCHES"; branch_ids?: number[]; entry_visibility: "STANDARD" | "AUDIENCE"; share_confidential: boolean; confirm_confidential_access: boolean;}\nexport interface FormTemplate { audience_branch_ids?: number[]; entry_visibility?: "STANDARD" | "AUDIENCE"; share_confidential?: boolean;')
    return s
save('forms.ts', 'types/forms.ts', types)
save('formsApi.ts', 'api/formsApi.ts', lambda s: s.replace('FormTemplatePayload }', 'FormTemplatePayload, FormPublicationSettings }').replace('publishTemplate(templateId: string)', 'publishTemplate(templateId: string, settings?: FormPublicationSettings)').replace('api.post(`form-templates/${templateId}/publish/`)', 'api.post(`form-templates/${templateId}/publish/`, settings)').replace('  async archiveTemplate', '  async deleteTemplate(templateId: string): Promise<void> { await api.delete(`form-templates/${templateId}/`); },\n  async archiveTemplate'))

def detail(s):
    s = s.replace('import type { FormTemplatePayload }', 'import { FormPublication } from "./FormPublication";\nimport type { FormPublicationSettings, FormTemplatePayload }')
    s = s.replace(' const [previewValues', ' const [publishing,setPublishing]=useState(false);const [deleting,setDeleting]=useState(false);\n const [previewValues')
    s = s.replace('mutationFn:()=>formsApi.publishTemplate(id),onSuccess:refresh', 'mutationFn:(settings:FormPublicationSettings)=>formsApi.publishTemplate(id,settings),onSuccess:async()=>{setPublishing(false);await refresh();}')
    s = s.replace('mutationFn:()=>formsApi.archiveTemplate(id),onSuccess:refresh', 'mutationFn:()=>formsApi.deleteTemplate(id),onSuccess:async()=>{await refresh();if(onBack)onBack();else router.push("/forms");}')
    s = s.replace('onClick={()=>publish.mutate()}>Publish form', 'onClick={()=>setPublishing(true)}>Make available')
    s = s.replace('Saved draft — review before publishing', 'Not available yet — review, then make available')
    s = s.replace('Ready to use — available to permitted employees', 'Available to the published audience')
    s = s.replace('Retired form', 'Historical form version')
    s = s.replace(' {!editing&&template.library_update', ' {publishing&&<FormPublication pending={publish.isPending} onPublish={settings=>publish.mutate(settings)} onCancel={()=>setPublishing(false)}/>}\n {!editing&&template.library_update')
    # An ordinary publication is location-based, not a mandatory position assignment.
    begin=s.index(' {!editing&&["material-dispatch"')
    end=s.index(' {!editing&&!["material-dispatch"',begin)
    s=s[:begin]+s[end:]
    s = s.replace('{allowed.includes("ARCHIVE")&&<Button variant="outline" loading={archive.isPending} onClick={()=>archive.mutate()}>Remove from company forms</Button>}', '')
    s = s.replace(' {(allowed.includes("COPY")', ' {allowed.includes("ARCHIVE")&&<section className="sb-workspace-panel space-y-3">{deleting?<><p className="text-sm">Delete this form from Company forms? Employees will no longer start entries with it. Saved entries and files remain for review. Standard forms can be chosen again from the global library.</p><Button variant="outline" loading={archive.isPending} onClick={()=>archive.mutate()}>Confirm delete from company forms</Button><Button variant="ghost" disabled={archive.isPending} onClick={()=>setDeleting(false)}>Cancel</Button></>:<Button variant="outline" onClick={()=>setDeleting(true)}>Delete from company forms</Button>}</section>}\n {(allowed.includes("COPY")')
    return s
save('FormDetail.tsx', 'components/forms/FormDetail.tsx', detail)

def workspace(s):
    s=s.replace(' const [showRetired,setShowRetired]=useState(false);\n','')
    s=s.replace('(showRetired||form.lifecycle_status!=="ARCHIVED")', '(form.lifecycle_status!=="ARCHIVED")')
    s='\n'.join(line for line in s.split('\n') if 'Include removed forms' not in line)
    s=s.replace('form.lifecycle_status==="ARCHIVED"?"Removed":"Draft"', '"Not available yet"').replace('"Review draft":"Open form"', '"Review & make available":"Open form"')
    return s
save('CompanyFormsWorkspace.tsx', 'components/forms/CompanyFormsWorkspace.tsx', workspace)
save('FormTemplateLibrary.tsx', 'components/forms/FormTemplateLibrary.tsx', lambda s:s.replace('Choose selected forms','Add selected forms').replace('Choose form','Add to company').replace('Added as drafts.','Not available until published.').replace('then review and publish your company draft','then review and make it available to your company'))

def designer(s):
    begin=s.index(' {([[\'branch\'')
    end=s.index(' </section>',begin)
    original=s[begin:end]
    s=s[:begin]+' <details className="sm:col-span-2"><summary className="cursor-pointer text-sm font-medium">Special reporting exceptions</summary><p className="my-2 text-sm text-[var(--muted)]">Ordinary forms use location choices when you make them available. Keep these advanced restrictions only for special approved reporting routes.</p><div className="grid gap-4 sm:grid-cols-2">'+original+'</div></details>\n'+s[end:]
    s=s.replace('1. Name your form and choose who can use it.', '1. Name your form.').replace('3. Save a draft to review before publishing.', '3. Save it, then choose its audience in Make available.')
    return s
save('FormDesigner.tsx', 'components/forms/FormDesigner.tsx', designer)

def sidebar(s):
    s=s.replace('import { Fragment, useState }', 'import { useState }')
    s=s.replace('workspaceGroups as sections, workspaceFor as sectionFor, ', 'workspaceFor as sectionFor, ')
    s=s.replace('  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});\n','')
    begin=s.index('  const navigation =')
    end=s.index('  const content =',begin)
    s=s[:begin]+'''  const groups = ["Home", "Daily work", "Company", "Administration", "My account & help", "Planning"];
  const groupFor = (href:string) => href === "/dashboard" ? "Home" : ["/analytics", "/company", "/employees", "/documents", "/activity", "/branches", "/departments", "/teams", "/records", "/data-tools"].includes(href) ? "Company" : ["Forms & reporting", "Requests & approvals"].includes(sectionFor(href)) ? "Daily work" : sectionFor(href) === "Optional planning" ? "Planning" : ["My account", "Communication"].includes(sectionFor(href)) ? "My account & help" : "Administration";
  const navigation = allNavigation.filter(item => `${item.label} ${groupFor(item.href)}`.toLowerCase().includes(search.trim().toLowerCase()));
  const navigate = () => { setSearch(""); onMobileOpenChange(false); };

'''+s[end:]
    begin=s.index('        {!search.trim() && primary.map')
    end=s.index('      </nav>',begin)
    s=s[:begin]+'''        {groups.map(group => {const items=navigation.filter(item=>groupFor(item.href)===group);return !items.length?null:<section key={group} aria-label={group} className="pt-2"><h2 className="sb-nav-heading">{group}</h2>{items.map(item=>{const Icon=item.icon;const active=selected?.href===item.href;return <Link key={item.href} href={item.href} onClick={navigate} aria-current={active?"page":undefined} className="sb-nav-link flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium"><Icon className="h-5 w-5 shrink-0" aria-hidden="true"/><span>{item.label}</span></Link>;})}</section>;})}
'''+s[end:]
    return s
save('Sidebar.tsx', 'components/layout/Sidebar.tsx', sidebar)
save('MobileBottomNav.tsx','components/layout/MobileBottomNav.tsx',lambda s:s.replace('Open more navigation','Open workspace menu').replace('<span>More</span>','<span>Menu</span>'))
