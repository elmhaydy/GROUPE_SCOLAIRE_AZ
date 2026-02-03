# core/forms_communication.py
from django import forms
from .models import Avis

class AvisForm(forms.ModelForm):
    class Meta:
        model = Avis
        fields = [
            "titre", "contenu",
            "cible_type",
            "degre", "niveau", "groupe", "eleve",
            "visible_parent",
        ]
        widgets = {
            "contenu": forms.Textarea(attrs={"rows": 6}),
        }

    def clean(self):
        cleaned = super().clean()
        t = cleaned.get("cible_type")

        degre = cleaned.get("degre")
        niveau = cleaned.get("niveau")
        groupe = cleaned.get("groupe")
        eleve = cleaned.get("eleve")

        # reset logique: on accepte mais on valide
        if t == "DEGRE" and not degre:
            self.add_error("degre", "Degré obligatoire.")
        if t == "NIVEAU" and not niveau:
            self.add_error("niveau", "Niveau obligatoire.")
        if t == "GROUPE" and not groupe:
            self.add_error("groupe", "Groupe obligatoire.")
        if t == "ELEVE" and not eleve:
            self.add_error("eleve", "Élève obligatoire.")

        if t == "TOUS":
            # on ignore les FK si remplies par erreur
            cleaned["degre"] = None
            cleaned["niveau"] = None
            cleaned["groupe"] = None
            cleaned["eleve"] = None

        return cleaned


class SmsSendForm(forms.Form):
    """
    Form pour envoyer SMS ciblé
    """
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}), max_length=700)

    cible_type = forms.ChoiceField(choices=Avis.CIBLE_CHOICES, initial="TOUS")

    degre = forms.IntegerField(required=False)   # Degre.id
    niveau = forms.IntegerField(required=False)  # Niveau.id
    groupe = forms.IntegerField(required=False)  # Groupe.id
    eleve = forms.IntegerField(required=False)   # Eleve.id
