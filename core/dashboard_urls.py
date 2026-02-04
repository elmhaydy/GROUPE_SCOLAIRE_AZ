# core/dashboard_urls.py (recommandé)
from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("admin/", views.dashboard_admin, name="dashboard_admin"),
    path("staff/", views.dashboard_staff, name="dashboard_staff"),
    path("superadmin/", views.dashboard_superadmin, name="dashboard_superadmin"),
]
