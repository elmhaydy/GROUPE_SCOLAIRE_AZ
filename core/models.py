
# core/models.py
from django.db import models
from django.db.models import Q
from django.conf import settings
from accounts.threadlocal import get_current_user
from django.contrib.auth.models import Group
from datetime import datetime, date as date_cls
from django.db import models
from django.conf import settings
from core.utils_dates import month_start, add_months
import os
import uuid
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from decimal import Decimal
from django.conf import settings
from django.db.models import Q
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.db import models, transaction as db_transaction
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal
import calendar
from datetime import date as date_cls
import os
import uuid
import calendar
from decimal import Decimal
from datetime import date as date_cls
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from accounts.threadlocal import get_current_user  # ✅ comme chez toi

# =========================
# Audit
# =========================
class AuditBase(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_%(class)s_set"
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="updated_%(class)s_set"
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user and getattr(user, "is_authenticated", False):
            if not self.pk and not self.created_by:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)


# =========================
# Structure scolaire
# =========================
class AnneeScolaire(models.Model):
    """
    Année scolaire (ex: 2025/2026)
    Règle: UNE seule année active à la fois.
    """
    nom = models.CharField(max_length=20, unique=True)
    date_debut = models.DateField()
    date_fin = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_debut"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="unique_active_annee_scolaire",
            )
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            AnneeScolaire.objects.exclude(pk=self.pk).update(is_active=False)

    def __str__(self):
        return self.nom


class Degre(models.Model):
    code = models.CharField(max_length=20, unique=True)  # ex: MATERNELLE
    nom = models.CharField(max_length=50, unique=True)   # ex: Maternelle
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "nom"]

    def __str__(self):
        return self.nom


class Niveau(AuditBase):
    degre = models.ForeignKey(Degre, on_delete=models.PROTECT, related_name="niveaux")
    nom = models.CharField(max_length=80)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["degre__ordre", "ordre", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["degre", "nom"], name="unique_niveau_par_degre")
        ]

    def __str__(self):
        return f"{self.degre.nom} — {self.nom}"


class Groupe(AuditBase):
    annee = models.ForeignKey(AnneeScolaire, on_delete=models.PROTECT, related_name="groupes")
    niveau = models.ForeignKey(Niveau, on_delete=models.PROTECT, related_name="groupes")
    nom = models.CharField(max_length=80)
    capacite = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["annee__date_debut", "niveau__degre__ordre", "niveau__ordre", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["annee", "niveau", "nom"], name="unique_groupe_par_annee_niveau_nom")
        ]

    def __str__(self):
        return f"{self.annee.nom} — {self.niveau.nom} — {self.nom}"


def eleve_photo_path(instance, filename: str) -> str:
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    ident = instance.matricule or (f"tmp-{instance.pk}" if instance.pk else "tmp")
    new_name = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join("eleves", ident, new_name)


class Eleve(AuditBase):
    matricule = models.CharField(max_length=20, unique=True, blank=True)
    nom = models.CharField(max_length=80)
    prenom = models.CharField(max_length=80)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="eleve_profile"
    )
    photo = models.ImageField(upload_to=eleve_photo_path, null=True, blank=True, verbose_name="Photo")

    SEXE_CHOICES = [("M", "Masculin"), ("F", "Féminin")]
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES, blank=True)

    date_naissance = models.DateField(null=True, blank=True)
    lieu_naissance = models.CharField(max_length=120, blank=True)

    adresse = models.CharField(max_length=255, blank=True)
    telephone = models.CharField(max_length=30, blank=True)

    is_active = models.BooleanField(default=True)

    # ✅ Pro: traçabilité d’archivage
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="eleves_archived"
    )

    def archive(self, by_user=None, save=True):
        """Archive (soft delete)"""
        self.is_active = False
        self.archived_at = timezone.now()
        self.archived_by = by_user if by_user and getattr(by_user, "is_authenticated", False) else None

        # ✅ optionnel: désactiver le compte user élève
        if self.user_id:
            self.user.is_active = False
            self.user.save(update_fields=["is_active"])

        if save:
            self.save(update_fields=["is_active", "archived_at", "archived_by"])

    def restore(self, save=True):
        """Restaure"""
        self.is_active = True
        self.archived_at = None
        self.archived_by = None

        # ✅ optionnel: réactiver le compte user élève
        if self.user_id:
            self.user.is_active = True
            self.user.save(update_fields=["is_active"])

        if save:
            self.save(update_fields=["is_active", "archived_at", "archived_by"])

    class Meta:
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.matricule or '—'} — {self.nom} {self.prenom}"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.matricule:
            self.matricule = f"AZ-{self.pk:06d}"
            super().save(update_fields=["matricule"])


# =========================
# Frais par niveau (tarif de référence)
# =========================
class FraisNiveau(AuditBase):
    annee = models.ForeignKey(AnneeScolaire, on_delete=models.PROTECT, related_name="frais_niveaux")
    niveau = models.ForeignKey(Niveau, on_delete=models.PROTECT, related_name="frais_niveaux")

    frais_inscription = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    frais_scolarite_mensuel = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["annee", "niveau"], name="unique_frais_par_annee_niveau")
        ]

    def __str__(self):
        return f"{self.annee.nom} — {self.niveau.nom}"


# =========================================
# Échéances mensuelles (Sep -> Jun) INDEPENDANTES de Inscription
# =======================================

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class EcheanceMensuelle(models.Model):
    """
    Échéances mensuelles Sep->Jun.
    ✅ Indépendantes fonctionnellement : le suivi se fait via (eleve, annee, groupe, mois_index).
    ⚠️ Techniquement, inscription est obligatoire car ta DB a inscription_id NOT NULL + UNIQUE(inscription_id, mois_index).
    """

    # ✅ Obligatoire (conforme DB VPS)
    inscription = models.ForeignKey(
        "Inscription",
        on_delete=models.CASCADE,
        related_name="echeances_mensuelles",
    )

    eleve = models.ForeignKey(
        "Eleve",
        on_delete=models.CASCADE,
        related_name="echeances",
    )

    annee = models.ForeignKey(
        "AnneeScolaire",
        on_delete=models.PROTECT,
        related_name="echeances",
        null=True,
        blank=True,
    )

    # snapshot groupe (filtres impayés)
    groupe = models.ForeignKey(
        "Groupe",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="echeances",
    )

    mois_index = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )  # 1..10 (Sep..Jun)

    date_echeance = models.DateField()

    montant_du = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    STATUT_CHOICES = [
        ("A_PAYER", "À payer"),
        ("PARTIEL", "Partiel"),
        ("PAYE", "Payé"),
    ]
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default="A_PAYER")

    MOIS_FR = {
        1: "Septembre", 2: "Octobre", 3: "Novembre", 4: "Décembre", 5: "Janvier",
        6: "Février", 7: "Mars", 8: "Avril", 9: "Mai", 10: "Juin",
    }

    class Meta:
       ordering = ["mois_index", "id"]
       constraints = [
           models.UniqueConstraint(
               fields=["inscription", "mois_index"],
               name="core_echeancemensuelle_inscription_id_mois_index_b5b1172f_uniq",
           ),
       ]
       indexes = [
           models.Index(fields=["eleve"], name="echm_eleve_idx"),
           models.Index(fields=["groupe"], name="echm_groupe_idx"),
       ]

    @property
    def mois_nom(self) -> str:
        return self.MOIS_FR.get(int(self.mois_index or 0), f"M{self.mois_index}")

    @property
    def reste(self) -> Decimal:
        du = self.montant_du or Decimal("0.00")
        paye = self.montant_paye or Decimal("0.00")
        r = du - paye
        return r if r > Decimal("0.00") else Decimal("0.00")

    def refresh_statut(self, save=True):
        paye = self.montant_paye or Decimal("0.00")
        du = self.montant_du or Decimal("0.00")

        # ✅ sécurité : jamais du < payé
        if du < paye:
            du = paye
            self.montant_du = du
            if save:
                self.save(update_fields=["montant_du"])

        # ✅ statut correct
        if du <= Decimal("0.00"):
            self.statut = "PAYE"
        elif paye <= Decimal("0.00"):
            self.statut = "A_PAYER"
        elif paye < du:
            self.statut = "PARTIEL"
        else:
            self.statut = "PAYE"

        if save:
            self.save(update_fields=["statut"])

    def __str__(self):
        return f"{self.eleve_id} {self.annee_id} {self.mois_nom} reste={self.reste}"





