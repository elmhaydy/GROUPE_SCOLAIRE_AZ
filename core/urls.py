# core/urls.py
from django.urls import path, include

from . import views
from . import views_prof
from . import views_settings
from . import views_finance
from . import views_absences_profs as vabs
from . import views_finance as vf
from .views_profile import profile_view
from . import views_depenses as dep

app_name = "core"

urlpatterns = [

    # DASHBOARDS
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/admin/", views.dashboard_admin, name="dashboard_admin"),
    path("dashboard/superadmin/", views.dashboard_superadmin, name="dashboard_superadmin"),
    path("dashboard/staff/", views.dashboard_staff, name="dashboard_staff"),

    # A2 — Années scolaires
    path("annees/", views.annee_list, name="annee_list"),
    path("annees/ajouter/", views.annee_create, name="annee_create"),
    path("annees/<int:pk>/modifier/", views.annee_update, name="annee_update"),
    path("annees/<int:pk>/supprimer/", views.annee_delete, name="annee_delete"),
    path("annees/<int:pk>/activer/", views.annee_activer, name="annee_activer"),

    # B1 — Degrés
    path("degres/", views.degre_list, name="degre_list"),
    path("degres/ajouter/", views.degre_create, name="degre_create"),
    path("degres/<int:pk>/modifier/", views.degre_update, name="degre_update"),
    path("degres/<int:pk>/supprimer/", views.degre_delete, name="degre_delete"),

    # B2 — Niveaux
    path("niveaux/", views.niveau_list, name="niveau_list"),
    path("niveaux/ajouter/", views.niveau_create, name="niveau_create"),
    path("niveaux/<int:pk>/modifier/", views.niveau_update, name="niveau_update"),
    path("niveaux/<int:pk>/supprimer/", views.niveau_delete, name="niveau_delete"),
    path("niveaux/<int:niveau_id>/prix/", views.niveau_prix_edit, name="niveau_prix_edit"),

    # B3 — Groupes
    path("groupes/", views.groupe_list, name="groupe_list"),
    path("groupes/ajouter/", views.groupe_create, name="groupe_create"),
    path("groupes/<int:pk>/modifier/", views.groupe_update, name="groupe_update"),
    path("groupes/<int:pk>/supprimer/", views.groupe_delete, name="groupe_delete"),

    # C1 — Élèves
    path("eleves/", views.eleve_list, name="eleve_list"),
    path("eleves/ajouter/", views.eleve_create, name="eleve_create"),
    path("eleves/<int:pk>/", views.eleve_detail, name="eleve_detail"),
    path("eleves/<int:pk>/modifier/", views.eleve_update, name="eleve_update"),
    path("eleves/<int:pk>/supprimer/", views.eleve_delete, name="eleve_delete"),

    # C3 — Inscriptions
    path("inscriptions/", views.inscription_list, name="inscription_list"),
    path("inscriptions/ajouter/", views.inscription_create, name="inscription_create"),
    path("inscriptions/ajouter/eleve/<int:eleve_id>/", views.inscription_create_for_eleve, name="inscription_create_for_eleve"),
    path("inscriptions/<int:pk>/modifier/", views.inscription_update, name="inscription_update"),
    path("inscriptions/<int:pk>/supprimer/", views.inscription_delete, name="inscription_delete"),
    # C3 — Inscriptions (FULL FORM)
    path("inscriptions/ajouter/full/",views.inscription_full_create,name="inscription_full_create"),

    path("api/groupes/", views.groupes_par_annee, name="api_groupes_par_annee"),

    # D1 — Paiements
    path("paiements/", views.paiement_list, name="paiement_list"),
    path("paiements/ajouter/", views.paiement_create, name="paiement_create"),
    path("paiements/ajouter/inscription/<int:inscription_id>/", views.paiement_create_for_inscription, name="paiement_create_for_inscription"),
    path("paiements/recu/<int:pk>/", views.paiement_recu, name="paiement_recu"),

    path("impayes/", views.impayes_list, name="impayes_list"),

    # G — Recouvrement
    path("recouvrements/", views.recouvrement_list, name="recouvrement_list"),
    path("recouvrements/ouvrir/inscription/<int:inscription_id>/", views.recouvrement_create_for_inscription, name="recouvrement_create_for_inscription"),
    path("recouvrements/<int:pk>/", views.recouvrement_detail, name="recouvrement_detail"),
    path("recouvrements/<int:pk>/cloturer/", views.recouvrement_cloturer, name="recouvrement_cloturer"),
    path("recouvrements/<int:dossier_id>/relance/", views.relance_create, name="relance_create"),

    # E1 — Enseignants
    path("enseignants/", views.enseignant_list, name="enseignant_list"),
    path("enseignants/ajouter/", views.enseignant_create, name="enseignant_create"),
    path("enseignants/<int:pk>/", views.enseignant_detail, name="enseignant_detail"),
    path("enseignants/<int:pk>/modifier/", views.enseignant_update, name="enseignant_update"),
    path("enseignants/<int:pk>/supprimer/", views.enseignant_delete, name="enseignant_delete"),

    # E1.5 — Affectations Enseignant <-> Groupes
    path("enseignants/<int:pk>/affectations/", views.enseignant_affectations, name="enseignant_affectations"),
    path("enseignants/<int:pk>/affectations/ajouter/", views.enseignant_affectation_add, name="enseignant_affectation_add"),
    path("enseignants/<int:pk>/affectations/<int:aff_id>/supprimer/", views.enseignant_affectation_delete, name="enseignant_affectation_delete"),

    # E2 — Séances (EDT)
    path("seances/", views.seance_list, name="seance_list"),
    path("seances/ajouter/", views.seance_create, name="seance_create"),
    path("seances/<int:pk>/modifier/", views.seance_update, name="seance_update"),
    path("seances/<int:pk>/supprimer/", views.seance_delete, name="seance_delete"),


    path("edt/", views.edt_week, name="edt_week"),
    
    # F1 — Absences
    path("absences/", views.absence_list, name="absence_list"),
    path("absences/ajouter/", views.absence_create, name="absence_create"),
    path("absences/<int:pk>/modifier/", views.absence_update, name="absence_update"),
    path("absences/<int:pk>/supprimer/", views.absence_delete, name="absence_delete"),

    path("api/seances/", views.api_seances_par_groupe_date, name="api_seances_par_groupe_date"),
    path("absences/jour/", views.absences_jour, name="absences_jour"),

    # G1 — Parents
    path("parents/", views.parent_list, name="parent_list"),
    path("parents/ajouter/", views.parent_create, name="parent_create"),
    path("parents/<int:pk>/", views.parent_detail, name="parent_detail"),
    path("parents/<int:pk>/modifier/", views.parent_update, name="parent_update"),
    path("parents/<int:pk>/supprimer/", views.parent_delete, name="parent_delete"),

    # K2 — PDF
    path("paiements/<int:pk>/pdf/", views.paiement_recu_pdf_auto, name="paiement_recu_pdf_auto"),
    path("absences/jour/pdf/", views.absences_jour_pdf_view, name="absences_jour_pdf"),
    path("impayes/pdf/", views.impayes_pdf_view, name="impayes_pdf"),
    path("eleves/pdf/", views.eleves_pdf_view, name="eleves_pdf"),

    # M1 — Excel Élèves
    path("eleves/excel/export/", views.eleves_excel_export, name="eleves_excel_export"),
    path("eleves/excel/import/", views.eleves_excel_import, name="eleves_excel_import"),

    # M2 — Excel Parents + liens
    path("parents/excel/export/", views.parents_excel_export, name="parents_excel_export"),
    path("parents/excel/import/", views.parents_excel_import, name="parents_excel_import"),

    # N1 — Excel Inscriptions
    path("inscriptions/excel/export/", views.inscriptions_excel_export, name="inscriptions_excel_export"),
    path("inscriptions/excel/import/", views.inscriptions_excel_import, name="inscriptions_excel_import"),

    # N2 — Excel Paiements
    path("paiements/excel/export/", views.paiements_excel_export, name="paiements_excel_export"),
    path("paiements/excel/import/", views.paiements_excel_import, name="paiements_excel_import"),

    # O1 — Notes
    # Matières (Pédagogie)
    path("pedagogie/matieres/", views.matiere_list, name="matiere_list"),
    path("pedagogie/matieres/ajouter/", views.matiere_create, name="matiere_create"),
    path("pedagogie/matieres/<int:pk>/modifier/", views.matiere_update, name="matiere_update"),
    path("pedagogie/matieres/<int:pk>/supprimer/", views.matiere_delete, name="matiere_delete"),

    path("notes/evaluations/", views.evaluation_list, name="evaluation_list"),
    path("notes/evaluations/ajouter/", views.evaluation_create, name="evaluation_create"),


    # O1.5 — Bulletin
    path("bulletin/eleve/<int:eleve_id>/", views.bulletin_view, name="bulletin_view"),
    path("bulletin/eleve/<int:eleve_id>/pdf/", views.bulletin_pdf_view, name="bulletin_pdf"),

    path("prof/", views_prof.prof_dashboard, name="prof_dashboard"),


    # U1 — Users
    path("users/", views.users_list, name="users_list"),
    path("users/<int:user_id>/", views.users_detail, name="users_detail"),
    path("users/ajouter/", views.users_create, name="users_create"),
    path("users/<int:user_id>/modifier/", views.users_update, name="users_update"),
    path("users/<int:user_id>/password/", views.users_password, name="users_password"),
    path("users/<int:user_id>/supprimer/", views.users_delete, name="users_delete"),

    path("users/export/", views.users_export_csv, name="users_export_csv"),
    path("users/reset-export/", views.users_reset_passwords_export_csv, name="users_reset_passwords_export_csv"),

    # Absences - mode pratique
    path("absences/pratique/", views.absences_pratique, name="absences_pratique"),
    path("absences/feuille/", views.absences_feuille, name="absences_feuille"),

    # API - feuille de présence
    path("api/feuille-presence/", views.api_feuille_presence, name="api_feuille_presence"),
    path("api/feuille-presence/save/", views.api_feuille_presence_save, name="api_feuille_presence_save"),

    # core/urls.py
    path("api/matieres/", views.api_matieres_par_groupe, name="api_matieres_par_groupe"),
   
    # Notes / saisie
    path("notes/saisie/", views.notes_saisie_home, name="notes_saisie_home"),
    path("notes/saisie/<int:evaluation_id>/", views.notes_saisie, name="notes_saisie"),



    # ✅ AJAX (filtres dépendants)
    path("ajax/niveaux/", views.ajax_niveaux, name="ajax_niveaux"),
    path("ajax/groupes/", views.ajax_groupes, name="ajax_groupes"),
    path("ajax/periodes/", views.ajax_periodes, name="ajax_periodes"),
    path("ajax/enseignants/", views.ajax_enseignants, name="ajax_enseignants"),
    path("ajax/matieres/", views.ajax_matieres, name="ajax_matieres"),
    path("ajax/eleves-par-groupe/", views.ajax_eleves_par_groupe, name="ajax_eleves_par_groupe"),

    path("api/enseignants/", views.api_enseignants, name="api_enseignants_simple"),

    path("api/enseignants-all/", views.api_enseignants, name="api_enseignants"),
    path("api/periodes-par-groupe/", views.api_periodes_par_groupe, name="api_periodes_par_groupe"),

    # =========================
    # I — Communication
    # =========================
    path("communication/avis/", views.avis_list, name="avis_list"),
    path("communication/avis/new/", views.avis_create, name="avis_create"),
    path("communication/avis/<int:pk>/", views.avis_detail, name="avis_detail"),
    path("communication/avis/<int:pk>/supprimer/", views.avis_delete, name="avis_delete"),

    path("communication/sms/", views.sms_send, name="sms_send"),
    path("communication/sms/historique/", views.sms_history, name="sms_history"),


    # Années scolaires — MODALE delete
    path("users/<int:pk>/modal/", views.users_detail_modal, name="users_detail_modal"),



    # Paramètres
    path("settings/", views_settings.settings_home, name="settings_home"),

    # Rôles & Permissions
    path("settings/roles/", views_settings.role_list, name="role_list"),
    path("settings/roles/add/", views_settings.role_create, name="role_create"),
    path("settings/roles/<int:pk>/edit/", views_settings.role_update, name="role_update"),
    path("settings/roles/<int:pk>/delete/", views_settings.role_delete, name="role_delete"),


    path("profs/absences/", vabs.absence_prof_list, name="absence_prof_list"),
    path("profs/absences/ajouter/", vabs.absence_prof_create, name="absence_prof_create"),
    path("profs/absences/<int:pk>/supprimer/", vabs.absence_prof_delete, name="absence_prof_delete"),


    path("eleves/<int:pk>/reinscrire/", views.eleve_reinscrire, name="eleve_reinscrire"),


    path("impayes/mensuels/", views.impayes_mensuels_list, name="impayes_mensuels_list"),

    path("finance/inscription/<int:inscription_id>/", vf.inscription_finance_detail, name="inscription_finance_detail"),


    path("finance/impayes-mensuels/excel/", views.impayes_mensuels_excel_export, name="impayes_mensuels_excel_export"),
    path("paiements/recu/batch/<str:batch_token>/", views.paiement_recu_batch, name="paiement_recu_batch"),
    path("paiements/recu/batch/<str:batch_token>/pdf/", views.paiement_recu_batch_pdf, name="paiement_recu_batch_pdf"),



    path("admin/profile/", profile_view, name="profile"),
        
    path("api/fratrie/", views_finance.api_fratrie, name="api_fratrie"),
    path("finance/paiements/eleve/<int:eleve_id>/", views_finance.paiements_eleve, name="paiements_eleve"),


    path("finance/transactions/wizard/", views_finance.transaction_wizard, name="transaction_wizard"),
    path("finance/transactions/create/", views_finance.transaction_create, name="transaction_create"),
    path("finance/transactions/<int:tx_id>/pdf/", views_finance.transaction_pdf, name="transaction_pdf"),
    path("transactions/<int:tx_id>/success/", views_finance.transaction_success, name="transaction_success"),

    path("ajax/transport-echeances/", views.ajax_transport_echeances, name="ajax_transport_echeances"),


    # ✅ tu gardes tes endpoints AJAX existants (groupes, echeances, fratrie...)
    path("ajax/echeances/", views_finance.ajax_echeances, name="ajax_echeances"),
    path("ajax/inscription-by-eleve/", views_finance.ajax_inscription_by_eleve, name="ajax_inscription_by_eleve"),
    path("api/groupes-par-niveau/", views_finance.api_groupes_par_niveau, name="api_groupes_par_niveau"),
    path("api/fratrie/", views_finance.api_fratrie, name="api_fratrie"),

    path("api/eleves-par-groupe/", views_finance.api_eleves_par_groupe, name="api_eleves_par_groupe"),

    path("transport/<int:eleve_id>/toggle/", views.transport_toggle, name="transport_toggle"),
    path("transport/<int:eleve_id>/tarif/", views.transport_set_tarif, name="transport_set_tarif"),
    path("ajax/transport-status/", views.ajax_transport_status, name="ajax_transport_status"),

    path("paiements/<int:tx_id>/rembourser/", views.transaction_remboursement_create, name="paiement_remboursement_create"),




    # ======================
    # Dépenses (Niveau 1)
    # ======================
    path("finance/depenses/", dep.depense_list, name="depense_list"),
    path("finance/depenses/create/", dep.depense_create, name="depense_create"),
    path("finance/depenses/<int:pk>/edit/", dep.depense_edit, name="depense_edit"),
    path("finance/depenses/<int:pk>/delete/", dep.depense_delete, name="depense_delete"),

    path("finance/depenses/categories/", dep.categorie_list, name="depense_categorie_list"),
    path("finance/depenses/categories/create/", dep.categorie_create, name="depense_categorie_create"),
    path("finance/depenses/categories/<int:pk>/edit/", dep.categorie_edit, name="depense_categorie_edit"),
    path("finance/depenses/categories/<int:pk>/delete/",dep.categorie_delete,name="depense_categorie_delete"),


    path("edt-prof/", views.edt_prof_week, name="edt_prof_week"),
    path("enseignants/<int:pk>/edt/", views.edt_prof_week, name="enseignant_edt"),

]
 
 
 