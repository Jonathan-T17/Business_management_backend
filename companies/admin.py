from django.contrib import admin

# Register your models here.
from .models import Company, Branch, CompanyInvite

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'manager', 'is_active')
    list_filter = ('company', 'is_active')
    search_fields = ('name',)

@admin.register(CompanyInvite)
class CompanyInviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'company', 'role', 'is_used', 'expires_at')
    list_filter = ('company', 'role', 'is_used')
    search_fields = ('email',)
