from django.contrib import admin

from .models import Contest


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ["title", "platform", "start_at", "cancelled"]
    list_filter = ["platform", "cancelled"]
    search_fields = ["title"]
