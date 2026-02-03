# core/urls_eleve.py
from django.urls import path
from core import views_eleve

app_name = "eleve"

urlpatterns = [
    path("", views_eleve.eleve_dashboard, name="dashboard"),
    path("profil/", views_eleve.eleve_profil, name="profil"),
    path("paiements/", views_eleve.eleve_paiements, name="paiements"),
    path("absences/", views_eleve.eleve_absences, name="absences"),
    path("notes/", views_eleve.eleve_notes, name="notes"),
    path("avis/", views_eleve.eleve_avis, name="avis"),
    path("edt/", views_eleve.eleve_edt, name="edt"),
    path("bulletin/", views_eleve.bulletin, name="bulletin"),
    path("avis/<int:pk>/", views_eleve.eleve_avis_detail, name="avis_detail"),
    path("cahier/", views_eleve.eleve_cahier, name="cahier"),
    path("resumes/", views_eleve.eleve_resumes, name="resumes"),

]
