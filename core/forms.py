# core/forms.py
from django import forms
from .models import AnneeScolaire, ProfGroupe
from .models import Degre
from .models import EnseignantGroupe
from .models import Eleve
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.utils_users import get_or_create_user_with_group
from core.models import TempPassword, ParentEleve, Enseignant
from .models import Seance, AnneeScolaire, Groupe, Enseignant, EnseignantGroupe
from .models import Absence
import json
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from .models import Niveau

from core.models import Paiement, Inscription, EcheanceMensuelle


class AnneeScolaireForm(forms.ModelForm):
    class Meta:
        model = AnneeScolaire
        fields = ["nom", "date_debut", "date_fin", "is_active"]
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "ex: 2025/2026"}),
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
        }


class DegreForm(forms.ModelForm):
    class Meta:
        model = Degre
        fields = ["nom", "ordre"]
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "ex: Maternelle"}),
            "ordre": forms.NumberInput(attrs={"min": 1}),
        }


class NiveauForm(forms.ModelForm):
    class Meta:
        model = Niveau
        fields = ["degre", "nom", "ordre"]
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "ex: CP / 1AC / Petite Section"}),
            "ordre": forms.NumberInput(attrs={"min": 1}),
        }


class GroupeForm(forms.ModelForm):
    class Meta:
        model = Groupe
        fields = ["annee", "niveau", "nom", "capacite"]
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "ex: CP-A / 1AC-B"}),
            "capacite": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Par défaut : propose l'année active en premier
        active = AnneeScolaire.objects.filter(is_active=True).first()
        if active and not self.initial.get("annee"):
            self.initial["annee"] = active



class EleveForm(forms.ModelForm):
    class Meta:
        model = Eleve
        fields = [
            "photo",  # ✅ NEW
            "nom", "prenom", "sexe",
            "date_naissance", "lieu_naissance",
            "adresse", "telephone",
            "is_active",
        ]
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}),
            "adresse": forms.TextInput(attrs={"placeholder": "Adresse"}),
            "telephone": forms.TextInput(attrs={"placeholder": "+212 ..."}),

            # ✅ OPTIONNEL: pour mieux indiquer le champ photo
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }


class InscriptionForm(forms.ModelForm):
    class Meta:
        model = Inscription

        # ✅ PAS de "niveau" (car le modèle Inscription ne l’a pas)
        fields = ["eleve", "annee", "groupe", "statut", "dernier_etablissement"]

        widgets = {
            "annee": forms.Select(attrs={"id": "id_annee"}),
            "groupe": forms.Select(attrs={"id": "id_groupe"}),
            "statut": forms.Select(),
            "eleve": forms.Select(),
            "dernier_etablissement": forms.TextInput(attrs={"class": "az-input", "placeholder": "Ex : École X"}),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Année active par défaut
        active = AnneeScolaire.objects.filter(is_active=True).first()
        if active and not self.initial.get("annee"):
            self.initial["annee"] = active

        # ✅ Filtrer les groupes selon l'année choisie (ou année active)
        annee_id = None
        
        if self.data.get("annee"):
            annee_id = self.data.get("annee")
        elif self.initial.get("annee"):
            a = self.initial.get("annee")
            annee_id = a.id if hasattr(a, "id") else a

        # c) update : on prend l'année de l'instance
        elif getattr(self.instance, "annee_id", None):
            annee_id = self.instance.annee_id

        if annee_id:
            self.fields["groupe"].queryset = (
                Groupe.objects.filter(annee_id=annee_id)
                .select_related("niveau", "annee")
                .order_by("niveau__degre__nom", "niveau__nom", "nom")
            )
        else:
            self.fields["groupe"].queryset = Groupe.objects.none()

    def clean(self):
        cleaned = super().clean()
        eleve = cleaned.get("eleve")
        annee = cleaned.get("annee")

        if eleve and annee:
            qs = Inscription.objects.filter(eleve=eleve, annee=annee)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError("⚠️ Cet élève est déjà inscrit pour cette année.")

        return cleaned


def _parse_payload_safe(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _to_decimal_safe(v) -> Decimal:
    try:
        s = str(v if v is not None else "").strip().replace(",", ".")
        if s == "":
            return Decimal("0.00")
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


class PaiementForm(forms.ModelForm):
    # ✅ payload multi-mois (rempli par JS)
    echeances_payload = forms.CharField(required=False, widget=forms.HiddenInput)

    # optionnel (si tu veux l’envoyer / afficher)
    montant_total = forms.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=10)

    class Meta:
        model = Paiement
        fields = ["inscription", "nature", "echeance", "montant", "mode", "reference", "note"]

    def __init__(self, *args, inscription=None, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ IMPORTANT : en multi-mois, echeance ne doit PAS être required
        if "echeance" in self.fields:
            self.fields["echeance"].required = False

        base_qs = (
            Inscription.objects
            .select_related("eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre")
            .all()
        )

        self._forced_inscription = None
        if inscription:
            self._forced_inscription = inscription
            self.fields["inscription"].queryset = base_qs.filter(pk=inscription.pk)
            self.fields["inscription"].initial = inscription.pk
            self.fields["inscription"].disabled = True
        else:
            self.fields["inscription"].queryset = base_qs

        # queryset echeances (utile en mode single)
        insc = inscription
        if not insc:
            insc_id = (self.data.get("inscription") or self.initial.get("inscription") or "")
            try:
                insc = Inscription.objects.filter(pk=int(insc_id)).first()
            except Exception:
                insc = None

        if insc and "echeance" in self.fields:
            self.fields["echeance"].queryset = (
                EcheanceMensuelle.objects
                .filter(eleve_id=insc.eleve_id, annee_id=insc.annee_id)
                .order_by("mois_index")
            )
        elif "echeance" in self.fields:
            self.fields["echeance"].queryset = EcheanceMensuelle.objects.none()

    def clean(self):
        cleaned = super().clean()

        insc = cleaned.get("inscription")

        # ✅ sécurité URL (paiement_create_for_inscription)
        if getattr(self, "_forced_inscription", None) and insc and insc.pk != self._forced_inscription.pk:
            raise ValidationError({"inscription": "Inscription invalide (forcée par l’URL)."})

        nature = (cleaned.get("nature") or "SCOLARITE").upper()

        if not insc:
            raise ValidationError({"inscription": "Inscription obligatoire."})

        # ✅ lire payload depuis POST (pas cleaned)
        payload = _parse_payload_safe(self.data.get("echeances_payload"))
        selected_ids = payload.get("selected_ids") or []
        prices_raw = payload.get("prices") or {}

        # normaliser ids (unique)
        ids_int = []
        for x in selected_ids:
            try:
                ids_int.append(int(str(x).strip()))
            except Exception:
                pass
        ids_int = list(dict.fromkeys(ids_int))
        is_multi = bool(ids_int)

        # =========================
        # INSCRIPTION
        # =========================
        if nature == "INSCRIPTION":
            m = cleaned.get("montant") or Decimal("0.00")
            if m <= 0:
                raise ValidationError({"montant": "Montant obligatoire."})
            if m > (insc.reste_inscription or Decimal("0.00")):
                raise ValidationError({"montant": f"Montant trop élevé. Max = {insc.reste_inscription} MAD."})

            cleaned["echeance"] = None
            cleaned["payload_selected_ids"] = []
            cleaned["payload_prices"] = {}
            cleaned["montant_total"] = m
            return cleaned

        # =========================
        # SCOLARITE MULTI-MOIS (FULL ONLY + prix modifiable)
        # =========================
        if nature == "SCOLARITE" and is_multi:
            qs = EcheanceMensuelle.objects.filter(
                id__in=ids_int,
                eleve_id=insc.eleve_id,
                annee_id=insc.annee_id
            )
            if qs.count() != len(ids_int):
                raise ValidationError("Certaines échéances ne correspondent pas à cet élève / année.")

            ech_map = {e.id: e for e in qs}
            total = Decimal("0.00")
            norm_prices = {}

            for eid in ids_int:
                e = ech_map.get(eid)
                if not e:
                    raise ValidationError("Échéance invalide.")

                # ✅ interdit si déjà payé
                if e.statut == "PAYE":
                    raise ValidationError(f"{e.mois_nom} est déjà réglé.")

                key = str(e.id)
                amount = _to_decimal_safe(prices_raw.get(key, e.montant_du))

                if amount <= 0:
                    raise ValidationError(f"Montant invalide pour {e.mois_nom}.")

                # ✅ Règle A : on enregistre ce montant comme nouveau prix du mois
                norm_prices[key] = str(amount)
                total += amount

            if total <= 0:
                raise ValidationError("Sélectionne au moins un mois.")

            cleaned["echeance"] = None
            cleaned["payload_selected_ids"] = ids_int
            cleaned["payload_prices"] = norm_prices
            cleaned["montant"] = total
            cleaned["montant_total"] = total
            return cleaned

        # =========================
        # SCOLARITE SINGLE
        # =========================
        if nature == "SCOLARITE" and not is_multi:
            ech = cleaned.get("echeance")
            m = cleaned.get("montant") or Decimal("0.00")

            if not ech:
                raise ValidationError({"echeance": "Échéance obligatoire (mode single)."})
            if ech.eleve_id != insc.eleve_id or ech.annee_id != insc.annee_id:
                raise ValidationError({"echeance": "Cette échéance ne correspond pas à cet élève / année."})

            if m <= 0:
                raise ValidationError({"montant": "Montant obligatoire."})

            if m > (ech.reste or Decimal("0.00")):
                raise ValidationError({"montant": f"Montant trop élevé. Max = {ech.reste} MAD."})

            cleaned["payload_selected_ids"] = []
            cleaned["payload_prices"] = {}
            cleaned["montant_total"] = m
            return cleaned

        return cleaned


class EnseignantForm(forms.ModelForm):
    class Meta:
        model = Enseignant
        fields = ["nom", "prenom", "telephone", "email", "specialite", "photo", "is_active"]
        widgets = {
            "telephone": forms.TextInput(attrs={"placeholder": "+212 ..."}),
            "email": forms.EmailInput(attrs={"placeholder": "email@exemple.com"}),
            "specialite": forms.TextInput(attrs={"placeholder": "Ex: Mathématiques"}),
        }
 


class EnseignantGroupeForm(forms.ModelForm):
    class Meta:
        model = EnseignantGroupe
        fields = ["annee", "groupe"]
        widgets = {
            "annee": forms.Select(attrs={"id": "id_annee_aff"}),
            "groupe": forms.Select(attrs={"id": "id_groupe_aff"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        active = AnneeScolaire.objects.filter(is_active=True).first()
        if active and not self.initial.get("annee") and not getattr(self.instance, "annee_id", None):
            self.initial["annee"] = active

        annee_id = (
            self.data.get("annee")
            or getattr(self.instance, "annee_id", None)
            or (active.id if active else None)
        )

        if annee_id:
            self.fields["groupe"].queryset = (
                Groupe.objects.filter(annee_id=annee_id)
                .select_related("niveau", "niveau__degre", "annee")
                .order_by("niveau__degre__ordre", "niveau__ordre", "nom")
            )
        else:
            self.fields["groupe"].queryset = Groupe.objects.none()


class SeanceForm(forms.ModelForm):
    class Meta:
        model = Seance
        fields = ["annee", "groupe", "enseignant", "jour", "heure_debut", "heure_fin", "matiere", "salle"]
        widgets = {
            "heure_debut": forms.TimeInput(attrs={"type": "time"}),
            "heure_fin": forms.TimeInput(attrs={"type": "time"}),
            "matiere": forms.TextInput(attrs={"placeholder": "Ex: Math"}),
            "salle": forms.TextInput(attrs={"placeholder": "Ex: Salle 3"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ année active par défaut
        active = AnneeScolaire.objects.filter(is_active=True).first()
        if active and not self.initial.get("annee"):
            self.initial["annee"] = active

        # ✅ 1) déterminer annee_id et groupe_id (POST ou initial ou instance)
        annee_id = None
        groupe_id = None

        if self.data.get("annee"):
            annee_id = self.data.get("annee")
        elif self.initial.get("annee"):
            a = self.initial.get("annee")
            annee_id = a.id if hasattr(a, "id") else a
        elif getattr(self.instance, "annee_id", None):
            annee_id = self.instance.annee_id

        if self.data.get("groupe"):
            groupe_id = self.data.get("groupe")
        elif getattr(self.instance, "groupe_id", None):
            groupe_id = self.instance.groupe_id

        # ✅ 2) Filtrer GROUPES par année (optionnel mais pratique)
        if annee_id:
            self.fields["groupe"].queryset = (
                Groupe.objects.filter(annee_id=annee_id)
                .select_related("niveau", "annee")
                .order_by("niveau__degre__ordre", "niveau__ordre", "nom")
            )
        else:
            self.fields["groupe"].queryset = Groupe.objects.none()

        # ✅ 3) Filtrer ENSEIGNANTS selon affectations (annee + groupe)
        if annee_id and groupe_id:
            enseignant_ids = (
                EnseignantGroupe.objects
                .filter(annee_id=annee_id, groupe_id=groupe_id)
                .values_list("enseignant_id", flat=True)
            )
            self.fields["enseignant"].queryset = (
                Enseignant.objects.filter(id__in=enseignant_ids, is_active=True)
                .order_by("nom", "prenom")
            )
        else:
            # tant que groupe pas choisi -> vide (pratique)
            self.fields["enseignant"].queryset = Enseignant.objects.none()

    def clean(self):
        cleaned = super().clean()
        annee = cleaned.get("annee")
        groupe = cleaned.get("groupe")
        enseignant = cleaned.get("enseignant")
        jour = cleaned.get("jour")
        debut = cleaned.get("heure_debut")
        fin = cleaned.get("heure_fin")

        if debut and fin and debut >= fin:
            raise forms.ValidationError("⚠️ L'heure de fin doit être après l'heure de début.")

        if not all([annee, groupe, enseignant, jour, debut, fin]):
            return cleaned

        qs = Seance.objects.filter(annee=annee, jour=jour)

        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.filter(groupe=groupe, heure_debut__lt=fin, heure_fin__gt=debut).exists():
            raise forms.ValidationError("⚠️ Conflit: ce groupe a déjà une séance sur ce créneau.")

        if qs.filter(enseignant=enseignant, heure_debut__lt=fin, heure_fin__gt=debut).exists():
            raise forms.ValidationError("⚠️ Conflit: cet enseignant a déjà une séance sur ce créneau.")

        return cleaned



class AbsenceForm(forms.ModelForm):
    class Meta:
        model = Absence
        fields = ["annee", "eleve", "groupe", "date", "seance", "type", "justifie", "motif"]
        widgets = {
            "motif": forms.TextInput(attrs={"placeholder": "Motif (option)"}),
            "annee": forms.Select(attrs={"id": "id_annee"}),
            "groupe": forms.Select(attrs={"id": "id_groupe"}),
            "date": forms.DateInput(attrs={"id": "id_date", "type": "date"}),
            "seance": forms.Select(attrs={"id": "id_seance"}),
            "eleve": forms.Select(attrs={"id": "id_eleve"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        active = AnneeScolaire.objects.filter(is_active=True).first()

        # ✅ si pas d'année active => on laisse, mais UI sera vide
        if not active:
            return

        # ─────────────────────────────────────────
        # ✅ 1) Année = uniquement active
        # ─────────────────────────────────────────
        self.fields["annee"].queryset = AnneeScolaire.objects.filter(id=active.id)
        self.initial["annee"] = active.id

        # 👉 Option: cacher totalement le champ année (recommandé)
        # self.fields["annee"].widget = forms.HiddenInput()

        # ─────────────────────────────────────────
        # ✅ récupérer "groupe_id" depuis:
        # - POST (submit)
        # - initial (GET prérempli)
        # - instance (update)
        # ─────────────────────────────────────────
        groupe_id = None

        if self.data.get("groupe"):
            groupe_id = str(self.data.get("groupe")).strip() or None
        elif self.initial.get("groupe"):
            groupe_id = str(self.initial.get("groupe")).strip() or None
        elif getattr(self.instance, "groupe_id", None):
            groupe_id = str(self.instance.groupe_id)

        # ─────────────────────────────────────────
        # ✅ 2) Groupes = seulement année active
        # ─────────────────────────────────────────
        self.fields["groupe"].queryset = Groupe.objects.filter(annee=active).select_related("niveau", "niveau__degre")

        # ─────────────────────────────────────────
        # ✅ 3) Séances = seulement année active
        #    + si groupe choisi => séances du groupe
        # ─────────────────────────────────────────
        seances_qs = Seance.objects.filter(annee=active).select_related("enseignant", "groupe")
        if groupe_id and groupe_id.isdigit():
            seances_qs = seances_qs.filter(groupe_id=int(groupe_id))
        self.fields["seance"].queryset = seances_qs

        # ─────────────────────────────────────────
        # ✅ 4) Élèves = seulement élèves inscrits dans le groupe (année active)
        # ─────────────────────────────────────────
        if groupe_id and groupe_id.isdigit():
            eleve_ids = (
                Inscription.objects
                .filter(annee=active, groupe_id=int(groupe_id))
                .values_list("eleve_id", flat=True)
                .distinct()
            )
            self.fields["eleve"].queryset = Eleve.objects.filter(id__in=eleve_ids).order_by("nom", "prenom")
        else:
            # tant qu'on a pas choisi groupe -> vide (plus propre)
            self.fields["eleve"].queryset = Eleve.objects.none()

        # ─────────────────────────────────────────
        # ✅ 5) sécurité: empêcher autre année en POST
        # ─────────────────────────────────────────
        if self.data.get("annee") and str(self.data.get("annee")) != str(active.id):
            # on force l’année active côté formulaire
            mutable = getattr(self.data, "_mutable", None)
            try:
                if mutable is not None:
                    self.data._mutable = True
                self.data["annee"] = str(active.id)
            finally:
                if mutable is not None:
                    self.data._mutable = mutable

    def clean(self):
        cleaned = super().clean()

        active = AnneeScolaire.objects.filter(is_active=True).first()
        if active:
            # ✅ override final (même si l'user a bricolé le POST)
            cleaned["annee"] = active

        eleve = cleaned.get("eleve")
        date = cleaned.get("date")
        seance = cleaned.get("seance")

        if not eleve or not date:
            return cleaned

        qs = Absence.objects.filter(eleve=eleve, date=date)

        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if seance:
            if qs.filter(seance=seance).exists():
                raise forms.ValidationError("⚠️ Cette absence existe déjà (même séance).")
        else:
            if qs.filter(seance__isnull=True).exists():
                raise forms.ValidationError("⚠️ Une absence (sans séance) existe déjà pour cet élève à cette date.")

        return cleaned

# --- G1: Parents ---
from django import forms
from django.forms import inlineformset_factory
from .models import Parent, ParentEleve

class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ["nom", "prenom", "telephone", "email", "adresse", "is_active"]
        widgets = {
            "telephone": forms.TextInput(attrs={"placeholder": "+212 ..."}),
            "email": forms.EmailInput(attrs={"placeholder": "email@exemple.com"}),
            "adresse": forms.TextInput(attrs={"placeholder": "Adresse (option)"}),
        }

class ParentEleveForm(forms.ModelForm):
    class Meta:
        model = ParentEleve
        fields = ["eleve", "lien"]   # ✅ parent est implicite via inline formset
        widgets = {
            "lien": forms.Select(),
        }

ParentEleveFormSet = inlineformset_factory(
    Parent,
    ParentEleve,
    form=ParentEleveForm,
    extra=1,
    can_delete=True
)

from django import forms
from .models import Matiere, Periode, Evaluation



class MatiereForm(forms.ModelForm):
    class Meta:
        model = Matiere
        fields = ["nom", "code", "coefficient", "is_active", "niveaux", "enseignants"]

        widgets = {
            "nom": forms.TextInput(attrs={
                "class": "az-input",
                "placeholder": "Ex: Mathématiques",
                "autocomplete": "off",
            }),
            "code": forms.TextInput(attrs={
                "class": "az-input",
                "placeholder": "Ex: MATH",
                "autocomplete": "off",
            }),
            "coefficient": forms.NumberInput(attrs={
                "class": "az-input",
                "min": "0",
                "step": "0.5",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "az-check",
            }),
            "niveaux": forms.SelectMultiple(attrs={
                "class": "az-select",
                "size": "8",
                "data-placeholder": "Sélectionner les niveaux…",
            }),
            "enseignants": forms.SelectMultiple(attrs={
                "class": "az-select",
                "size": "8",
                "data-placeholder": "Sélectionner les enseignants…",
            }),
        }


# ✅ Semestres auto (pas de CRUD)
# PeriodeForm supprimé volontairement:
# Les semestres (S1/S2) sont créés automatiquement à chaque année scolaire.


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = [
            "titre", "periode", "groupe", "matiere", "enseignant",
            "type", "date", "note_max", "coefficient"
        ]

    def __init__(self, *args, **kwargs):
        # ✅ on accepte un param custom depuis la view
        niveau_ui = kwargs.pop("niveau_ui", None)

        super().__init__(*args, **kwargs)

        # =========================
        # ✅ Année active
        # =========================
        active = AnneeScolaire.objects.filter(is_active=True).first()

        # Par défaut : éviter afficher tout
        self.fields["matiere"].queryset = Matiere.objects.none()
        self.fields["enseignant"].queryset = Enseignant.objects.none()

        # ✅ Filtrer groupe/période par année active
        if active:
            qs_groupes = Groupe.objects.select_related("niveau", "annee").filter(annee=active)
            if niveau_ui and str(niveau_ui).isdigit():
                qs_groupes = qs_groupes.filter(niveau_id=int(niveau_ui))

            self.fields["groupe"].queryset = qs_groupes.order_by("niveau__degre__ordre", "niveau__ordre", "nom")

            # IMPORTANT : adapte si ton modèle Periode s'appelle autrement
            self.fields["periode"].queryset = Periode.objects.filter(annee=active).order_by("ordre")
        else:
            self.fields["groupe"].queryset = Groupe.objects.none()
            self.fields["periode"].queryset = Periode.objects.none()

        # =========================
        # ✅ UPDATE (instance existante)
        # =========================
        if self.instance and self.instance.pk and self.instance.groupe_id:
            g = self.instance.groupe

            # sécurité : si groupe pas année active => on laisse quand même afficher, mais tu peux bloquer
            if getattr(g, "niveau_id", None):
                self.fields["matiere"].queryset = (
                    Matiere.objects.filter(niveaux=g.niveau, is_active=True).order_by("nom")
                )

            # enseignants par affectations (année + groupe)
            self.fields["enseignant"].queryset = (
                Enseignant.objects.filter(
                    is_active=True,
                    affectations_groupes__annee_id=g.annee_id,
                    affectations_groupes__groupe_id=g.id
                ).distinct().order_by("nom", "prenom")
            )
            return

        # =========================
        # ✅ CREATE / POST (groupe choisi)
        # =========================
        data = self.data or None
        groupe_id = data.get("groupe") if data else None

        if active and groupe_id and str(groupe_id).isdigit():
            g = Groupe.objects.select_related("niveau", "annee").filter(
                id=int(groupe_id),
                annee=active,   # ✅ BLOQUE les groupes des autres années
            ).first()

            if g:
                self.fields["matiere"].queryset = (
                    Matiere.objects.filter(niveaux=g.niveau, is_active=True).order_by("nom")
                )

                self.fields["enseignant"].queryset = (
                    Enseignant.objects.filter(
                        is_active=True,
                        affectations_groupes__annee_id=g.annee_id,
                        affectations_groupes__groupe_id=g.id
                    ).distinct().order_by("nom", "prenom")
                )

    def clean_periode(self):
        """✅ Empêche choisir une période d’une autre année."""
        p = self.cleaned_data.get("periode")
        active = AnneeScolaire.objects.filter(is_active=True).first()
        if active and p and getattr(p, "annee_id", None) != active.id:
            raise ValidationError("Période invalide (pas dans l'année active).")
        return p

    def clean_groupe(self):
        """✅ Empêche choisir un groupe d’une autre année."""
        g = self.cleaned_data.get("groupe")
        active = AnneeScolaire.objects.filter(is_active=True).first()
        if active and g and getattr(g, "annee_id", None) != active.id:
            raise ValidationError("Groupe invalide (pas dans l'année active).")
        return g


# core/forms.py
# core/forms.py
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import (
    AnneeScolaire, Groupe,
    Eleve, Parent, ParentEleve,
    Inscription
)
import re

def normalize_phone(phone: str) -> str:
    """
    0672786793
    06.72.78.67.93
    06 72 78 67 93
    +212672786793
    → 0672786793
    """
    if not phone:
        return ""

    # garder uniquement les chiffres
    digits = re.sub(r"\D", "", phone)

    # Maroc: +2126XXXXXXXX → 06XXXXXXXX
    if digits.startswith("212") and len(digits) >= 12:
        digits = "0" + digits[3:]

    return digits

class InscriptionFullForm(forms.Form):
    """
    1 écran => crée :
      - Élève (avec photo)
      - (optionnel) Parent
      - (optionnel) Lien ParentEleve
      - Inscription

    ✅ Règle AZ:
    - Les PRIX sont par NIVEAU via FraisNiveau.
    - Donc on ne touche PAS les tarifs ici.
    - Inscription.save() appliquera automatiquement les tarifs.
    """

    # =========================
    # SECTION ELEVE
    # =========================
    eleve_nom = forms.CharField(
        max_length=80, label="Nom élève",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "Nom"})
    )
    eleve_prenom = forms.CharField(
        max_length=80, label="Prénom élève",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "Prénom"})
    )

    eleve_photo = forms.ImageField(
        required=False, label="Photo élève",
        widget=forms.ClearableFileInput(attrs={"class": "az-input"})
    )

    eleve_sexe = forms.ChoiceField(
        choices=[("", "—"), ("M", "Masculin"), ("F", "Féminin")],
        required=False, label="Sexe",
        widget=forms.Select(attrs={"class": "az-select"})
    )
    eleve_date_naissance = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "az-input"}),
        label="Date naissance"
    )
    eleve_lieu_naissance = forms.CharField(
        max_length=120, required=False, label="Lieu naissance",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "Ville"})
    )
    dernier_etablissement = forms.CharField(
        required=False,
        max_length=160,
        label="Dernier établissement",
        widget=forms.TextInput(attrs={
            "class": "az-input",
            "placeholder": "Ex : École X / Collège Y..."
        })
    )

    eleve_adresse = forms.CharField(
        max_length=255, required=False, label="Adresse",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "Adresse"})
    )
    eleve_telephone = forms.CharField(
        max_length=30, required=False, label="Téléphone élève",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "06..."})
    )

    # =========================
    # SECTION PARENT (OPTIONNEL)
    # =========================
    parent_nom = forms.CharField(
        max_length=80, required=False, label="Nom parent",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "Nom"})
    )
    parent_prenom = forms.CharField(
        max_length=80, required=False, label="Prénom parent",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "Prénom"})
    )
    parent_telephone = forms.CharField(
        max_length=30, required=False, label="Téléphone parent",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "06..."})
    )
    parent_email = forms.EmailField(
        required=False, label="Email parent",
        widget=forms.EmailInput(attrs={"class": "az-input", "placeholder": "email@..."})
    )
    parent_adresse = forms.CharField(
        max_length=255, required=False, label="Adresse parent",
        widget=forms.TextInput(attrs={"class": "az-input", "placeholder": "Adresse"})
    )

    lien = forms.ChoiceField(
        choices=[("PERE", "Père"), ("MERE", "Mère"), ("TUTEUR", "Tuteur"), ("AUTRE", "Autre")],
        initial="TUTEUR",
        required=False,  # ✅ deviendra obligatoire si parent rempli
        label="Lien",
        widget=forms.Select(attrs={"class": "az-select"})
    )

    # =========================
    # SECTION INSCRIPTION
    # =========================
    annee = forms.ModelChoiceField(
        queryset=AnneeScolaire.objects.all().order_by("-date_debut"),
        label="Année scolaire",
        widget=forms.Select(attrs={"class": "az-select"})
    )
    groupe = forms.ModelChoiceField(
        queryset=Groupe.objects.none(),
        label="Groupe / Classe",
        widget=forms.Select(attrs={"class": "az-select"})
    )
    statut = forms.ChoiceField(
        choices=[("VALIDEE", "Validée"), ("EN_COURS", "En cours")],
        initial="VALIDEE",
        label="Statut",
        widget=forms.Select(attrs={"class": "az-select"})
    )

    # =========================
    # INIT (groupes par année)
    # =========================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ année active par défaut
        active = AnneeScolaire.objects.filter(is_active=True).first()
        if active and not self.initial.get("annee"):
            self.initial["annee"] = active

        annee_id = None
        if self.data.get("annee"):
            annee_id = self.data.get("annee")
        elif self.initial.get("annee"):
            a = self.initial.get("annee")
            annee_id = a.id if hasattr(a, "id") else a

        if annee_id:
            self.fields["groupe"].queryset = (
                Groupe.objects.filter(annee_id=annee_id)
                .select_related("niveau", "annee", "niveau__degre")
                .order_by("niveau__degre__ordre", "niveau__ordre", "nom")
            )
        else:
            self.fields["groupe"].queryset = Groupe.objects.none()

    # =========================
    # VALIDATIONS
    # =========================
    def clean_eleve_photo(self):
        f = self.cleaned_data.get("eleve_photo")
        if not f:
            return f

        # ✅ limite taille (ex: 2MB)
        max_size = 2 * 1024 * 1024
        if f.size > max_size:
            raise ValidationError("⚠️ Photo trop lourde (max 2MB).")

        # ✅ extensions autorisées
        name = (getattr(f, "name", "") or "").lower()
        allowed = (".jpg", ".jpeg", ".png", ".webp")
        if name and not name.endswith(allowed):
            raise ValidationError("⚠️ Format photo invalide. Utilise JPG/PNG/WEBP.")

        return f

    def clean(self):
        cd = super().clean()

        annee = cd.get("annee")
        groupe = cd.get("groupe")
        if annee and groupe and groupe.annee_id != annee.id:
            raise ValidationError("⚠️ Le groupe choisi n'appartient pas à l'année sélectionnée.")

        # Parent optionnel: si un champ parent est rempli => nom+prenom+lien obligatoires
        p_nom = (cd.get("parent_nom") or "").strip()
        p_pre = (cd.get("parent_prenom") or "").strip()
        p_tel = (cd.get("parent_telephone") or "").strip()
        p_mail = (cd.get("parent_email") or "").strip()
        has_any_parent = any([p_nom, p_pre, p_tel, p_mail])

        if has_any_parent:
            if not p_nom or not p_pre:
                raise ValidationError("⚠️ Si tu ajoutes un parent, le Nom + Prénom parent sont obligatoires.")
            if not (cd.get("lien") or "").strip():
                raise ValidationError("⚠️ Choisis le lien (Père/Mère/Tuteur/Autre).")

        return cd

    # =========================
    # SAVE
    # =========================
    @transaction.atomic
    def save(self):
        cd = self.cleaned_data

        # 1) Élève (+ photo)
        eleve = Eleve.objects.create(
            nom=cd["eleve_nom"].strip(),
            prenom=cd["eleve_prenom"].strip(),
            photo=cd.get("eleve_photo"),
            sexe=cd.get("eleve_sexe") or "",
            date_naissance=cd.get("eleve_date_naissance"),
            lieu_naissance=(cd.get("eleve_lieu_naissance") or "").strip(),
            adresse=(cd.get("eleve_adresse") or "").strip(),
            telephone=(cd.get("eleve_telephone") or "").strip(),
            is_active=True,
        )
        eleve.refresh_from_db(fields=["matricule"])

        # 2) Parent optionnel (réutiliser/créer) + lien
        parent = None
        p_nom = (cd.get("parent_nom") or "").strip()
        p_pre = (cd.get("parent_prenom") or "").strip()
        p_tel = (cd.get("parent_telephone") or "").strip()
        p_mail = (cd.get("parent_email") or "").strip()
        p_adr = (cd.get("parent_adresse") or "").strip()

        has_any_parent = any([p_nom, p_pre, p_tel, p_mail])

        if has_any_parent:
            norm_tel = normalize_phone(p_tel)

            # priorité email, sinon tel normalisé
            if p_mail:
                parent = Parent.objects.filter(email__iexact=p_mail).first()

            if not parent and norm_tel:
                parent = Parent.objects.filter(telephone_norm=norm_tel).first()

            if not parent:
                parent = Parent.objects.create(
                    user=None,
                    nom=p_nom,
                    prenom=p_pre,
                    telephone=p_tel,
                    telephone_norm=norm_tel,
                    email=p_mail,
                    adresse=p_adr,
                    is_active=True,
                )
            else:
                # update soft + set telephone_norm si vide
                changed = False

                if norm_tel and not (parent.telephone_norm or "").strip():
                    parent.telephone_norm = norm_tel
                    changed = True

                if p_nom and not (parent.nom or "").strip():
                    parent.nom = p_nom; changed = True
                if p_pre and not (parent.prenom or "").strip():
                    parent.prenom = p_pre; changed = True
                if p_tel and not (parent.telephone or "").strip():
                    parent.telephone = p_tel; changed = True
                if p_mail and not (parent.email or "").strip():
                    parent.email = p_mail; changed = True
                if p_adr and not (parent.adresse or "").strip():
                    parent.adresse = p_adr; changed = True

                if changed:
                    parent.save()

            ParentEleve.objects.get_or_create(
                parent=parent,
                eleve=eleve,
                defaults={"lien": cd.get("lien") or "TUTEUR"},
            )

        # 3) Inscription
        inscription = Inscription.objects.create(
            eleve=eleve,
            annee=cd["annee"],
            groupe=cd["groupe"],
            statut=cd["statut"],
            dernier_etablissement=(cd.get("dernier_etablissement") or "").strip(),

        )

        return eleve, parent, inscription


