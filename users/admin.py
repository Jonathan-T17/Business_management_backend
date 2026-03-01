from django.contrib import admin

# Register your models here.
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'role', 'company', 'branch', 'is_active', 'is_staff')
    list_filter = ('role', 'company', 'branch', 'is_active')
    search_fields = ('email', 'full_name')
    ordering = ('email',)