from django.contrib import admin

from connections.models import DatabaseConnection


@admin.register(DatabaseConnection)
class DatabaseConnectionAdmin(admin.ModelAdmin):
    # encrypted_credentials is intentionally excluded: never rendered, even encrypted.
    list_display = ("name", "user", "engine", "status", "last_synced_at", "created_at")
    list_filter = ("engine", "status")
    search_fields = ("name", "user__username", "user__email")
    exclude = ("encrypted_credentials",)
    readonly_fields = ("created_at",)