# =========================================
# Inscription (avec sync échéances)
# =========================================
class Inscription(models.Model):
    eleve = models.ForeignKey("Eleve", on_delete=models.CASCADE, related_name="inscriptions")

    annee = models.ForeignKey("AnneeScolaire", on_delete=models.PROTECT, related_name="inscriptions")
    groupe = models.ForeignKey("Groupe", on_delete=models.PROTECT, related_name="inscriptions")
    periode = models.ForeignKey("Periode", on_delete=models.PROTECT, related_name="inscriptions", null=True, blank=True)

    sco_default_mensuel = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Override montant mensuel scolarité pour cette inscription"
    )

    tr_default_mensuel = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Override montant mensuel transport pour cette inscription"
    )
    tarif_override = models.BooleanField(default=False)
    override_frais_inscription_du = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    override_frais_scolarite_mensuel = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    dernier_etablissement = models.CharField(
        max_length=160,
        blank=True,
        default="",
        help_text="Dernier établissement fréquenté"
    )
    date_inscription = models.DateField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=[("EN_COURS", "En cours"), ("VALIDEE", "Validée")], default="VALIDEE")

    frais_inscription_du = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    frais_inscription_paye = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    frais_scolarite_mensuel = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    montant_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    commentaire = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date_inscription"]
        constraints = [
            models.UniqueConstraint(fields=["eleve", "annee"], name="unique_inscription_eleve_annee")
        ]

    @property
    def echeances(self):
        return EcheanceMensuelle.objects.filter(eleve_id=self.eleve_id, annee_id=self.annee_id)

    @property
    def reste_inscription(self) -> Decimal:
        du = self.frais_inscription_du or Decimal("0.00")
        paye = self.frais_inscription_paye or Decimal("0.00")
        return max(du - paye, Decimal("0.00"))

    def save(self, *args, **kwargs):
        creating = self.pk is None  # ✅ True si création

        old_mensuel = None
        if not creating:
            old = Inscription.objects.filter(pk=self.pk).only("frais_scolarite_mensuel").first()
            if old:
                old_mensuel = old.frais_scolarite_mensuel

        # appliquer FraisNiveau si pas override
        if self.annee_id and self.groupe_id:
            if self.tarif_override:
                self.frais_inscription_du = self.override_frais_inscription_du or Decimal("0.00")
                self.frais_scolarite_mensuel = self.override_frais_scolarite_mensuel or Decimal("0.00")
            else:
                niveau = self.groupe.niveau
                fn = FraisNiveau.objects.filter(annee=self.annee, niveau=niveau).first()
                if fn:
                    self.frais_inscription_du = fn.frais_inscription or Decimal("0.00")
                    self.frais_scolarite_mensuel = fn.frais_scolarite_mensuel or Decimal("0.00")

        # total (toujours 10 mois Sep->Jun)
        self.montant_total = (self.frais_inscription_du or Decimal("0.00")) + (self.frais_scolarite_mensuel or Decimal("0.00")) * Decimal("10")

        super().save(*args, **kwargs)

        # ✅ SYNC uniquement en UPDATE (pas en création)
        if (not creating) and (old_mensuel is not None) and (old_mensuel != self.frais_scolarite_mensuel):
            from core.services.echeances import sync_echeances_with_tarif
            sync_echeances_with_tarif(self.id)


    @property
    def total_scolarite_du(self) -> Decimal:
        return (self.frais_scolarite_mensuel or Decimal("0.00")) * Decimal("10")

    @property
    def total_scolarite_paye(self) -> Decimal:
        qs = EcheanceMensuelle.objects.filter(eleve_id=self.eleve_id, annee_id=self.annee_id)
        return sum((e.montant_paye or Decimal("0.00")) for e in qs)

    @property
    def total_reste(self) -> Decimal:
        qs = EcheanceMensuelle.objects.filter(eleve_id=self.eleve_id, annee_id=self.annee_id)
        reste_sco = sum((e.reste for e in qs), Decimal("0.00"))
        return self.reste_inscription + reste_sco

    def __str__(self):
        return f"{self.eleve.matricule} — {self.annee.nom} — {self.groupe.nom}"


# =======================================
# Paiement (INSCRIPTION / SCOLARITE)
# =======================================
class Paiement(models.Model):
    inscription = models.ForeignKey("Inscription", on_delete=models.PROTECT, related_name="paiements")
    date_paiement = models.DateField(auto_now_add=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)

    # ✅ utilisé pour reçu batch multi-mois
    batch_token = models.CharField(max_length=36, blank=True, db_index=True)

    NATURE_CHOICES = [
        ("INSCRIPTION", "Frais d'inscription"),
        ("SCOLARITE", "Frais de scolarité"),
    ]
    nature = models.CharField(max_length=20, choices=NATURE_CHOICES, default="SCOLARITE")

    # single mois (optionnel si tu gardes mode single)
    echeance = models.ForeignKey(
        "EcheanceMensuelle",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="paiements"
    )

    MODE_CHOICES = [
        ("ESPECES", "Espèces"),
        ("VIREMENT", "Virement"),
        ("CHEQUE", "Chèque"),
    ]
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="ESPECES")

    reference = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date_paiement", "-id"]

    def clean(self):
        m = self.montant or Decimal("0.00")
        if m <= 0:
            raise ValidationError({"montant": "⚠️ Montant invalide."})

        if self.nature == "SCOLARITE":
            # paiement global (batch) sans echeance => ok
            if self.batch_token and not self.echeance_id:
                return

            if not self.echeance_id:
                raise ValidationError({"echeance": "⚠️ Échéance obligatoire pour un paiement scolarité."})

            if self.echeance.eleve_id != self.inscription.eleve_id:
                raise ValidationError({"echeance": "⚠️ Cette échéance n'appartient pas à cet élève."})

            if self.echeance.annee_id != self.inscription.annee_id:
                raise ValidationError({"echeance": "⚠️ Cette échéance n'appartient pas à la même année scolaire."})

            reste = self.echeance.reste
            if reste <= Decimal("0.00"):
                raise ValidationError({"echeance": "✅ Cette échéance est déjà réglée."})

            if m > reste:
                raise ValidationError({"montant": f"⚠️ Montant trop élevé. Max = {reste} MAD."})

        elif self.nature == "INSCRIPTION":
            reste = self.inscription.reste_inscription
            if reste <= Decimal("0.00"):
                raise ValidationError({"montant": "✅ Frais d'inscription déjà réglés."})
            if m > reste:
                raise ValidationError({"montant": f"⚠️ Montant trop élevé. Max = {reste} MAD."})

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.full_clean()
        super().save(*args, **kwargs)

        if not is_new:
            return

        # paiement global batch => lignes gèrent les montants mois
        if self.nature == "SCOLARITE" and self.batch_token and not self.echeance_id:
            return

        if self.nature == "INSCRIPTION":
            insc = self.inscription
            insc.frais_inscription_paye = (insc.frais_inscription_paye or Decimal("0.00")) + (self.montant or Decimal("0.00"))
            insc.save(update_fields=["frais_inscription_paye"])

        elif self.nature == "SCOLARITE" and self.echeance_id:
            e = self.echeance
            e.montant_paye = (e.montant_paye or Decimal("0.00")) + (self.montant or Decimal("0.00"))
            e.refresh_statut(save=False)
            e.save(update_fields=["montant_paye", "statut"])


