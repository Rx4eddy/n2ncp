from django.contrib import admin

from .models import LinkedAccount, SyncRun


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ["platform", "kind", "started_at", "success", "detail"]
    list_filter = ["platform", "kind", "success"]
    readonly_fields = ["platform", "kind", "started_at", "finished_at", "success", "detail"]

    def has_add_permission(self, request):
        return False


@admin.register(LinkedAccount)
class LinkedAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "handle", "last_synced_at", "status"]
    readonly_fields = [
        "user",
        "platform",
        "handle",
        "verified_at",
        "sync_cursor",
        "last_synced_at",
        "status",
    ]

    def has_add_permission(self, request):
        return False