password = forms.CharField(
    required=False,
    widget=forms.PasswordInput(attrs={"class": "az-input", "placeholder": "Nouveau mot de passe"})
)


from django import forms

class UserPasswordForm(forms.Form):
    auto_password = forms.BooleanField(
        required=False,
        initial=True,
        label="Reset automatique",
        widget=forms.CheckboxInput(attrs={"class": "az-toggle"})
    )

    password = forms.CharField(
        required=False,
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "az-input",
            "placeholder": "Nouveau mot de passe…",
            "autocomplete": "new-password",
        })
    )

    def clean(self):
        cleaned = super().clean()
        auto = cleaned.get("auto_password")
        pwd = (cleaned.get("password") or "").strip()

        # si reset auto désactivé => mdp obligatoire
        if not auto and len(pwd) < 6:
            self.add_error("password", "Mot de passe requis (min 6 caractères) si le reset auto est désactivé.")
        return cleaned

from django import forms

class PasswordChangeForm(forms.Form):
    auto_password = forms.BooleanField(
        required=False,
        initial=True,
        label="Reset automatique (générer un mot de passe temporaire)",
        widget=forms.CheckboxInput(attrs={"class": "az-toggle"})
    )

    password = forms.CharField(
        required=False,
        label="Mot de passe (si reset automatique désactivé)",
        widget=forms.PasswordInput(attrs={
            "class": "az-input",
            "placeholder": "Nouveau mot de passe…",
            "autocomplete": "new-password",
        })
    )

    def clean(self):
        cleaned = super().clean()
        auto = cleaned.get("auto_password")
        pwd = (cleaned.get("password") or "").strip()

        if not auto and len(pwd) < 6:
            self.add_error("password", "Mot de passe requis (min 6 caractères) si le reset automatique est désactivé.")
        return cleaned


