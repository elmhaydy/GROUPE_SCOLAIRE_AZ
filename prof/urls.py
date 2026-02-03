from django.urls import path
from core import views_prof

app_name = "prof"

urlpatterns = [
    path("", views_prof.prof_dashboard, name="dashboard"),
    path("absences/", views_prof.prof_absences, name="absences"),
    path("evaluations/", views_prof.prof_evaluations, name="evaluations"),
    path("notes/<int:evaluation_id>/", views_prof.prof_notes_saisie, name="notes_saisie"),
    
    path("evaluations/ajouter/", views_prof.prof_evaluation_create, name="evaluation_create"),

    path("absences/prise/", views_prof.prof_absences_prise, name="absences_prise"),

    # Cahier de texte
    path("cahier/", views_prof.prof_cahier_list, name="cahier_list"),
    path("cahier/ajouter/", views_prof.prof_cahier_create, name="cahier_create"),
    path("cahier/<int:pk>/modifier/", views_prof.prof_cahier_update, name="cahier_update"),

    # Résumés PDF
    path("resumes/", views_prof.prof_resumes_list, name="resumes_list"),
    path("resumes/ajouter/", views_prof.prof_resume_create, name="resume_create"),

    path("emploi-du-temps/", views_prof.prof_edt, name="edt"),
    path("profil/", views_prof.prof_profil, name="profil"),


    path("ajax/matieres/", views_prof.prof_ajax_matieres, name="ajax_matieres"),
    path("ajax/periodes/", views_prof.prof_ajax_periodes, name="ajax_periodes"),
    path("ajax/groupes/", views_prof.prof_ajax_groupes, name="ajax_groupes"),
]
