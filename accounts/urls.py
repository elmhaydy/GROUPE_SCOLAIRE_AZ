# accounts/urls.py
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("password/change/", views.password_change, name="password_change"),
    path("eleve/password/change/", views.eleve_password_change, name="eleve_password_change"),

    path("password/reset/", views.password_reset_request, name="password_reset_request"),
    path("password/reset/otp/", views.password_reset_otp, name="password_reset_otp"),
    path("password/reset/resend/", views.password_reset_resend_otp, name="password_reset_resend_otp"),
    path("password/reset/confirm/", views.password_reset_confirm_otp, name="password_reset_confirm_otp"),
    path("password/reset/sent/", views.password_reset_sent, name="password_reset_sent"),
    path("password/reset/<uuid:token>/", views.password_reset_confirm, name="password_reset_confirm"),
]