# =========================================
# PaiementLigne (pour Paiement global multi-mois)
# =========================================
class PaiementLigne(models.Model):
    paiement = models.ForeignKey("Paiement", on_delete=models.CASCADE, related_name="lignes")
    echeance = models.ForeignKey("EcheanceMensuelle", on_delete=models.PROTECT, related_name="lignes_paiement")
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["paiement", "echeance"], name="unique_ligne_paiement_echeance")
        ]
        ordering = ["id"]

    def clean(self):
        m = self.montant or Decimal("0.00")
        if m <= 0:
            raise ValidationError({"montant": "Montant ligne invalide."})

    def __str__(self):
        return f"{self.paiement_id} -> {self.echeance_id} ({self.montant})"


# =========================================
# Relances (optionnel)
# =========================================
class RelanceMensuelle(models.Model):
    echeance = models.ForeignKey(EcheanceMensuelle, on_delete=models.CASCADE, related_name="relances")
    canal = models.CharField(max_length=10, choices=[("SMS","SMS"),("AVIS","Avis")], default="AVIS")
    message = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.canal} — {self.echeance} — {self.sent_at:%Y-%m-%d}"


import os
import uuid

def enseignant_photo_path(instance, filename: str) -> str:
    """
    media/enseignants/<matricule_ou_pk>/<uuid>.<ext>
    """
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    ident = instance.matricule or (f"tmp-{instance.pk}" if instance.pk else "tmp")
    new_name = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join("enseignants", ident, new_name)

class Enseignant(AuditBase):
    """
    Enseignant = personne + infos pro.
    Matricule automatique (ENS-000001)
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="enseignant_profile"
    )

    matricule = models.CharField(max_length=20, unique=True, blank=True)
    nom = models.CharField(max_length=80)
    prenom = models.CharField(max_length=80)

    telephone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    specialite = models.CharField(max_length=120, blank=True)

    # ✅ NOUVEAU : photo enseignant
    photo = models.ImageField(
        upload_to=enseignant_photo_path,
        null=True,
        blank=True,
        verbose_name="Photo",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.matricule or '—'} — {self.nom} {self.prenom}"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        # ✅ Générer matricule après création
        if creating and not self.matricule:
            self.matricule = f"ENS-{self.pk:06d}"
            super().save(update_fields=["matricule"])

class Seance(AuditBase):
    """
    Séance de cours (emploi du temps)
    """
    annee = models.ForeignKey(AnneeScolaire, on_delete=models.PROTECT, related_name="seances")
    groupe = models.ForeignKey(Groupe, on_delete=models.PROTECT, related_name="seances")
    enseignant = models.ForeignKey(Enseignant, on_delete=models.PROTECT, related_name="seances")

    JOUR_CHOICES = [
        ("LUN", "Lundi"),
        ("MAR", "Mardi"),
        ("MER", "Mercredi"),
        ("JEU", "Jeudi"),
        ("VEN", "Vendredi"),
        ("SAM", "Samedi"),
    ]
    jour = models.CharField(max_length=3, choices=JOUR_CHOICES)

    heure_debut = models.TimeField()
    heure_fin = models.TimeField()

    matiere = models.CharField(max_length=120, blank=True)
    salle = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["annee__date_debut", "jour", "heure_debut"]
        constraints = [
            # ✅ un groupe ne peut pas avoir 2 séances identiques même créneau
            models.UniqueConstraint(
                fields=["annee", "groupe", "jour", "heure_debut", "heure_fin"],
                name="unique_seance_groupe_creneau",
            )
        ]

    def __str__(self):
        return f"{self.annee.nom} {self.groupe.nom} {self.jour} {self.heure_debut}-{self.heure_fin}"
    @property
    def duree_minutes(self) -> int:
        """
        Calcule la durée en minutes à partir de heure_debut/heure_fin.
        Chez toi: 1h ou 2h max => ça marche parfaitement.
        """
        dt0 = datetime.combine(date_cls.today(), self.heure_debut)
        dt1 = datetime.combine(date_cls.today(), self.heure_fin)
        minutes = int((dt1 - dt0).total_seconds() // 60)
        return max(minutes, 0)
  
    
class AbsenceProf(AuditBase):
    """
    Absence prof liée à une séance + une date réelle (occurrence).
    Exemple: Seance = MAR 10:00-12:00, date = 2026-01-13 => absent ce jour-là.
    """
    annee = models.ForeignKey(AnneeScolaire, on_delete=models.PROTECT, related_name="absences_profs")
    enseignant = models.ForeignKey(Enseignant, on_delete=models.PROTECT, related_name="absences_profs")
    seance = models.ForeignKey(Seance, on_delete=models.PROTECT, related_name="absences_profs")

    date = models.DateField()  # ✅ occurrence réelle dans le calendrier
    minutes_perdues = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date", "seance__heure_debut"]
        constraints = [
            # ✅ une seule absence pour la même séance à la même date
            models.UniqueConstraint(fields=["seance", "date"], name="unique_absence_prof_seance_date"),
        ]

    def clean(self):
        # cohérence annee
        if self.seance_id and self.annee_id and self.seance.annee_id != self.annee_id:
            raise ValidationError("La séance ne correspond pas à la même année scolaire.")

        # cohérence enseignant
        if self.seance_id and self.enseignant_id and self.seance.enseignant_id != self.enseignant_id:
            raise ValidationError("Cette séance n'appartient pas à cet enseignant.")

        # date dans l'année scolaire
        if self.annee_id and self.date:
            if not (self.annee.date_debut <= self.date <= self.annee.date_fin):
                raise ValidationError("La date est hors de l'année scolaire.")

        # date doit matcher le jour de la séance
        if self.seance_id and self.date:
            # mapping python weekday: LUN=0 ... DIM=6
            map_jour = {"LUN": 0, "MAR": 1, "MER": 2, "JEU": 3, "VEN": 4, "SAM": 5}
            if self.seance.jour in map_jour:
                if self.date.weekday() != map_jour[self.seance.jour]:
                    raise ValidationError("La date ne correspond pas au jour de la séance (LUN/MAR/...).")

    def save(self, *args, **kwargs):
        # auto minutes = durée de la séance (absence full)
        if self.seance_id and (not self.minutes_perdues or self.minutes_perdues == 0):
            self.minutes_perdues = self.seance.duree_minutes
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.enseignant} absent {self.date} ({self.seance})"
    
       
class Absence(AuditBase):
    """
    Absence / Retard d'un élève, éventuellement liée à une séance.
    """
    annee = models.ForeignKey(AnneeScolaire, on_delete=models.PROTECT, related_name="absences")
    eleve = models.ForeignKey(Eleve, on_delete=models.PROTECT, related_name="absences")
    groupe = models.ForeignKey(Groupe, on_delete=models.PROTECT, related_name="absences")

    date = models.DateField()
    seance = models.ForeignKey(Seance, on_delete=models.PROTECT, null=True, blank=True, related_name="absences")

    TYPE_CHOICES = [
        ("ABS", "Absence"),
        ("RET", "Retard"),
    ]
    type = models.CharField(max_length=3, choices=TYPE_CHOICES, default="ABS")

    justifie = models.BooleanField(default=False)
    motif = models.CharField(max_length=255, blank=True)

   

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["eleve", "date", "seance"],
                name="unique_absence_eleve_date_seance",
            )
        ]

    def __str__(self):
        return f"{self.eleve.matricule} {self.date} {self.get_type_display()}"


class Parent(AuditBase):
    """
    Parent / Tuteur légal.
    Liaison vers un compte User (optionnel) pour permettre la connexion.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_profile"
    )

    nom = models.CharField(max_length=80)
    prenom = models.CharField(max_length=80)

    telephone = models.CharField(max_length=30, blank=True)
    telephone_norm = models.CharField(max_length=20, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    adresse = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom", "prenom"]

    def __str__(self):
        if self.user:
            return f"{self.nom} {self.prenom} ({self.user.username})"
        return f"{self.nom} {self.prenom}"


class ParentEleve(AuditBase):
    """
    Table pivot Parent <-> Élève
    Permet type de lien (Père, Mère, Tuteur...)
    """
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name="liens")
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="liens_parents")

    LIEN_CHOICES = [
        ("PERE", "Père"),
        ("MERE", "Mère"),
        ("TUTEUR", "Tuteur"),
        ("AUTRE", "Autre"),
    ]
    lien = models.CharField(max_length=10, choices=LIEN_CHOICES, default="PERE")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["parent", "eleve"], name="unique_parent_eleve")
        ]

    def __str__(self):
        return f"{self.parent} -> {self.eleve} ({self.get_lien_display()})"


