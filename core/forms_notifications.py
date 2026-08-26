# core/forms_notifications.py
from django import forms
from .models import Degre, Niveau, Groupe, Eleve


CIBLE_CHOICES = [
    ("TOUS",    "Tous les parents"),
    ("DEGRE",   "Par degré"),
    ("NIVEAU",  "Par niveau"),
    ("GROUPE",  "Par groupe"),
    ("ELEVE",   "Élève ciblé"),
]

CANAL_CHOICES = [
    ("sms",      "SMS"),
    ("email",    "Email"),
    ("internal", "Notification interne"),
]


class NotifComposeForm(forms.Form):
    titre = forms.CharField(
        max_length=200,
        label="Objet / titre",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "Ex : Rappel de paiement"}),
    )
    message = forms.CharField(
        max_length=700,
        label="Message",
        widget=forms.Textarea(attrs={
            "class": "az-textarea",
            "rows": 5,
            "placeholder": "Rédigez votre message ici…",
        }),
    )
    canaux = forms.MultipleChoiceField(
        choices=CANAL_CHOICES,
        label="Canaux d'envoi",
        widget=forms.CheckboxSelectMultiple,
        initial=["sms", "internal"],
        required=True,
        error_messages={"required": "Choisissez au moins un canal d'envoi."},
    )
    cible_type = forms.ChoiceField(
        choices=CIBLE_CHOICES,
        label="Destinataires",
        widget=forms.Select(attrs={"class": "az-select", "id": "id_cible_type"}),
    )
    degre = forms.ModelChoiceField(
        queryset=Degre.objects.all(),
        required=False,
        label="Degré",
        widget=forms.Select(attrs={"class": "az-select", "id": "id_degre"}),
        empty_label="— Sélectionner —",
    )
    niveau = forms.ModelChoiceField(
        queryset=Niveau.objects.none(),
        required=False,
        label="Niveau",
        widget=forms.Select(attrs={"class": "az-select", "id": "id_niveau"}),
        empty_label="— Sélectionner —",
    )
    groupe = forms.ModelChoiceField(
        queryset=Groupe.objects.none(),
        required=False,
        label="Groupe",
        widget=forms.Select(attrs={"class": "az-select", "id": "id_groupe"}),
        empty_label="— Sélectionner —",
    )
    eleve = forms.ModelChoiceField(
        queryset=Eleve.objects.filter(is_active=True).select_related(),
        required=False,
        label="Élève",
        widget=forms.Select(attrs={"class": "az-select", "id": "id_eleve"}),
        empty_label="— Sélectionner —",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate dynamic selects if values are posted
        data = args[0] if args else None
        if data:
            if data.get("degre"):
                self.fields["niveau"].queryset = Niveau.objects.filter(
                    degre_id=data["degre"]
                )
            if data.get("niveau"):
                self.fields["groupe"].queryset = Groupe.objects.filter(
                    niveau_id=data["niveau"]
                )
        else:
            self.fields["niveau"].queryset = Niveau.objects.all()
            self.fields["groupe"].queryset = Groupe.objects.all()

    def clean(self):
        cleaned = super().clean()
        cible = cleaned.get("cible_type")
        if cible == "DEGRE" and not cleaned.get("degre"):
            self.add_error("degre", "Sélectionnez un degré.")
        if cible == "NIVEAU" and not cleaned.get("niveau"):
            self.add_error("niveau", "Sélectionnez un niveau.")
        if cible == "GROUPE" and not cleaned.get("groupe"):
            self.add_error("groupe", "Sélectionnez un groupe.")
        if cible == "ELEVE" and not cleaned.get("eleve"):
            self.add_error("eleve", "Sélectionnez un élève.")
        return cleaned
