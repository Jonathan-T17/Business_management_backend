import { apiClient as api } from "./client";
import { collectionPage } from "./workspaceApi";
import { extractResults } from "@/utils/api";
import type { FormSubmission, FormTemplate, FormTemplatePayload, FormPublicationSettings } from "@/types/forms";
export interface MaterialProgress {id?:string;title?:string;reference:string;status:string;can_approve:boolean;items:Array<{id:string;item:string;unit:string;quantity:string;approved:string;dispatched:string;received:string;returned:string}>;stages:Record<string,Array<{id:string;name:string}>>;history:Array<{related_reference:string|null;reference:string;stage:string;note:string;created_at:string;quantities:Record<string,string>}>}
function submissionResult(raw: FormSubmission & { data?: Record<string, unknown> }): FormSubmission {
  const snapshot = raw.schema_snapshot as FormTemplate & { template_id?: string; template_name?: string; template_code?: string; template_version?: number };
  return { ...raw, values: raw.data ?? raw.values ?? {}, schema_snapshot: { ...snapshot, id: snapshot.template_id ?? snapshot.id, name: snapshot.template_name ?? snapshot.name, code: snapshot.template_code ?? snapshot.code, version: snapshot.template_version ?? snapshot.version } };
}
export const formsApi = {
  async submissions(page=1) {const data=collectionPage<FormSubmission & {data?:Record<string,unknown>}>((await api.get("form-submissions/",{params:{page}})).data);return {...data,results:data.results.map(submissionResult)};},
  async initialValues(id:string):Promise<{values:Record<string,unknown>}> {return (await api.get(`form-templates/${id}/initial-values/`)).data;},
  async applyLibraryUpdate(id:string, signature:string, version:number):Promise<FormTemplate> {return (await api.post(`form-templates/${id}/apply-library-update/`,{signature,version})).data;},
  async materialJourney(id:string):Promise<MaterialProgress> {return (await api.get(`form-submissions/${id}/materials/`)).data;},
  async materialsList(page=1):Promise<{count:number;next:string|null;previous:string|null;results:MaterialProgress[]}> {return (await api.get('form-submissions/materials/',{params:{page}})).data;},
  async moveMaterials(id:string,payload:{related_reference?:string;stage:string;template_id:string;quantities:Record<string,string>;reference:string;note:string;answers:Record<string,unknown>}):Promise<MaterialProgress> {return (await api.post(`form-submissions/${id}/materials/`,payload)).data;},
  async approveMaterials(id:string,quantities:Record<string,string>,note:string):Promise<MaterialProgress> {return (await api.post(`form-submissions/${id}/approve-materials/`,{quantities,note})).data;},
  async configureReview(id: string, route: string, headquarters_position?: number): Promise<FormTemplate> { return (await api.post(`form-templates/${id}/configure-review/`, {route, headquarters_position})).data; },
  async selectStarters(codes: string[]): Promise<{created:FormTemplate[];existing:FormTemplate[]}> { return (await api.post('form-templates/select-starters/', {codes})).data; },
  async attachments(id: string): Promise<{can_upload:boolean;can_remove:boolean;restricted:boolean;files:Array<{id:string;name:string;size:number}>}> { return (await api.get(`form-submissions/${id}/attachments/`)).data; },
  async uploadAttachment(id: string, file: File) { const data = new FormData(); data.append("file", file); return (await api.post(`form-submissions/${id}/attachments/`, data, { headers: { "Content-Type": "multipart/form-data" } })).data; },
  async removeAttachment(id: string, fileId: string) { await api.delete(`form-submissions/${id}/attachments/${fileId}/`); },
  async downloadAttachment(id: string, fileId: string): Promise<Blob> { return (await api.get(`form-submissions/${id}/attachments/${fileId}/`, {responseType:"blob"})).data; },
  async requestTypes(): Promise<Array<{id:number;code:string;name:string;amount_enabled:boolean;quantity_enabled:boolean;needed_by_enabled:boolean;form_template_id:string|null}>> { return (await api.get("form-templates/request_types/")).data; },
  async choices(): Promise<Record<"branches"|"departments"|"teams"|"workflows",Array<{id:number|string;name:string}>> & {people:Array<{id:string;name:string}>;headquarters_positions:Array<{id:number;title:string}>;positions:Array<{id:number;title:string}>}> { return (await api.get("form-templates/choices/")).data; },
  async builderTemplates(): Promise<FormTemplate[]> {
    const forms:FormTemplate[]=[];let page=1;
    while(true){const result=collectionPage<FormTemplate>((await api.get("form-templates/",{params:{mode:"builder",page}})).data);forms.push(...result.results);if(!result.next)break;page+=1;}
    return forms;
  },
  async starters(): Promise<FormTemplatePayload[]> { return (await api.get("form-templates/starters/")).data; },
  async copyTemplate(id: string, name: string, code: string): Promise<FormTemplate> { return (await api.post(`form-templates/${id}/copy/`,{name,code})).data; },
  async templates(): Promise<FormTemplate[]> { return extractResults<FormTemplate>((await api.get("form-templates/")).data); },
  async template(templateId: string): Promise<FormTemplate> { return (await api.get(`form-templates/${templateId}/`)).data; },
  async createTemplate(payload: FormTemplatePayload): Promise<FormTemplate> { return (await api.post("form-templates/", payload)).data; },
  async updateTemplate(templateId: string, payload: Partial<FormTemplatePayload>): Promise<FormTemplate> { return (await api.patch(`form-templates/${templateId}/`, payload)).data; },
  async publishTemplate(templateId: string, settings?: FormPublicationSettings): Promise<FormTemplate> { return (await api.post(`form-templates/${templateId}/publish/`, settings)).data; },
  async deleteTemplate(templateId: string): Promise<void> { await api.delete(`form-templates/${templateId}/`); },
  async archiveTemplate(templateId: string): Promise<FormTemplate> { return (await api.post(`form-templates/${templateId}/archive/`)).data; },
  async reorderFields(templateId: string, fieldIds: string[]): Promise<FormTemplate> { return (await api.post(`form-templates/${templateId}/reorder-fields/`, { field_ids: fieldIds })).data; },
  async submission(submissionId: string): Promise<FormSubmission> { return submissionResult((await api.get(`form-submissions/${submissionId}/`)).data); },
  async createDraft(templateId: string, values: Record<string, unknown>) { return submissionResult((await api.post("form-submissions/", { template: templateId, data: values })).data); },
  async update(submissionId: string, values: Record<string, unknown>) { return submissionResult((await api.patch(`form-submissions/${submissionId}/`, { data: values })).data); },
  async submit(submissionId: string) { return submissionResult((await api.post(`form-submissions/${submissionId}/submit/`)).data.submission); },
};


