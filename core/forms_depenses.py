# core/forms_depenses.py
from django import forms
from django.utils import timezone
from core.models import Depense, CategorieDepense

class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ["annee", "date_depense", "montant", "categorie", "libelle", "description", "justificatif"]
        widgets = {
            "date_depense": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        annee_default = kwargs.pop("annee_default", None)
        super().__init__(*args, **kwargs)

        # catégories actives uniquement
        self.fields["categorie"].queryset = CategorieDepense.objects.filter(is_active=True).order_by("ordre", "nom")

        # defaults
        if not self.instance.pk:
            if annee_default and not self.initial.get("annee"):
                self.initial["annee"] = annee_default
            if not self.initial.get("date_depense"):
                self.initial["date_depense"] = timezone.now().date()


class CategorieDepenseForm(forms.ModelForm):
    class Meta:
        model = CategorieDepense
        fields = ["nom", "is_active", "ordre"]
