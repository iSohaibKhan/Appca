from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'account', 'action', 'entity_type', 'entity_id',
        'old_value', 'new_value', 'is_automated', 'created_at'
    ]
    list_filter = ['action', 'is_automated', 'created_at']
    search_fields = ['entity_id', 'reason', 'account__account_name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

