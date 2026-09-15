from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import APIException
from core.capabilities import Capabilities as C
from core.visibility import VisibilityService
from .access import FormAccess
from .models import FormTemplate, FormField, FormSubmission
from .versioning import FormTemplateVersionService as Versions

class FieldFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors): return
        fields=[{key:form.cleaned_data.get(key) for key in Versions.FIELDS if key in form.cleaned_data} for form in self.forms if form.cleaned_data and not form.cleaned_data.get('DELETE')]
        config={key:getattr(self.instance,key) for key in Versions.CONFIG}
        try:
            Versions.validate(actor=self.actor,company=self.actor.company,data=config,fields=fields)
        except APIException as exc:
            raise DjangoValidationError(str(exc.detail))

class FormFieldInline(admin.TabularInline):
    model=FormField
    extra=0
    def get_formset(self,request,obj=None,**kwargs):
        actor=request.user
        class BoundFormSet(FieldFormSet): pass
        BoundFormSet.actor=actor
        kwargs['formset']=BoundFormSet
        return super().get_formset(request,obj,**kwargs)
    def has_change_permission(self,request,obj=None):
        return bool(obj and obj.lifecycle_status=='DRAFT' and not obj.submissions.exists() and FormAccess.has(request.user,C.MANAGE_FORM_TEMPLATES))
    def has_add_permission(self,request,obj=None):
        return self.has_change_permission(request,obj)
    def has_delete_permission(self,request,obj=None):
        return self.has_change_permission(request,obj)

@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return self.has_view_permission(request)
    list_display=('name','company','version','lifecycle_status')
    inlines=[FormFieldInline]
    actions=['revise_versions','publish_versions','retire_versions']
    def get_queryset(self,request):
        return FormAccess.templates(request.user,super().get_queryset(request),builder=True)
    def has_view_permission(self,request,obj=None):
        return FormAccess.has(request.user,C.MANAGE_FORM_TEMPLATES) or FormAccess.has(request.user,C.PUBLISH_FORM_TEMPLATES)
    def has_change_permission(self,request,obj=None):
        return self.has_view_permission(request,obj)
    def has_add_permission(self,request): return FormAccess.has(request.user,C.MANAGE_FORM_TEMPLATES)
    def save_model(self,request,obj,form,change):
        obj.company=request.user.company
        if not change:
            obj.created_by=request.user;obj.lifecycle_status='DRAFT';obj.is_active=False
        Versions.authorize(request.user,obj.company)
        obj.save()
        Versions.audit(obj,request.user,'Saved form draft in Django admin')
    def has_delete_permission(self,request,obj=None): return False
    def get_readonly_fields(self,request,obj=None):
        if not FormAccess.has(request.user,C.MANAGE_FORM_TEMPLATES) or obj and (obj.lifecycle_status!='DRAFT' or obj.submissions.exists()):
            return [field.name for field in self.model._meta.fields]
        return ('company','version','supersedes','lifecycle_status','is_active','created_by','created_at','updated_at')
    @admin.action(description='Create draft revisions of selected forms')
    def revise_versions(self,request,queryset):
        for template in queryset: Versions.revise(template=template,actor=request.user,data={})
    @admin.action(description='Publish selected draft versions')
    def publish_versions(self,request,queryset):
        for template in queryset: Versions.publish(template=template,actor=request.user)
    @admin.action(description='Retire selected versions')
    def retire_versions(self,request,queryset):
        for template in queryset: Versions.retire(template=template,actor=request.user)

@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return self.has_view_permission(request)
    list_display=('reference_number','company','status','template_version')
    exclude=('data',)
    def get_readonly_fields(self,request,obj=None):
        from .policy import FormSubmissionDisclosurePolicy
        import json
        def answers(instance):
            return json.dumps(FormSubmissionDisclosurePolicy.data_for(submission=instance,user=request.user),ensure_ascii=False,indent=2)
        answers.short_description='Answers (permission filtered)'
        return [field.name for field in self.model._meta.fields if field.name!='data']+[answers]
    def get_queryset(self,request):
        return VisibilityService.form_submissions_queryset(user=request.user,queryset=super().get_queryset(request))
    def has_view_permission(self,request,obj=None):
        return FormAccess.has(request.user,C.VIEW_FORM_SUBMISSIONS) or FormAccess.has(request.user,C.REVIEW_SUBMISSIONS)
    def has_change_permission(self,request,obj=None): return False
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
from .models import FormStarter
@admin.register(FormStarter)
class FormStarterAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return self.has_view_permission(request)
    list_display=('name','code','category','is_active')
    def has_view_permission(self,request,obj=None):
        return bool(request.user.is_active and request.user.is_staff and request.user.is_superuser)
    def has_add_permission(self,request): return self.has_view_permission(request)
    def has_change_permission(self,request,obj=None): return self.has_view_permission(request,obj)
    def has_delete_permission(self,request,obj=None): return False