class Matiere(AuditBase):
    """
    Matière enseignée (Maths, Français, Physique…)
    - liée à plusieurs niveaux
    - liée à plusieurs enseignants
    """
    nom = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=20, unique=True)
    coefficient = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    is_active = models.BooleanField(default=True)

    # ✅ Matière -> plusieurs niveaux
    niveaux = models.ManyToManyField(
        "Niveau",
        related_name="matieres",
        blank=True
    )

    # ✅ Matière -> plusieurs enseignants (et inversement)
    enseignants = models.ManyToManyField(
        "Enseignant",
        related_name="matieres",
        blank=True
    )

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


# =========================
# Périodes = Semestres (S1 / S2)
# =========================


class Periode(AuditBase):
    """
    Période scolaire = Semestre
    Règle: chaque année scolaire doit avoir exactement 2 semestres:
      - ordre=1 => Semestre 1
      - ordre=2 => Semestre 2
    """

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name="periodes"   # tu peux laisser "periodes" pour compatibilité
    )

    ordre = models.PositiveSmallIntegerField(
        choices=[(1, "Semestre 1"), (2, "Semestre 2")]
    )

    # nom auto (pas modifiable)
    nom = models.CharField(max_length=50, editable=False)

    # optionnel mais utile (bulletins/exports)
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["annee__date_debut", "ordre"]
        constraints = [
            # ✅ une seule ligne (annee, ordre) => empêche 2 S1 ou 2 S2
            models.UniqueConstraint(fields=["annee", "ordre"], name="unique_semestre_par_annee_ordre"),
            # ✅ sécurité: empêche doublon nom sur la même année
            models.UniqueConstraint(fields=["annee", "nom"], name="unique_semestre_par_annee_nom"),
        ]

    def save(self, *args, **kwargs):
        # ✅ nom auto
        self.nom = "Semestre 1" if self.ordre == 1 else "Semestre 2"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} — {self.annee.nom}"
    

from decimal import Decimal
from datetime import date as date_cls
from django.db import models
from django.utils import timezone

def first_day(d: date_cls) -> date_cls:
    return date_cls(d.year, d.month, 1)

def months_between(start: date_cls, current: date_cls) -> int:
    """Nombre de mois entre start (1er du mois) et current (1er du mois)."""
    return (current.year - start.year) * 12 + (current.month - start.month)





    
# =========================
# Auto-création des semestres (S1/S2) par année scolaire
# =========================

def ensure_two_semestres(annee: "AnneeScolaire"):
    """
    Garantie : chaque année a 2 semestres (S1 & S2).
    Création si manquants.
    """

    # Semestre 1
    Periode.objects.get_or_create(
        annee=annee,
        ordre=1,
        defaults={
            "date_debut": annee.date_debut,
            "date_fin": None,
        }
    )

    # Semestre 2
    Periode.objects.get_or_create(
        annee=annee,
        ordre=2,
        defaults={
            "date_debut": None,
            "date_fin": annee.date_fin,
        }
    )



class Evaluation(AuditBase):
    """
    Contrôle / Devoir / Examen
    """
    TYPE_CHOICES = [
        ("CC", "Contrôle continu"),
        ("DEV", "Devoir"),
        ("EXAM", "Examen"),
    ]

    titre = models.CharField(max_length=100)

    matiere = models.ForeignKey("Matiere", on_delete=models.PROTECT)
    enseignant = models.ForeignKey("Enseignant", on_delete=models.PROTECT, null=True, blank=True)

    periode = models.ForeignKey("Periode", on_delete=models.CASCADE)
    groupe = models.ForeignKey("Groupe", on_delete=models.CASCADE)

    coefficient = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="CC")
    date = models.DateField()
    note_max = models.PositiveSmallIntegerField(default=20)

    class Meta:
        ordering = ["-date", "titre"]
        constraints = [
            # ✅ Anti-doublon (tu peux l’assouplir plus tard si tu veux CTRL1/CTRL2)
            models.UniqueConstraint(
                fields=["periode", "groupe", "matiere", "type", "date"],
                name="unique_eval_periode_groupe_matiere_type_date"
            ),
        ]

    def clean(self):
        """
        ✅ Règles AZ:
        1) Matière doit appartenir au niveau du groupe
        2) Période doit appartenir à la même année que le groupe
        """
        if self.groupe_id and self.matiere_id:
            niveau = getattr(self.groupe, "niveau", None)
            if niveau and not self.matiere.niveaux.filter(id=niveau.id).exists():
                raise ValidationError({"matiere": f"Matière invalide pour le niveau '{niveau.nom}'."})

        if self.groupe_id and self.periode_id:
            if self.groupe.annee_id != self.periode.annee_id:
                raise ValidationError({"periode": "Cette période n’appartient pas à l’année du groupe."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titre} — {self.matiere.nom}"

class Note(AuditBase):
    """
    Note d’un élève pour une évaluation
    """
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="notes")
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)

    valeur = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ("evaluation", "eleve")

    def __str__(self):
        return f"{self.eleve.matricule} — {self.valeur}"
    
    
