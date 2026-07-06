from django.contrib import admin

from snapshots.models import SchemaDiff


@admin.register(SchemaDiff)
class SchemaDiffAdmin(admin.ModelAdmin):
    list_display = ("id", "connection", "from_snapshot", "to_snapshot", "created_at")
    list_filter = ("connection",)
