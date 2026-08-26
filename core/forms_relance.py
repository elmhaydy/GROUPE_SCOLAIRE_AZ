from django import forms
from core.models_relance import RelanceRule


class RelanceRuleForm(forms.ModelForm):
    class Meta:
        model = RelanceRule
        fields = [
            "type", "nom", "actif",
            "jours_apres", "niveau_relance", "seuil_occurrences",
            "intervalle_min_jours", "message_defaut", "ordre",
        ]
        widgets = {
            "type":            forms.Select(attrs={"class": "az-select"}),
            "nom":             forms.TextInput(attrs={"class": "az-input"}),
            "actif":           forms.CheckboxInput(attrs={"class": "az-checkbox"}),
            "jours_apres":     forms.NumberInput(attrs={"class": "az-input", "min": 0}),
            "niveau_relance":  forms.Select(attrs={"class": "az-select"}),
            "seuil_occurrences":    forms.NumberInput(attrs={"class": "az-input", "min": 1}),
            "intervalle_min_jours": forms.NumberInput(attrs={"class": "az-input", "min": 0}),
            "message_defaut":  forms.Textarea(attrs={
                "class": "az-input", "rows": 3,
                "placeholder": "Laisser vide pour utiliser le message par défaut du système."
            }),
            "ordre": forms.NumberInput(attrs={"class": "az-input", "min": 0}),
        }
        labels = {
            "type":                 "Type de relance",
            "nom":                  "Nom de la règle",
            "actif":                "Active",
            "jours_apres":          "Délai (jours)",
            "niveau_relance":       "Niveau",
            "seuil_occurrences":    "Seuil d'occurrences",
            "intervalle_min_jours": "Intervalle minimum (jours)",
            "message_defaut":       "Message SMS personnalisé",
            "ordre":                "Ordre d'affichage",
        }
        help_texts = {
            "jours_apres":     "Impayé : jours après l'échéance. Renouvellement : jours avant fin d'année.",
            "seuil_occurrences": "Absence / Retard uniquement : nombre minimum ce mois avant alerte.",
            "intervalle_min_jours": "Évite le spam : délai minimum entre 2 relances identiques au même élève.",
            "message_defaut": "Variables disponibles : {eleve}, {groupe}, {montant}, {date}, {mois}, {nb}, {annee}",
        }