class ProfGroupe(AuditBase):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "groupe"], name="unique_user_groupe")
        ]


# =========================
# E1.5 — Affectation Enseignant <-> Groupe (par année)
# =========================

class EnseignantGroupe(AuditBase):
    annee = models.ForeignKey(AnneeScolaire, on_delete=models.PROTECT, related_name="affectations_enseignants")
    enseignant = models.ForeignKey(Enseignant, on_delete=models.CASCADE, related_name="affectations_groupes")
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE, related_name="affectations_enseignants")

    # ✅ matière devient optionnelle
    matiere_fk = models.ForeignKey(
        "Matiere",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="affectations_enseignants_groupes"
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # ✅ un prof ne peut pas avoir 2 fois le même groupe pour la même année (sans matière)
            models.UniqueConstraint(
                fields=["annee", "enseignant", "groupe"],
                condition=Q(matiere_fk__isnull=True),
                name="unique_enseignant_groupe_annee_sans_matiere"
            ),
            # ✅ avec matière: unique
            models.UniqueConstraint(
                fields=["annee", "enseignant", "groupe", "matiere_fk"],
                condition=Q(matiere_fk__isnull=False),
                name="unique_enseignant_groupe_annee_matiere"
            ),
        ]

    def clean(self):
        if self.groupe_id and self.annee_id and self.groupe.annee_id != self.annee_id:
            raise ValidationError("⚠️ L'année choisie doit correspondre à l'année du groupe.")

        # ✅ vérifier la matière seulement si elle est fournie
        if self.groupe_id and self.matiere_fk_id:
            if not self.matiere_fk.niveaux.filter(id=self.groupe.niveau_id).exists():
                raise ValidationError("⚠️ Cette matière n'appartient pas au niveau du groupe.")

    def save(self, *args, **kwargs):
        if self.groupe_id and not self.annee_id:
            self.annee_id = self.groupe.annee_id
        self.full_clean()
        super().save(*args, **kwargs)

# =========================
# G — Recouvrement
# =========================

