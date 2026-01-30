from django.contrib import admin
from .models import Admin

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email', 'name')
    readonly_fields = ('created_at',)
