from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as accounts
from apps.contests.views import calendar
from apps.journal import views as journal
from apps.notifications.views import unsubscribe
from apps.practice import views as practice
from apps.recommendations.views import recommendations

from .views import dashboard, health

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("profile/", accounts.profile, name="profile"),
    path("profile/link/", accounts.link_account, name="link"),
    path("profile/verify/<int:pk>/", accounts.verify_account, name="verify"),
    path("profile/unlink/<int:pk>/", accounts.unlink_account, name="unlink"),
    path("profile/sync/<int:pk>/", accounts.sync_now, name="sync"),
    path("calendar/", calendar, name="calendar"),
    path("journal/", journal.journal, name="journal"),
    path("journal/<int:pk>/notes/", journal.edit_notes, name="notes"),
    path("journal/<int:pk>/delete/", journal.delete_entry, name="delete_entry"),
    path("recommendations/", recommendations, name="recommendations"),
    path("practice/", practice.practice, name="practice"),
    path("practice/attempt/", practice.attempt, name="attempt"),
    path("practice/<slug:slug>/", practice.module_detail, name="module"),
    path("unsubscribe/<str:token>/", unsubscribe, name="unsubscribe"),
]
