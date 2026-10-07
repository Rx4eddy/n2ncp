from django.contrib import admin

from .models import Problem, Topic


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ["title", "platform", "difficulty", "curated"]
    list_filter = ["platform", "difficulty", "curated"]
    search_fields = ["title", "problem_id"]
    filter_horizontal = ["topics"]


admin.site.register(Topic)