class Recouvrement(AuditBase):
    """
    Dossier de recouvrement (lié à une inscription impayée).
    Règle: 1 seul dossier par inscription (OneToOne).
    """

    STATUT_CHOICES = [
        ("EN_COURS", "En cours"),
        ("EN_RELANCE", "En relance"),
        ("REGLE", "Réglé"),
        ("CLOTURE", "Clôturé"),
    ]

    inscription = models.OneToOneField(
        "Inscription",
        on_delete=models.PROTECT,
        related_name="recouvrement"
    )

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="EN_COURS")
    date_ouverture = models.DateField(default=timezone.now)
    date_cloture = models.DateField(null=True, blank=True)

    note_interne = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date_ouverture", "-id"]

    def __str__(self):
        return f"Recouvrement {self.inscription.eleve.matricule} — {self.inscription.annee.nom}"

    @property
    def total_paye(self):
        s = self.inscription.paiements.aggregate(
            s=Coalesce(
                Sum("montant"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )["s"]
        return s or Decimal("0.00")

    @property
    def solde(self):
        total = self.inscription.montant_total or Decimal("0.00")
        return total - (self.total_paye or Decimal("0.00"))

    def refresh_statut_si_regle(self, save=True):
        """
        Si solde <= 0 : on passe automatiquement à REGLE.
        """
        if self.statut not in ["CLOTURE"] and self.solde <= Decimal("0.00"):
            self.statut = "REGLE"
            if not self.date_cloture:
                self.date_cloture = timezone.now().date()
            if save:
                self.save(update_fields=["statut", "date_cloture", "updated_at", "updated_by"])


class Relance(AuditBase):
    """
    Relance associée à un dossier de recouvrement.
    """
    TYPE_CHOICES = [
        ("SMS", "SMS"),
        ("APPEL", "Appel"),
        ("AVIS", "Avis"),
        ("EMAIL", "Email"),
        ("AUTRE", "Autre"),
    ]

    recouvrement = models.ForeignKey(
        Recouvrement,
        on_delete=models.CASCADE,
        related_name="relances"
    )

    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="SMS")
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Relance {self.get_type_display()} — {self.recouvrement.inscription.eleve.matricule}"

# =========================
# U1 — Mot de passe temporaire (export)
# =========================
class TempPassword(AuditBase):
    """
    Stocke le dernier mot de passe temporaire généré pour un utilisateur.
    Utilisé uniquement pour export CSV (usage admin).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="temp_password"
    )
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TempPassword({self.user.username})"


# =========================
# I — Communication (Avis + SMS)
# =========================

# core/models.py

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models

class Avis(AuditBase):
    CIBLE_CHOICES = [
        ("TOUS", "Tous"),
        ("DEGRE", "Degré"),
        ("NIVEAU", "Niveau"),
        ("GROUPE", "Groupe"),
        ("ELEVE", "Élève"),
    ]

    titre = models.CharField(max_length=120)
    contenu = models.TextField()
    cible_type = models.CharField(max_length=10, choices=CIBLE_CHOICES, default="TOUS")

    degre = models.ForeignKey("Degre", on_delete=models.PROTECT, null=True, blank=True, related_name="avis")
    niveau = models.ForeignKey("Niveau", on_delete=models.PROTECT, null=True, blank=True, related_name="avis")
    groupe = models.ForeignKey("Groupe", on_delete=models.PROTECT, null=True, blank=True, related_name="avis")
    eleve = models.ForeignKey("Eleve", on_delete=models.PROTECT, null=True, blank=True, related_name="avis")

    visible_parent = models.BooleanField(default=True)
    date_publication = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date_publication", "-id"]

    def __str__(self):
        return f"Avis: {self.titre}"

    def clean(self):
        """
        Règles (FINAL):
        - TOUS   => rien
        - DEGRE  => degre seul
        - NIVEAU => niveau seul
        - GROUPE => niveau + groupe
        - ELEVE  => niveau + groupe + eleve
        """
        cible = self.cible_type

        has_degre  = bool(self.degre_id)
        has_niveau = bool(self.niveau_id)
        has_groupe = bool(self.groupe_id)
        has_eleve  = bool(self.eleve_id)

        # ---- TOUS ----
        if cible == "TOUS":
            if any([has_degre, has_niveau, has_groupe, has_eleve]):
                raise ValidationError("Pour la cible 'Tous', ne remplis aucun champ Degré/Niveau/Groupe/Élève.")
            return

        # ---- DEGRE ----
        if cible == "DEGRE":
            if not has_degre:
                raise ValidationError({"degre": "Ce champ est obligatoire pour ce type de cible."})
            if any([has_niveau, has_groupe, has_eleve]):
                raise ValidationError("Ciblage Degré → ne sélectionne que le degré.")
            return

        # ---- NIVEAU ----
        if cible == "NIVEAU":
            if not has_niveau:
                raise ValidationError({"niveau": "Ce champ est obligatoire pour ce type de cible."})
            if any([has_degre, has_groupe, has_eleve]):
                raise ValidationError("Ciblage Niveau → ne sélectionne que le niveau.")
            return

        # ---- GROUPE (niveau + groupe) ----
        if cible == "GROUPE":
            if not has_niveau:
                raise ValidationError({"niveau": "Le niveau est obligatoire pour choisir un groupe."})
            if not has_groupe:
                raise ValidationError({"groupe": "Le groupe est obligatoire."})
            if any([has_degre, has_eleve]):
                raise ValidationError("Ciblage Groupe → ne sélectionne que Niveau + Groupe.")

            # cohérence groupe/niveau
            if self.groupe_id and self.niveau_id and getattr(self.groupe, "niveau_id", None) != self.niveau_id:
                raise ValidationError({"groupe": "Ce groupe ne correspond pas au niveau sélectionné."})
            return

        # ---- ELEVE (niveau + groupe + eleve) ----
        if cible == "ELEVE":
            if not has_niveau:
                raise ValidationError({"niveau": "Le niveau est obligatoire."})
            if not has_groupe:
                raise ValidationError({"groupe": "Le groupe est obligatoire."})
            if not has_eleve:
                raise ValidationError({"eleve": "L’élève est obligatoire."})
            if has_degre:
                raise ValidationError("Ciblage Élève → ne sélectionne pas de degré.")

            # cohérence groupe/niveau
            if self.groupe_id and self.niveau_id and getattr(self.groupe, "niveau_id", None) != self.niveau_id:
                raise ValidationError({"groupe": "Ce groupe ne correspond pas au niveau sélectionné."})

            # sécurité: eleve appartient au groupe via Inscription
            from .models import Inscription  # adapte le chemin si besoin
            ok = Inscription.objects.filter(eleve_id=self.eleve_id, groupe_id=self.groupe_id).exists()
            if not ok:
                raise ValidationError({"eleve": "Cet élève n’appartient pas au groupe sélectionné."})
            return

        raise ValidationError("Type de cible invalide.")

class SmsHistorique(AuditBase):
    """
    Historique SMS envoyés (réels).
    On enregistre chaque destinataire comme 1 ligne (simple & fiable).
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SENT", "Sent"),
        ("FAILED", "Failed"),
    ]

    # Optionnel: si le SMS vient d'un avis
    avis = models.ForeignKey("Avis", on_delete=models.SET_NULL, null=True, blank=True, related_name="sms")

    parent = models.ForeignKey("Parent", on_delete=models.SET_NULL, null=True, blank=True, related_name="sms")
    telephone = models.CharField(max_length=30)  # numéro final utilisé
    message = models.TextField()

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    provider = models.CharField(max_length=50, default="twilio")  # ou autre
    provider_message_id = models.CharField(max_length=120, blank=True)
    error_message = models.TextField(blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"SMS {self.status} -> {self.telephone}"


from decimal import Decimal
from core.models import EcheanceMensuelle

def _allocate_to_echeances(inscription: Inscription, montant: Decimal, preferred=None):
    """
    Affecte un montant aux échéances mensuelles (du plus ancien impayé vers le plus récent).
    ✅ Source des échéances = (eleve, annee)
    """
    restant = montant or Decimal("0.00")
    first_used = None

    # 1) si on cible une échéance précise
    if preferred and restant > 0:
        ech = preferred
        r = ech.reste
        if r > 0:
            take = r if restant >= r else restant
            ech.montant_paye = (ech.montant_paye or Decimal("0.00")) + take
            ech.refresh_statut(save=False)
            ech.save(update_fields=["montant_paye", "statut"])
            restant -= take
            first_used = first_used or ech

    # 2) puis compléter sur les plus anciennes impayées
    if restant > 0:
        echeances = (EcheanceMensuelle.objects
                     .filter(eleve_id=inscription.eleve_id, annee_id=inscription.annee_id)
                     .order_by("date_echeance", "mois_index", "id"))

        for ech in echeances:
            if restant <= 0:
                break
            r = ech.reste
            if r <= 0:
                continue

            take = r if restant >= r else restant
            ech.montant_paye = (ech.montant_paye or Decimal("0.00")) + take
            ech.refresh_statut(save=False)
            ech.save(update_fields=["montant_paye", "statut"])
            restant -= take
            first_used = first_used or ech

    return first_used, restant


from django.db import transaction
from django.db.models.deletion import ProtectedError

@transaction.atomic
def hard_delete_eleve(eleve):
    # 1) supprime ce qui pointe vers Eleve directement
    eleve.liens_parents.all().delete()     # ParentEleve (CASCADE normalement, mais safe)
    eleve.absences.all().delete()          # Absence (si PROTECT, on supprime avant)

    # Notes éventuelles
    from core.models import Note
    Note.objects.filter(eleve=eleve).delete()

    # 2) inscriptions + tout ce qui dépend
    for insc in eleve.inscriptions.all():
        # recouvrement + relances
        if hasattr(insc, "recouvrement"):
            insc.recouvrement.relances.all().delete()
            insc.recouvrement.delete()

        # paiements (PROTECT => delete avant)
        insc.paiements.all().delete()

        # échéances (paiements.echeance est PROTECT => déjà supprimés au-dessus)
        insc.echeances.all().delete()

        # relances mensuelles (si tu les utilises)
        RelanceMensuelle.objects.filter(echeance__eleve=eleve, echeance__annee=insc.annee).delete()

        # supprimer l’inscription
        insc.delete()

    # 3) enfin l'élève
    eleve.delete()




# =========================
# P — PROFESSEURS 
# =========================


# core/models.py
from django.db import models
from django.conf import settings

# ⚠️ Assure-toi que tu as déjà ces models existants :
# - AnneeScolaire, Groupe, Matiere

class CahierTexte(models.Model):
    """
    Cahier de texte (Prof) : résumé + devoir, lié à groupe/matière/date.
    """
    annee = models.ForeignKey("core.AnneeScolaire", on_delete=models.PROTECT, related_name="cahiers_textes")
    groupe = models.ForeignKey("core.Groupe", on_delete=models.PROTECT, related_name="cahiers_textes")
    matiere = models.ForeignKey("core.Matiere", on_delete=models.PROTECT, related_name="cahiers_textes")

    prof = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cahiers_textes")

    date = models.DateField()
    titre = models.CharField(max_length=160, blank=True, default="")
    contenu = models.TextField()
    devoir = models.TextField(blank=True, default="")

    piece_jointe = models.FileField(upload_to="prof/cahier/", blank=True, null=True)

    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["annee", "groupe", "matiere", "date"]),
            models.Index(fields=["prof", "date"]),
        ]

    def __str__(self):
        return f"CahierTexte {self.groupe} {self.matiere} {self.date}"


class CoursResumePDF(models.Model):
    """
    Dépôt PDF (Prof) : résumé de cours (PDF), séparé du cahier de texte (Option A).
    """
    annee = models.ForeignKey("core.AnneeScolaire", on_delete=models.PROTECT, related_name="resumes_pdf")
    groupe = models.ForeignKey("core.Groupe", on_delete=models.PROTECT, related_name="resumes_pdf")
    matiere = models.ForeignKey("core.Matiere", on_delete=models.PROTECT, related_name="resumes_pdf")

    prof = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="resumes_pdf")

    date = models.DateField()
    titre = models.CharField(max_length=200)

    fichier = models.FileField(upload_to="prof/resumes_pdf/")
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["annee", "groupe", "matiere", "date"]),
            models.Index(fields=["prof", "date"]),
        ]

    def __str__(self):
        return f"ResumePDF {self.groupe} {self.matiere} {self.date}"






