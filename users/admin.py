from django.contrib import admin
from .models import User

# Register your models here.
admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'role', 'company', 'is_active', 'is_staff')
    search_fields = ('email', 'full_name')
    list_filter = ('role', 'is_active', 'is_staff')
    ordering = ('email',)