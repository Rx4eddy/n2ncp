from django.contrib import admin

from .models import EmailOutbox, ReminderDelivery, ReminderPreference


@admin.register(EmailOutbox)
class OutboxAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "recipient",
        "status",
        "attempts",
        "available_at",
        "sent_at",
        "last_error",
    ]
    list_filter = ["status"]
    search_fields = ["recipient"]
    readonly_fields = [
        "recipient",
        "subject",
        "body",
        "headers",
        "reminder",
        "status",
        "attempts",
        "claimed_at",
        "available_at",
        "created_at",
        "sent_at",
        "last_error",
    ]

    def has_add_permission(self, request):
        return False


admin.site.register(ReminderPreference)
admin.site.register(ReminderDelivery)