# =========================
# Transaction (nouveau système paiement)
# =========================
# core/models.py
from decimal import Decimal
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.db import transaction as dbtx


class TransactionFinance(AuditBase):
    parent = models.ForeignKey(
        "Parent",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="transactions"
    )
    inscription = models.ForeignKey("Inscription", on_delete=models.PROTECT, related_name="transactions")
    date_transaction = models.DateTimeField(auto_now_add=True)
    receipt_seq = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    TYPE_CHOICES = [
        ("INSCRIPTION", "Inscription"),
        ("SCOLARITE", "Scolarité"),
        ("TRANSPORT", "Transport"),
        ("PACK", "Pack"),
    ]
    type_transaction = models.CharField(max_length=20, choices=TYPE_CHOICES, default="SCOLARITE")

    montant_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    MODE_CHOICES = [
        ("ESPECES", "Espèces"),
        ("VIREMENT", "Virement"),
        ("CHEQUE", "Chèque"),
    ]
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="ESPECES")

    reference = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=255, blank=True)
    batch_token = models.CharField(max_length=36, blank=True, db_index=True)

    class Meta:
        ordering = ["-date_transaction", "-id"]

    def clean(self):
        m = self.montant_total or Decimal("0.00")
        if m < Decimal("0.00"):
            raise ValidationError({"montant_total": "Montant total invalide (négatif)."})

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        # ✅ Référence auto UNE SEULE FOIS
        if creating and not (self.reference or "").strip():
            from core.models import RecuCounter  # même app, ok
            annee_id = self.inscription.annee_id

            with transaction.atomic():
                n = RecuCounter.next_for_annee(annee_id)

                # ✅ année : tu peux prendre date_debut.year OU datetime.now().year
                year = self.inscription.annee.date_debut.year
                self.reference = f"AZ-PAY-{year}-{n}"
                super().save(update_fields=["reference"])

class TransactionLigne(models.Model):
    transaction = models.ForeignKey("TransactionFinance", on_delete=models.CASCADE, related_name="lignes")

    echeance = models.ForeignKey(
        "EcheanceMensuelle",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="transactions_lignes"
    )

    echeance_transport = models.ForeignKey(
        "EcheanceTransportMensuelle",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="transactions_lignes_transport"
    )

    libelle = models.CharField(max_length=120, blank=True)

    # ✅ 0 autorisé
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["transaction", "echeance"],
                condition=Q(echeance__isnull=False),
                name="unique_tx_sco_echeance"
            ),
            models.UniqueConstraint(
                fields=["transaction", "echeance_transport"],
                condition=Q(echeance_transport__isnull=False),
                name="unique_tx_tr_echeance"
            ),
            models.CheckConstraint(
                check=~(Q(echeance__isnull=False) & Q(echeance_transport__isnull=False)),
                name="ck_txligne_not_both_echeances"
            ),
        ]

    def clean(self):
        # ✅ autorise 0 (mois gratuit)
        m = self.montant or Decimal("0.00")
        if m < Decimal("0.00"):
            raise ValidationError({"montant": "Montant ligne invalide (négatif)."})

from django.db import models
from django.core.validators import FileExtensionValidator

class TransactionJustificatif(models.Model):
    tx = models.ForeignKey(
        "TransactionFinance",
        on_delete=models.CASCADE,
        related_name="justificatifs"
    )

    # optionnel: catégoriser (reçu virement, scan chèque, etc.)
    TYPE_CHOICES = [
        ("RECU", "Reçu / Bordereau"),
        ("CHEQUE", "Chèque (scan)"),
        ("VIREMENT", "Virement (preuve)"),
        ("AUTRE", "Autre"),
    ]
    type_piece = models.CharField(max_length=20, choices=TYPE_CHOICES, default="AUTRE")

    fichier = models.FileField(
        upload_to="finance/transactions/justificatifs/%Y/%m/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png", "webp"])]
    )

    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return f"Justif TX#{self.tx_id} - {self.original_name or self.fichier.name}"


from django.db.models import F

class RecuCounter(models.Model):
    annee = models.OneToOneField("AnneeScolaire", on_delete=models.CASCADE, related_name="recu_counter")
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.annee.nom} -> {self.last_number}"

    @staticmethod
    @transaction.atomic
    def next_for_annee(annee_id: int) -> int:
        obj, _ = RecuCounter.objects.select_for_update().get_or_create(
            annee_id=annee_id,
            defaults={"last_number": 0},
        )
        obj.last_number = F("last_number") + 1
        obj.save(update_fields=["last_number"])
        obj.refresh_from_db(fields=["last_number"])
        return int(obj.last_number)

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError

class EleveTransport(models.Model):
    """
    Transport optionnel par élève.
    - enabled=False => pas d'échéances transport.
    - tarif_mensuel => prix du transport pour cet élève (modifiable / réduction).
    """
    eleve = models.OneToOneField("Eleve", on_delete=models.CASCADE, related_name="transport")
    enabled = models.BooleanField(default=False)
    tarif_mensuel = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    def clean(self):
        if self.enabled and (self.tarif_mensuel or Decimal("0.00")) <= Decimal("0.00"):
            raise ValidationError({"tarif_mensuel": "Tarif transport mensuel invalide."})

    def __str__(self):
        return f"Transport {self.eleve_id} enabled={self.enabled} tarif={self.tarif_mensuel}"

class EcheanceTransportMensuelle(models.Model):
    eleve = models.ForeignKey("Eleve", on_delete=models.CASCADE, related_name="echeances_transport")
    annee = models.ForeignKey("AnneeScolaire", on_delete=models.PROTECT, related_name="echeances_transport")

    # snapshot groupe (pour filtres, impayés, etc.)
    groupe = models.ForeignKey("Groupe", on_delete=models.PROTECT, null=True, blank=True, related_name="echeances_transport")

    mois_index = models.PositiveSmallIntegerField()  # 1..10 (Sep..Jun)
    date_echeance = models.DateField()

    montant_du = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    STATUT_CHOICES = [("A_PAYER", "À payer"), ("PARTIEL", "Partiel"), ("PAYE", "Payé")]
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default="A_PAYER")

    MOIS_FR = {
        1: "Septembre", 2: "Octobre", 3: "Novembre", 4: "Décembre", 5: "Janvier",
        6: "Février", 7: "Mars", 8: "Avril", 9: "Mai", 10: "Juin",
    }

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["eleve", "annee", "mois_index"], name="unique_transport_eleve_annee_mois")
        ]
        ordering = ["mois_index", "id"]

    @property
    def mois_nom(self) -> str:
        return self.MOIS_FR.get(int(self.mois_index or 0), f"M{self.mois_index}")

    @property
    def reste(self) -> Decimal:
        du = self.montant_du or Decimal("0.00")
        paye = self.montant_paye or Decimal("0.00")
        return max(du - paye, Decimal("0.00"))

    def refresh_statut(self, save=True):
        paye = self.montant_paye or Decimal("0.00")
        du = self.montant_du or Decimal("0.00")

        if paye <= Decimal("0.00"):
            self.statut = "A_PAYER"
        elif paye < du:
            self.statut = "PARTIEL"
        else:
            self.statut = "PAYE"

        if save:
            self.save(update_fields=["statut"])

    def clean(self):
        if (self.montant_du or Decimal("0.00")) < Decimal("0.00"):
            raise ValidationError({"montant_du": "Montant dû invalide."})

    def __str__(self):
        return f"TR {self.eleve_id} {self.annee_id} {self.mois_nom} reste={self.reste}"


