from decimal import Decimal
from django import forms
from core.models import FichePaie, Enseignant, AnneeScolaire
from django.contrib.auth import get_user_model

User = get_user_model()


class FichePaieForm(forms.ModelForm):
    class Meta:
        model = FichePaie
        fields = [
            "personnel_type",
            "enseignant",
            "user",
            "annee",
            "mois_index",
            "salaire_base",
            "primes",
            "deductions",
            "statut",
            "date_paiement",
            "mode_paiement",
            "reference_virement",
            "remarques",
        ]
        widgets = {
            "personnel_type": forms.Select(attrs={"class": "az-select", "id": "id_personnel_type"}),
            "enseignant": forms.Select(attrs={"class": "az-select", "id": "id_enseignant"}),
            "user": forms.Select(attrs={"class": "az-select", "id": "id_user"}),
            "annee": forms.Select(attrs={"class": "az-select"}),
            "mois_index": forms.NumberInput(attrs={"class": "az-input", "min": 1, "max": 12}),
            "salaire_base": forms.NumberInput(attrs={"class": "az-input", "step": "0.01"}),
            "primes": forms.NumberInput(attrs={"class": "az-input", "step": "0.01"}),
            "deductions": forms.NumberInput(attrs={"class": "az-input", "step": "0.01"}),
            "statut": forms.Select(attrs={"class": "az-select"}),
            "date_paiement": forms.DateInput(attrs={"class": "az-input", "type": "date"}),
            "mode_paiement": forms.Select(attrs={"class": "az-select"}),
            "reference_virement": forms.TextInput(attrs={"class": "az-input", "placeholder": "Ex: VIR-2026-0042"}),
            "remarques": forms.Textarea(attrs={"class": "az-textarea", "rows": 3, "placeholder": "Notes ou observations sur la fiche de paie..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["enseignant"].queryset = Enseignant.objects.filter(is_active=True).order_by("nom", "prenom")
        self.fields["user"].queryset = (
            User.objects.filter(is_active=True)
            .exclude(groups__name="ELEVE")
            .exclude(eleve_profile__isnull=False)
            .exclude(enseignant_profile__isnull=False)
            .order_by("first_name", "last_name", "username")
        )
        self.fields["annee"].queryset = AnneeScolaire.objects.order_by("-is_active", "-date_debut")
