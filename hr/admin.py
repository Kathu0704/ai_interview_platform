from django.contrib import admin
from .models import HR

@admin.register(HR)
class HRAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'field_of_expertise', 'years_of_experience', 'is_active', 'created_at')
    list_filter = ('field_of_expertise', 'gender', 'is_active', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Personal Details', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'gender', 'date_of_birth')
        }),
        ('Professional Details', {
            'fields': ('field_of_expertise', 'designations_handled', 'years_of_experience', 'specialization_skills')
        }),
        ('Login Credentials', {
            'fields': ('username', 'password', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
