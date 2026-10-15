from django.contrib import admin

# Register your models here.
from .models import Company, Branch, CompanyInvite

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('archived_at', 'recovery_until', 'archived_by', 'archive_reason', 'active_before_archive', 'deletion_hold_reason')

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (('is_active',) if obj and obj.archived_at else ())

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'manager', 'is_active')
    list_filter = ('company', 'is_active')
    search_fields = ('name',)

@admin.register(CompanyInvite)
class CompanyInviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'company', 'role', 'status', 'expires_at', 'accepted_at')
    list_filter = ('company', 'role', 'status', 'expires_at')
    search_fields = ('email', "company__name")
