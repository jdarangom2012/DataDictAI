from django.contrib import admin

from ai_engine.models import NLQuery


@admin.register(NLQuery)
class NLQueryAdmin(admin.ModelAdmin):
    list_display = ("connection", "user", "question", "created_at")
    list_filter = ("connection",)
    readonly_fields = (
        "connection",
        "user",
        "question",
        "answer",
        "referenced_tables",
        "created_at",
    )
