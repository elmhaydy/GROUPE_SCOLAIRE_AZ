# core/admin.py
from django.contrib import admin
from django.utils import timezone

from .models import (
    # Scolarité / Pédagogie
    AnneeScolaire,
    Matiere, Periode, Evaluation, Note,

    # Affectations
    ProfGroupe,
    EnseignantGroupe,

    # Personnes
    Parent, ParentEleve,
    Eleve,
    Enseignant,

    # Structure
    Groupe, Niveau,

    # Finance
    FraisNiveau,
)


# =========================
# Année Scolaire
# =========================
@admin.action(description="✅ Activer l'année sélectionnée (désactive les autres)")
def activer_annee(modeladmin, request, queryset):
    annee = queryset.order_by("-date_debut").first()
    if not annee:
        return
    AnneeScolaire.objects.update(is_active=False)
    annee.is_active = True
    annee.save()


@admin.register(AnneeScolaire)
class AnneeScolaireAdmin(admin.ModelAdmin):
    list_display = ("nom", "date_debut", "date_fin", "is_active")
    list_filter = ("is_active",)
    search_fields = ("nom",)
    actions = [activer_annee]

    def get_changeform_initial_data(self, request):
        today = timezone.now().date()
        return {"date_debut": today}


# =========================
# Scolarité (matières/notes)
# =========================
@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    search_fields = ("nom",)
    list_display = ("nom", "is_active")
    list_filter = ("is_active",)


@admin.register(Periode)
class PeriodeAdmin(admin.ModelAdmin):
    search_fields = ("nom", "annee__nom")
    list_display = ("annee", "nom")
    list_filter = ("annee",)


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    search_fields = ("titre", "groupe__nom", "matiere__nom")
    list_display = ("date", "titre", "matiere", "enseignant", "periode", "groupe")
    list_filter = ("periode__annee", "periode", "groupe__niveau__degre", "groupe__niveau", "groupe", "matiere")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("evaluation", "eleve", "valeur")
    list_filter = ("evaluation__periode__annee", "evaluation__periode", "evaluation__groupe")
    search_fields = ("eleve__nom", "eleve__prenom", "evaluation__titre")



# =========================
# Parent <-> Élève
# =========================
class ParentEleveInline(admin.TabularInline):
    model = ParentEleve
    extra = 0
    autocomplete_fields = ("eleve",)
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by")


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = (
        "nom", "prenom", "telephone", "email", "user", "is_active",
        "created_at", "created_by", "updated_at", "updated_by"
    )
    list_filter = ("is_active",)
    search_fields = ("nom", "prenom", "telephone", "email", "user__username")
    autocomplete_fields = ("user",)
    inlines = [ParentEleveInline]
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by")


@admin.register(ParentEleve)
class ParentEleveAdmin(admin.ModelAdmin):
    list_display = ("parent", "eleve", "lien", "created_at", "created_by", "updated_at", "updated_by")
    list_filter = ("lien",)
    search_fields = ("parent__nom", "parent__prenom", "eleve__nom", "eleve__prenom", "eleve__matricule")
    autocomplete_fields = ("parent", "eleve")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by")


# =========================
# Élèves
# =========================
@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ("matricule", "nom", "prenom", "telephone", "is_active", "created_at", "created_by", "updated_at", "updated_by")
    search_fields = ("matricule", "nom", "prenom", "telephone")
    list_filter = ("is_active",)
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by")


# =========================
# Finance
# =========================
from django.contrib import admin
from .models import FraisNiveau

@admin.register(FraisNiveau)
class FraisNiveauAdmin(admin.ModelAdmin):
    list_display = ("annee", "niveau", "frais_scolarite_mensuel")
    list_filter = ("annee", "niveau__degre")
    search_fields = ("niveau__nom", "niveau__degre__nom", "annee__nom")


# =========================
# Structure (pour autocomplete_fields)
# =========================
@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    search_fields = ("matricule", "nom", "prenom")
    list_display = ("matricule", "nom", "prenom", "is_active")
    list_filter = ("is_active",)


@admin.register(Groupe)
class GroupeAdmin(admin.ModelAdmin):
    search_fields = ("nom", "niveau__nom", "niveau__degre__nom", "annee__nom")
    list_display = ("annee", "niveau", "nom")
    list_filter = ("annee", "niveau__degre", "niveau")


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    search_fields = ("nom", "degre__nom")
    list_display = ("degre", "nom")
    list_filter = ("degre",)



# =========================
# Enseignant <-> Groupe (Affectations)
# =========================
@admin.register(EnseignantGroupe)
class EnseignantGroupeAdmin(admin.ModelAdmin):
    @admin.display(description="Matière")
    def matiere_label(self, obj):
        # FK prioritaire
        if getattr(obj, "matiere_fk_id", None):
            return obj.matiere_fk.nom
        # fallback si le champ texte existe encore
        return (getattr(obj, "matiere", "") or "").strip() or "—"

    list_display = ("annee", "groupe", "enseignant", "matiere_label", "created_at")

    list_filter = (
        "annee",
        "groupe__niveau__degre",
        "groupe__niveau",
        "groupe",
        "enseignant",
        "matiere_fk",
    )

    search_fields = (
        "enseignant__nom", "enseignant__prenom", "enseignant__matricule",
        "groupe__nom", "groupe__niveau__nom", "groupe__niveau__degre__nom",
        "annee__nom",
        "matiere_fk__nom",
        # fallback texte si tu gardes encore le champ matiere pendant la transition
        "matiere",
    )

    autocomplete_fields = ("annee", "groupe", "enseignant", "matiere_fk")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by")

    def save_model(self, request, obj, form, change):
        # ✅ auto-fill annee depuis groupe si vide
        if obj.groupe_id and not obj.annee_id:
            obj.annee_id = obj.groupe.annee_id
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # ✅ si on édite une affectation existante: filtre les groupes par année
        if obj and obj.annee_id:
            form.base_fields["groupe"].queryset = Groupe.objects.filter(annee_id=obj.annee_id)
        else:
            form.base_fields["groupe"].queryset = Groupe.objects.all()

        return form

