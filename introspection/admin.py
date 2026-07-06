from django.contrib import admin

from introspection.models import ColumnDoc, SchemaSnapshot, TableDoc


class ColumnDocInline(admin.TabularInline):
    model = ColumnDoc
    extra = 0


@admin.register(TableDoc)
class TableDocAdmin(admin.ModelAdmin):
    list_display = ("table_name", "snapshot", "row_count_estimate")
    search_fields = ("table_name",)
    inlines = [ColumnDocInline]


@admin.register(SchemaSnapshot)
class SchemaSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "connection", "created_at")
    list_filter = ("connection",)