from .models import Avis, Groupe, Eleve, Inscription

class AvisForm(forms.ModelForm):
    class Meta:
        model = Avis
        fields = ["titre", "contenu", "cible_type", "degre", "niveau", "groupe", "eleve", "visible_parent"]
        widgets = {
            "titre": forms.TextInput(attrs={
                "class": "az-input", "id": "id_titre",
                "placeholder": "Ex: Réunion parents, sortie scolaire..."
            }),
            "contenu": forms.Textarea(attrs={
                "class": "az-textarea", "id": "id_contenu",
                "rows": 7, "placeholder": "Écris ton avis ici..."
            }),
            "cible_type": forms.Select(attrs={"class": "az-select", "id": "id_cible_type"}),
            "degre": forms.Select(attrs={"class": "az-select", "id": "id_degre"}),
            "niveau": forms.Select(attrs={"class": "az-select", "id": "id_niveau"}),
            "groupe": forms.Select(attrs={"class": "az-select", "id": "id_groupe"}),
            "eleve": forms.Select(attrs={"class": "az-select", "id": "id_eleve"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Par défaut vides (AJAX remplira)
        self.fields["groupe"].queryset = Groupe.objects.none()
        self.fields["eleve"].queryset = Eleve.objects.none()

        # --- niveau_id (pour groupes) ---
        niveau_id = None
        if self.instance and self.instance.pk and getattr(self.instance, "niveau_id", None):
            niveau_id = self.instance.niveau_id
        else:
            raw_niveau = self.data.get("niveau")  # name="niveau"
            if raw_niveau and str(raw_niveau).isdigit():
                niveau_id = int(raw_niveau)

        if niveau_id:
            self.fields["groupe"].queryset = Groupe.objects.filter(niveau_id=niveau_id).order_by("nom")

        # --- groupe_id (pour élèves) ---
        groupe_id = None
        if self.instance and self.instance.pk and getattr(self.instance, "groupe_id", None):
            groupe_id = self.instance.groupe_id
        else:
            raw_groupe = self.data.get("groupe")  # name="groupe"
            if raw_groupe and str(raw_groupe).isdigit():
                groupe_id = int(raw_groupe)

        if groupe_id:
            self.fields["eleve"].queryset = (
                Eleve.objects
                .filter(inscriptions__groupe_id=groupe_id)
                .distinct()
                .order_by("nom", "prenom")
            )

    def clean(self):
        cleaned = super().clean()
        cible  = cleaned.get("cible_type")

        degre  = cleaned.get("degre")
        niveau = cleaned.get("niveau")
        groupe = cleaned.get("groupe")
        eleve  = cleaned.get("eleve")

        def must_empty(*names):
            for n in names:
                if cleaned.get(n):
                    self.add_error(n, "Ce champ doit rester vide pour ce type de cible.")

        # TOUS
        if cible == "TOUS":
            if any([degre, niveau, groupe, eleve]):
                raise ValidationError("Cible = Tous → ne sélectionne aucun Degré / Niveau / Groupe / Élève.")
            return cleaned

        # DEGRE
        if cible == "DEGRE":
            if not degre:
                self.add_error("degre", "Le degré est obligatoire.")
            must_empty("niveau", "groupe", "eleve")
            return cleaned

        # NIVEAU
        if cible == "NIVEAU":
            if not niveau:
                self.add_error("niveau", "Le niveau est obligatoire.")
            must_empty("degre", "groupe", "eleve")
            return cleaned

        # GROUPE = niveau + groupe
        if cible == "GROUPE":
            if not niveau:
                self.add_error("niveau", "Le niveau est obligatoire pour choisir un groupe.")
            if not groupe:
                self.add_error("groupe", "Le groupe est obligatoire.")

            must_empty("degre", "eleve")

            if groupe and niveau and getattr(groupe, "niveau_id", None) != niveau.id:
                self.add_error("groupe", "Ce groupe ne correspond pas au niveau sélectionné.")
            return cleaned

        # ELEVE = niveau + groupe + eleve
        if cible == "ELEVE":
            if not niveau:
                self.add_error("niveau", "Le niveau est obligatoire.")
            if not groupe:
                self.add_error("groupe", "Le groupe est obligatoire.")
            if not eleve:
                self.add_error("eleve", "L’élève est obligatoire.")

            must_empty("degre")

            if groupe and niveau and getattr(groupe, "niveau_id", None) != niveau.id:
                self.add_error("groupe", "Ce groupe ne correspond pas au niveau sélectionné.")

            if eleve and groupe:
                ok = Inscription.objects.filter(eleve_id=eleve.id, groupe_id=groupe.id).exists()
                if not ok:
                    self.add_error("eleve", "Cet élève n’appartient pas au groupe sélectionné.")

            return cleaned

        return cleaned





