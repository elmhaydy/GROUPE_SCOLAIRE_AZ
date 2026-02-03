# core/forms_prof.py
from django import forms

from core.models import (
    CahierTexte,
    CoursResumePDF,
    Evaluation,
    Groupe,
    Matiere,
    Periode,
    EnseignantGroupe,
)

# =========================================================
# Utils
# =========================================================
def _clean_gid(raw):
    """
    Nettoie un id provenant d'un select/GET/POST.
    Évite le bug: id="None" ou "null" -> ValueError.
    Retourne un string digit ou "".
    """
    s = str(raw or "").strip()
    if not s or s.lower() in ("none", "null", "undefined"):
        return ""
    if not s.isdigit():
        return ""
    return s


def _matieres_for_user_groupe(user, groupe: Groupe):
    """
    Matières autorisées STRICTEMENT par affectation (EnseignantGroupe.matiere_fk)
    pour CE groupe et l'année du groupe.
    """
    ens = getattr(user, "enseignant_profile", None)
    if not ens or not groupe:
        return Matiere.objects.none()

    matiere_ids = (
        EnseignantGroupe.objects
        .filter(
            annee=groupe.annee,
            groupe=groupe,
            enseignant=ens,
            matiere_fk__isnull=False,
        )
        .values_list("matiere_fk_id", flat=True)
        .distinct()
    )

    return (
        Matiere.objects
        .filter(is_active=True, id__in=matiere_ids)
        .order_by("nom")
    )


# =========================================================
# ProfEvaluationForm (PROF)
# =========================================================
class ProfEvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ["titre", "type", "groupe", "matiere", "periode", "date", "note_max", "coefficient"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        allowed_groupes = kwargs.pop("allowed_groupes", None)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._user = user

        # styles
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "az-field")

        self.fields["titre"].widget.attrs.update({"placeholder": "Ex: Contrôle 1"})
        self.fields["note_max"].widget.attrs.update({"min": "1", "max": "100"})
        self.fields["coefficient"].widget.attrs.update({"step": "0.25", "min": "0.25"})

        # ✅ Groupes autorisés
        if allowed_groupes is not None:
            if not hasattr(allowed_groupes, "model"):
                ids = [g.id for g in allowed_groupes if g and getattr(g, "id", None)]
                allowed_groupes = Groupe.objects.filter(id__in=ids)

            self.fields["groupe"].queryset = (
                allowed_groupes
                .select_related("annee", "niveau", "niveau__degre")
                .order_by("niveau__degre__ordre", "niveau__ordre", "nom")
            )

        # par défaut
        self.fields["periode"].queryset = Periode.objects.none()
        self.fields["matiere"].queryset = Matiere.objects.none()

        gid = _clean_gid(self.data.get("groupe") or self.data.get("groupe_id") or getattr(self.instance, "groupe_id", ""))
        groupe = None

        if gid:
            groupe = self.fields["groupe"].queryset.filter(id=int(gid)).first()
        else:
            groupe = getattr(self.instance, "groupe", None)

        if groupe:
            self.fields["periode"].queryset = Periode.objects.filter(annee=groupe.annee).order_by("ordre")
            if user:
                self.fields["matiere"].queryset = _matieres_for_user_groupe(user, groupe)

    def clean(self):
        cleaned = super().clean()
        groupe = cleaned.get("groupe")
        periode = cleaned.get("periode")
        matiere = cleaned.get("matiere")

        if groupe and periode and groupe.annee_id != periode.annee_id:
            self.add_error("periode", "Cette période n’appartient pas à l’année du groupe.")

        # ✅ sécurité matière
        if groupe and matiere and self._user:
            if not _matieres_for_user_groupe(self._user, groupe).filter(id=matiere.id).exists():
                self.add_error("matiere", "Matière non autorisée pour ce groupe.")

        return cleaned


# =========================================================
# ProfCahierTexteForm (PROF)
# =========================================================
class ProfCahierTexteForm(forms.ModelForm):
    class Meta:
        model = CahierTexte
        fields = ["titre", "date", "groupe", "matiere", "contenu", "devoir", "piece_jointe", "is_published"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "contenu": forms.Textarea(attrs={"rows": 6}),
            "devoir": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        allowed_groupes = kwargs.pop("allowed_groupes", None)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._user = user

        if allowed_groupes is not None:
            if not hasattr(allowed_groupes, "model"):
                ids = [g.id for g in allowed_groupes if g and getattr(g, "id", None)]
                allowed_groupes = Groupe.objects.filter(id__in=ids)

            self.fields["groupe"].queryset = (
                allowed_groupes
                .select_related("annee", "niveau", "niveau__degre")
                .order_by("niveau__degre__ordre", "niveau__ordre", "nom")
            )

        self.fields["matiere"].queryset = Matiere.objects.none()

        gid = _clean_gid(self.data.get("groupe") or getattr(self.instance, "groupe_id", ""))
        groupe = None

        if gid:
            groupe = self.fields["groupe"].queryset.filter(id=int(gid)).first()
        else:
            groupe = getattr(self.instance, "groupe", None)

        if groupe and user:
            self.fields["matiere"].queryset = _matieres_for_user_groupe(user, groupe)

    def clean(self):
        cleaned = super().clean()
        groupe = cleaned.get("groupe")
        matiere = cleaned.get("matiere")

        if groupe and matiere and self._user:
            if not _matieres_for_user_groupe(self._user, groupe).filter(id=matiere.id).exists():
                self.add_error("matiere", "Matière non autorisée pour ce groupe.")

        return cleaned


# =========================================================
# ProfResumePDFForm (PROF)
# =========================================================
class ProfResumePDFForm(forms.ModelForm):
    class Meta:
        model = CoursResumePDF
        fields = ["titre", "matiere", "groupe", "date", "fichier", "is_published"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        allowed_groupes = kwargs.pop("allowed_groupes", None)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._user = user

        if allowed_groupes is not None:
            if not hasattr(allowed_groupes, "model"):
                ids = [g.id for g in allowed_groupes if g and getattr(g, "id", None)]
                allowed_groupes = Groupe.objects.filter(id__in=ids)

            self.fields["groupe"].queryset = (
                allowed_groupes
                .select_related("annee", "niveau", "niveau__degre")
                .order_by("niveau__degre__ordre", "niveau__ordre", "nom")
            )

        self.fields["matiere"].queryset = Matiere.objects.none()

        gid = _clean_gid(self.data.get("groupe") or getattr(self.instance, "groupe_id", ""))
        groupe = None

        if gid:
            groupe = self.fields["groupe"].queryset.filter(id=int(gid)).first()
        else:
            groupe = getattr(self.instance, "groupe", None)

        if groupe and user:
            self.fields["matiere"].queryset = _matieres_for_user_groupe(user, groupe)

    def clean(self):
        cleaned = super().clean()
        groupe = cleaned.get("groupe")
        matiere = cleaned.get("matiere")

        if groupe and matiere and self._user:
            if not _matieres_for_user_groupe(self._user, groupe).filter(id=matiere.id).exists():
                self.add_error("matiere", "Matière non autorisée pour ce groupe.")

        return cleaned

    def clean_fichier(self):
        f = self.cleaned_data.get("fichier")
        if not f:
            return f
        name = (f.name or "").lower()
        if not name.endswith(".pdf"):
            raise forms.ValidationError("Le fichier doit être un PDF.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("PDF trop grand (max 10MB).")
        return f