from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction as db_transaction

class RemboursementFinance(models.Model):
    transaction = models.ForeignKey("TransactionFinance", on_delete=models.PROTECT, related_name="remboursements")
    created_at = models.DateTimeField(auto_now_add=True)

    montant = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_annulation = models.BooleanField(default=False)

    MODE_CHOICES = [
        ("ESPECES", "Espèces"),
        ("VIREMENT", "Virement"),
        ("CHEQUE", "Chèque"),
    ]
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="ESPECES")
    raison = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="remboursements_finance_crees"
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def clean(self):
        if not self.transaction_id:
            raise ValidationError({"transaction": "Transaction obligatoire."})

        total = self.transaction.montant_total or Decimal("0.00")
        m = self.montant if self.montant is not None else Decimal("0.00")

        if m < Decimal("0.00"):
            raise ValidationError({"montant": "Montant invalide (négatif interdit)."})

        # =========================
        # ✅ CAS 1 : Transaction = 0  => Annulation logique
        # =========================
        if total == Decimal("0.00"):
            deja_annulee = self.transaction.remboursements.filter(is_annulation=True).exclude(pk=self.pk).exists()
            if deja_annulee:
                raise ValidationError("Cette transaction à 0 est déjà annulée.")

            # force montant=0 + annulation
            if m != Decimal("0.00"):
                raise ValidationError({"montant": "Transaction à 0 => le montant doit rester à 0."})

            self.is_annulation = True
            return


        # =========================
        # ✅ CAS 2 : Transaction > 0 => Remboursement normal (partiel/total)
        # =========================
        if m <= Decimal("0.00"):
            raise ValidationError({"montant": "Montant remboursement invalide (doit être > 0)."})

        deja = self.transaction.remboursements.aggregate(s=models.Sum("montant"))["s"] or Decimal("0.00")
        max_remb = max(total - deja, Decimal("0.00"))

        if m > max_remb:
            raise ValidationError({"montant": f"Trop élevé. Max = {max_remb} MAD."})

        # ✅ pas une annulation
        self.is_annulation = False

    @db_transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.full_clean()
        super().save(*args, **kwargs)

        if not is_new:
            return

        # ✅ Annulation logique (tx=0) => aucune ligne, aucune modif sur échéances
        if self.is_annulation:
            return

        # ✅ remboursement normal => ton flow (lignes + décrément payé)
        tx = self.transaction
        remaining = self.montant or Decimal("0.00")
        lignes = tx.lignes.select_related("echeance", "echeance_transport").order_by("-id")

        for ln in lignes:
            if remaining <= Decimal("0.00"):
                break

            ln_amount = ln.montant or Decimal("0.00")
            if ln_amount <= Decimal("0.00"):
                continue

            take = min(ln_amount, remaining)

            RemboursementFinanceLigne.objects.create(
                remboursement=self,
                transaction_ligne=ln,
                echeance=ln.echeance if ln.echeance_id else None,
                echeance_transport=ln.echeance_transport if getattr(ln, "echeance_transport_id", None) else None,
                montant=take
            )

            # 1) INSCRIPTION
            if not ln.echeance_id and not getattr(ln, "echeance_transport_id", None):
                insc = tx.inscription
                insc.frais_inscription_paye = (insc.frais_inscription_paye or Decimal("0.00")) - take
                if insc.frais_inscription_paye < Decimal("0.00"):
                    insc.frais_inscription_paye = Decimal("0.00")
                insc.save(update_fields=["frais_inscription_paye"])

            # 2) SCOLARITE
            elif ln.echeance_id:
                e = ln.echeance
                e.montant_paye = (e.montant_paye or Decimal("0.00")) - take
                if e.montant_paye < Decimal("0.00"):
                    e.montant_paye = Decimal("0.00")
                e.refresh_statut(save=False)
                e.save(update_fields=["montant_paye", "statut"])

            # 3) TRANSPORT
            else:
                et = ln.echeance_transport
                et.montant_paye = (et.montant_paye or Decimal("0.00")) - take
                if et.montant_paye < Decimal("0.00"):
                    et.montant_paye = Decimal("0.00")
                et.refresh_statut(save=False)
                et.save(update_fields=["montant_paye", "statut"])

            remaining -= take



class RemboursementFinanceLigne(models.Model):
    remboursement = models.ForeignKey("RemboursementFinance", on_delete=models.CASCADE, related_name="lignes")
    transaction_ligne = models.ForeignKey("TransactionLigne", on_delete=models.PROTECT, related_name="remboursements_lignes")

    echeance = models.ForeignKey(
        "EcheanceMensuelle",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="remboursements_finance_lignes"
    )
    echeance_transport = models.ForeignKey(
        "EcheanceTransportMensuelle",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="remboursements_finance_lignes"
    )

    montant = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]

    def clean(self):
        m = self.montant or Decimal("0.00")
        if m <= Decimal("0.00"):
            raise ValidationError({"montant": "Montant ligne remboursement invalide."})







# =========================
# H — Dépenses (Niveau 1)
# =========================
from decimal import Decimal
import os
import uuid
from django.core.exceptions import ValidationError

def depense_justificatif_path(instance, filename: str) -> str:
    """
    media/depenses/<annee>/<uuid>.<ext>
    """
    ext = filename.split(".")[-1].lower() if "." in filename else "pdf"
    annee = getattr(instance.annee, "nom", "annee") if instance.annee_id else "annee"
    new_name = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join("depenses", annee, new_name)


class CategorieDepense(AuditBase):
    """
    Catégorie pour classer les dépenses.
    """
    nom = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "nom"]

    def __str__(self):
        return self.nom


class Depense(AuditBase):
    """
    Dépense (sortie).
    Dépend de: Année scolaire (année active par défaut côté form/view).
    """
    annee = models.ForeignKey(
        "AnneeScolaire",
        on_delete=models.PROTECT,
        related_name="depenses"
    )

    date_depense = models.DateField()
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    categorie = models.ForeignKey(
        "CategorieDepense",
        on_delete=models.PROTECT,
        related_name="depenses"
    )

    libelle = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    justificatif = models.FileField(
        upload_to=depense_justificatif_path,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-date_depense", "-id"]
        indexes = [
            models.Index(fields=["annee", "date_depense"]),
            models.Index(fields=["categorie"]),
        ]

    def clean(self):
        m = self.montant or Decimal("0.00")
        if m <= Decimal("0.00"):
            raise ValidationError({"montant": "Montant dépense invalide (doit être > 0)."})
        if self.categorie_id and not self.categorie.is_active:
            raise ValidationError({"categorie": "Cette catégorie est inactive."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date_depense} — {self.libelle} ({self.montant} MAD)"



from decimal import Decimal
from django.db import models

class Tarification(models.Model):
    nom = models.CharField(max_length=80, unique=True)

    # tarifs par défaut
    sco_mensuel = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tr_mensuel  = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    inscription = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom
