from django.urls import path

from apps.support import views


urlpatterns = [
    path("platform/support-incidents/", views.SupportIncidentView.as_view()),
    path("platform/support-cases/<int:pk>/incidents/", views.CaseIncidentsView.as_view()),
    path("platform/support-cases/staff/", views.SupportStaffView.as_view()),
    path("platform/support-cases/<int:pk>/internal-notes/", views.CaseNotesView.as_view()),
    path("platform/support-cases/<int:pk>/assign/", views.CaseAssignView.as_view()),
    path("platform/support-cases/<int:pk>/transition/", views.CaseTransitionView.as_view()),
]

for prefix, platform in [("platform/support-cases", True), ("support/cases", False)]:
    urlpatterns += [
        path(f"{prefix}/", views.CaseListView.as_view(platform=platform)),
        path(f"{prefix}/<int:pk>/", views.CaseDetailView.as_view(platform=platform)),
        path(f"{prefix}/<int:pk>/messages/", views.CaseMessagesView.as_view(platform=platform)),
        path(f"{prefix}/<int:pk>/events/", views.CaseEventsView.as_view(platform=platform)),
        path(f"{prefix}/<int:pk>/reopen/", views.CaseReopenView.as_view(platform=platform)),
        path(f"{prefix}/<int:pk>/read/", views.CaseReadView.as_view(platform=platform)),
    ]
