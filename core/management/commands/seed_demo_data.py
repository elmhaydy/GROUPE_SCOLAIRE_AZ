# core/management/commands/seed_demo_data.py
import os
import sys
from decimal import Decimal
from datetime import date, time, timedelta, datetime

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from core.models import (
    AnneeScolaire, Degre, Niveau, Groupe, FraisNiveau,
    Periode, Matiere, Enseignant, EnseignantGroupe,
    Eleve, Inscription, EcheanceMensuelle,
    TransactionFinance, TransactionLigne, Paiement,
    Parent, ParentEleve, Seance, Absence,
    Evaluation, Note, CategorieDepense, Depense
)
from accounts.models import UserSecurityProfile


def set_profile_photo(obj, field_name: str, filename: str):
    """Attache une photo depuis static/img/demo/ vers l'ImageField spécifié."""
    try:
        static_dir = settings.BASE_DIR / "static" / "img" / "demo"
        img_path = static_dir / filename
        if not img_path.exists():
            img_path = settings.BASE_DIR / "media" / "demo_avatars" / filename
        if not img_path.exists():
            return
        current_file = getattr(obj, field_name, None)
        if not current_file or not current_file.name:
            with open(img_path, "rb") as f:
                getattr(obj, field_name).save(filename, File(f), save=True)
    except Exception:
        pass


class Command(BaseCommand):
    help = "Initialise des données de test réalistes complètes pour la démo en 1 clic d'Atlas School ERP."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force la réinitialisation et ré-injection complète des données de démonstration.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("[Atlas School ERP] Initialisation des donnees de demo..."))

        # -------------------------------------------------------------
        # 1. RÔLES & PERMISSIONS
        # -------------------------------------------------------------
        self.stdout.write("--> 1/8 Configuration des roles et groupes utilisateurs...")
        call_command("seed_roles", verbosity=0)

        # Assurer la présence des groupes ELEVE et PARENT
        Group.objects.get_or_create(name="ELEVE")
        Group.objects.get_or_create(name="PARENT")

        # -------------------------------------------------------------
        # 2. ANNÉE SCOLAIRE ACTIVE
        # -------------------------------------------------------------
        self.stdout.write("--> 2/8 Configuration de l'Annee Scolaire active...")
        AnneeScolaire.objects.update(is_active=False)

        annee, _ = AnneeScolaire.objects.update_or_create(
            nom="2025-2026",
            defaults={
                "date_debut": date(2025, 9, 1),
                "date_fin": date(2026, 6, 30),
                "is_active": True,
            }
        )

        # -------------------------------------------------------------
        # 3. STRUCTURE PÉDAGOGIQUE (DEGRÉS, NIVEAUX, CLASSES)
        # -------------------------------------------------------------
        self.stdout.write("--> 3/8 Creation de la structure scolaire (Degres, Niveaux, Classes)...")
        call_command("seed_degres", verbosity=0)

        degre_maternelle = Degre.objects.get(code="MATERNELLE")
        degre_primaire = Degre.objects.get(code="PRIMAIRE")
        degre_college = Degre.objects.get(code="COLLEGE")
        degre_lycee = Degre.objects.get(code="LYCEE")

        # Niveaux
        cp, _ = Niveau.objects.update_or_create(
            degre=degre_primaire, nom="CP",
            defaults={"ordre": 1}
        )
        ce1, _ = Niveau.objects.update_or_create(
            degre=degre_primaire, nom="CE1",
            defaults={"ordre": 2}
        )
        ac1, _ = Niveau.objects.update_or_create(
            degre=degre_college, nom="1ere Annee College",
            defaults={"ordre": 3}
        )
        tc, _ = Niveau.objects.update_or_create(
            degre=degre_lycee, nom="Tronc Commun",
            defaults={"ordre": 4}
        )

        # Tarifs par niveau
        FraisNiveau.objects.update_or_create(
            annee=annee, niveau=cp,
            defaults={"frais_inscription": Decimal("1500.00"), "frais_scolarite_mensuel": Decimal("1200.00")}
        )
        FraisNiveau.objects.update_or_create(
            annee=annee, niveau=ce1,
            defaults={"frais_inscription": Decimal("1500.00"), "frais_scolarite_mensuel": Decimal("1300.00")}
        )
        FraisNiveau.objects.update_or_create(
            annee=annee, niveau=ac1,
            defaults={"frais_inscription": Decimal("1800.00"), "frais_scolarite_mensuel": Decimal("1600.00")}
        )
        FraisNiveau.objects.update_or_create(
            annee=annee, niveau=tc,
            defaults={"frais_inscription": Decimal("2000.00"), "frais_scolarite_mensuel": Decimal("1900.00")}
        )

        # Groupes / Classes
        groupe_cp, _ = Groupe.objects.update_or_create(
            annee=annee, niveau=cp, nom="CP-A",
            defaults={"capacite": 25}
        )
        groupe_ce1, _ = Groupe.objects.update_or_create(
            annee=annee, niveau=ce1, nom="CE1-A",
            defaults={"capacite": 25}
        )
        groupe_1ac, _ = Groupe.objects.update_or_create(
            annee=annee, niveau=ac1, nom="1AC-1",
            defaults={"capacite": 30}
        )
        groupe_tc, _ = Groupe.objects.update_or_create(
            annee=annee, niveau=tc, nom="TC-Sciences",
            defaults={"capacite": 30}
        )

        # Périodes (Semestres 1 et 2)
        s1, _ = Periode.objects.update_or_create(
            annee=annee, ordre=1,
            defaults={
                "date_debut": date(2025, 9, 1),
                "date_fin": date(2026, 1, 31),
            }
        )
        s2, _ = Periode.objects.update_or_create(
            annee=annee, ordre=2,
            defaults={
                "date_debut": date(2026, 2, 1),
                "date_fin": date(2026, 6, 30),
            }
        )

        # Matières
        mat_math, _ = Matiere.objects.update_or_create(
            code="MATH",
            defaults={"nom": "Mathematiques", "coefficient": Decimal("4.00"), "is_active": True}
        )
        mat_fr, _ = Matiere.objects.update_or_create(
            code="FR",
            defaults={"nom": "Francais", "coefficient": Decimal("4.00"), "is_active": True}
        )
        mat_ar, _ = Matiere.objects.update_or_create(
            code="AR",
            defaults={"nom": "Langue Arabe", "coefficient": Decimal("3.00"), "is_active": True}
        )
        mat_svt, _ = Matiere.objects.update_or_create(
            code="SVT",
            defaults={"nom": "Sciences de la Vie et de la Terre", "coefficient": Decimal("3.00"), "is_active": True}
        )
        mat_hg, _ = Matiere.objects.update_or_create(
            code="HG",
            defaults={"nom": "Histoire-Geographie", "coefficient": Decimal("2.00"), "is_active": True}
        )
        mat_ang, _ = Matiere.objects.update_or_create(
            code="ANG",
            defaults={"nom": "Anglais", "coefficient": Decimal("2.00"), "is_active": True}
        )

        # Rattachement des matières aux niveaux
        for mat in [mat_math, mat_fr, mat_ar, mat_svt, mat_hg, mat_ang]:
            mat.niveaux.add(cp, ce1, ac1, tc)

        # Catégories de Dépenses
        cat_fournitures, _ = CategorieDepense.objects.update_or_create(
            nom="Fournitures scolaires & Pedagogie",
            defaults={"is_active": True}
        )
        cat_energie, _ = CategorieDepense.objects.update_or_create(
            nom="Energie, Eau & Telecoms",
            defaults={"is_active": True}
        )
        cat_maintenance, _ = CategorieDepense.objects.update_or_create(
            nom="Maintenance & Entretien",
            defaults={"is_active": True}
        )
        cat_salaires, _ = CategorieDepense.objects.update_or_create(
            nom="Salaires & Primes du Personnel",
            defaults={"is_active": True}
        )

        # Dépenses réalistes
        Depense.objects.update_or_create(
            annee=annee, libelle="Achat ramettes papier et manuels scolaires",
            defaults={"date_depense": date(2025, 9, 10), "montant": Decimal("4800.00"), "categorie": cat_fournitures}
        )
        Depense.objects.update_or_create(
            annee=annee, libelle="Facture electricite & eau Septembre",
            defaults={"date_depense": date(2025, 10, 2), "montant": Decimal("3150.00"), "categorie": cat_energie}
        )
        Depense.objects.update_or_create(
            annee=annee, libelle="Revision climatisation et extincteurs",
            defaults={"date_depense": date(2025, 10, 15), "montant": Decimal("2600.00"), "categorie": cat_maintenance}
        )

        # Règles de relance automatiques
        call_command("relance_init_defaults", verbosity=0)

        # -------------------------------------------------------------
        # 4. COMPTES UTILISATEURS DÉMO PRÊTS À L'EMPLOI
        # -------------------------------------------------------------
        self.stdout.write("--> 4/8 Creation des 4 comptes de demonstration (Mot de passe: Demo2026!*)...")
        DEMO_PASSWORD = "Demo2026!*"
        User = get_user_model()

        def create_clean_user(username, email, first_name, last_name, is_staff=False, is_superuser=False, groups=None):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                    "is_active": True,
                }
            )
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.is_active = True
            user.set_password(DEMO_PASSWORD)
            user.save()

            if groups:
                for grp_name in groups:
                    grp, _ = Group.objects.get_or_create(name=grp_name)
                    user.groups.add(grp)

            # Déverrouiller et empêcher le forçage de changement de mot de passe en démo
            sec_prof = UserSecurityProfile.get_for(user)
            sec_prof.must_change_password = False
            sec_prof.failed_login_attempts = 0
            sec_prof.locked_until = None
            sec_prof.last_failed_login = None
            sec_prof.save()

            return user

        # 1. Superadmin (Direction)
        user_admin = create_clean_user(
            username="admin@demo.ma",
            email="admin@demo.ma",
            first_name="Directeur",
            last_name="General",
            is_staff=True,
            is_superuser=True,
            groups=["ADMIN"]
        )

        # 2. Comptable / Caisse
        user_caisse = create_clean_user(
            username="caisse@demo.ma",
            email="caisse@demo.ma",
            first_name="Responsable",
            last_name="Comptabilite",
            is_staff=True,
            is_superuser=False,
            groups=["COMPTABLE"]
        )

        # 3. Professeur
        user_prof = create_clean_user(
            username="prof@demo.ma",
            email="prof@demo.ma",
            first_name="Karim",
            last_name="Alami",
            is_staff=True,
            is_superuser=False,
            groups=["PROF"]
        )

        # Enseignant lié (sécurisé contre les conflits de matricule / user existants)
        ens_prof = Enseignant.objects.filter(matricule="ENS-0001").first()
        if not ens_prof:
            ens_prof = Enseignant.objects.filter(user=user_prof).first()

        # Détacher tout autre enseignant lié à ce user pour respecter OneToOneField
        Enseignant.objects.filter(user=user_prof).exclude(id=getattr(ens_prof, "id", None)).update(user=None)

        if ens_prof:
            ens_prof.user = user_prof
            ens_prof.matricule = "ENS-0001"
            ens_prof.nom = "Alami"
            ens_prof.prenom = "Karim"
            ens_prof.email = "prof@demo.ma"
            ens_prof.telephone = "0661123456"
            ens_prof.specialite = "Mathematiques"
            ens_prof.is_active = True
            ens_prof.save()
        else:
            ens_prof = Enseignant.objects.create(
                user=user_prof,
                matricule="ENS-0001",
                nom="Alami",
                prenom="Karim",
                email="prof@demo.ma",
                telephone="0661123456",
                specialite="Mathematiques",
                is_active=True,
            )
        mat_math.enseignants.add(ens_prof)

        # Affectations de Karim Alami aux 4 classes
        all_groupes = [groupe_cp, groupe_ce1, groupe_1ac, groupe_tc]
        for grp in all_groupes:
            EnseignantGroupe.objects.get_or_create(
                annee=annee,
                enseignant=ens_prof,
                groupe=grp,
                matiere_fk=None,
            )
            EnseignantGroupe.objects.get_or_create(
                annee=annee,
                enseignant=ens_prof,
                groupe=grp,
                matiere_fk=mat_math,
            )

        # 4. Compte Parent
        user_parent = create_clean_user(
            username="parent@demo.ma",
            email="parent@demo.ma",
            first_name="Rachid",
            last_name="El Mansouri",
            is_staff=False,
            is_superuser=False,
            groups=["ELEVE", "PARENT"]
        )

        parent_rachid = Parent.objects.filter(email="parent@demo.ma").first()
        if not parent_rachid:
            parent_rachid = Parent.objects.filter(user=user_parent).first()

        Parent.objects.filter(user=user_parent).exclude(id=getattr(parent_rachid, "id", None)).update(user=None)

        if parent_rachid:
            parent_rachid.user = user_parent
            parent_rachid.nom = "El Mansouri"
            parent_rachid.prenom = "Rachid"
            parent_rachid.telephone = "0662987654"
            parent_rachid.email = "parent@demo.ma"
            parent_rachid.adresse = "14 Avenue Mohammed V, Casablanca"
            parent_rachid.is_active = True
            parent_rachid.save()
        else:
            parent_rachid = Parent.objects.create(
                user=user_parent,
                nom="El Mansouri",
                prenom="Rachid",
                telephone="0662987654",
                email="parent@demo.ma",
                adresse="14 Avenue Mohammed V, Casablanca",
                is_active=True,
            )

        # Parent 2 (pour la Fratrie 2)
        parent_nadia, _ = Parent.objects.update_or_create(
            email="nadia.benjelloun@demo.ma",
            defaults={
                "nom": "Benjelloun",
                "prenom": "Nadia",
                "telephone": "0663456789",
                "adresse": "8 Rue Ibn Batouta, Casablanca",
                "is_active": True,
            }
        )

        # Photos de profil réalistes pour les comptes démo
        set_profile_photo(UserSecurityProfile.get_for(user_admin), "avatar", "admin_directeur.jpg")
        set_profile_photo(UserSecurityProfile.get_for(user_caisse), "avatar", "caisse_comptable.jpg")
        set_profile_photo(UserSecurityProfile.get_for(user_prof), "avatar", "prof_karim.jpg")
        set_profile_photo(ens_prof, "photo", "prof_karim.jpg")
        set_profile_photo(UserSecurityProfile.get_for(user_parent), "avatar", "admin_directeur.jpg")

        # -------------------------------------------------------------
        # 5. ÉLÈVES & INSCRIPTIONS (30 ÉLÈVES AVEC 2 FRATRIES)
        # -------------------------------------------------------------
        self.stdout.write("--> 5/8 Enregistrement de 30 eleves avec 2 fratries et inscriptions...")

        STUDENTS = [
            # CP-A (8 élèves)
            {"prenom": "Lina", "nom": "El Mansouri", "sexe": "F", "grp": groupe_cp, "dn": date(2019, 3, 14), "parent": parent_rachid, "impaye": "OK"},
            {"prenom": "Ziad", "nom": "Tahiri", "sexe": "M", "grp": groupe_cp, "dn": date(2019, 5, 22), "parent": None, "impaye": "PARTIEL"},
            {"prenom": "Ines", "nom": "Bennani", "sexe": "F", "grp": groupe_cp, "dn": date(2019, 1, 10), "parent": None, "impaye": "OK"},
            {"prenom": "Rayane", "nom": "Chraibi", "sexe": "M", "grp": groupe_cp, "dn": date(2019, 7, 5), "parent": None, "impaye": "OK"},
            {"prenom": "Kenza", "nom": "Fassi", "sexe": "F", "grp": groupe_cp, "dn": date(2019, 9, 18), "parent": None, "impaye": "OK"},
            {"prenom": "Adam", "nom": "Chaoui", "sexe": "M", "grp": groupe_cp, "dn": date(2019, 11, 30), "parent": None, "impaye": "OK"},
            {"prenom": "Nour", "nom": "Daoudi", "sexe": "F", "grp": groupe_cp, "dn": date(2019, 4, 12), "parent": None, "impaye": "OK"},
            {"prenom": "Yassine", "nom": "Cherkaoui", "sexe": "M", "grp": groupe_cp, "dn": date(2019, 8, 25), "parent": None, "impaye": "OK"},

            # CE1-A (8 élèves)
            {"prenom": "Mehdi", "nom": "El Mansouri", "sexe": "M", "grp": groupe_ce1, "dn": date(2018, 6, 15), "parent": parent_rachid, "impaye": "OK", "link_parent_user": True},
            {"prenom": "Salma", "nom": "Alaoui", "sexe": "F", "grp": groupe_ce1, "dn": date(2018, 2, 28), "parent": None, "impaye": "INSCRIPTION_RESTE"},
            {"prenom": "Amine", "nom": "El Amrani", "sexe": "M", "grp": groupe_ce1, "dn": date(2018, 4, 19), "parent": None, "impaye": "OK"},
            {"prenom": "Yasmine", "nom": "Idrissi", "sexe": "F", "grp": groupe_ce1, "dn": date(2018, 10, 8), "parent": None, "impaye": "OK"},
            {"prenom": "Omar", "nom": "Berrada", "sexe": "M", "grp": groupe_ce1, "dn": date(2018, 12, 1), "parent": None, "impaye": "OK"},
            {"prenom": "Rania", "nom": "Senhaji", "sexe": "F", "grp": groupe_ce1, "dn": date(2018, 3, 21), "parent": None, "impaye": "OK"},
            {"prenom": "Hamza", "nom": "Lahlou", "sexe": "M", "grp": groupe_ce1, "dn": date(2018, 7, 14), "parent": None, "impaye": "OK"},
            {"prenom": "Ghita", "nom": "Filali", "sexe": "F", "grp": groupe_ce1, "dn": date(2018, 9, 3), "parent": None, "impaye": "OK"},

            # 1AC-1 (7 élèves)
            {"prenom": "Sami", "nom": "Benjelloun", "sexe": "M", "grp": groupe_1ac, "dn": date(2013, 5, 11), "parent": parent_nadia, "impaye": "OK"},
            {"prenom": "Ayoub", "nom": "Naciri", "sexe": "M", "grp": groupe_1ac, "dn": date(2013, 8, 20), "parent": None, "impaye": "RETARD_J20"},
            {"prenom": "Rim", "nom": "Benchekroun", "sexe": "F", "grp": groupe_1ac, "dn": date(2013, 1, 15), "parent": None, "impaye": "OK"},
            {"prenom": "Walid", "nom": "Slaoui", "sexe": "M", "grp": groupe_1ac, "dn": date(2013, 11, 4), "parent": None, "impaye": "OK"},
            {"prenom": "Malak", "nom": "Belhaj", "sexe": "F", "grp": groupe_1ac, "dn": date(2013, 3, 27), "parent": None, "impaye": "OK"},
            {"prenom": "Taha", "nom": "Mekouar", "sexe": "M", "grp": groupe_1ac, "dn": date(2013, 7, 9), "parent": None, "impaye": "OK"},
            {"prenom": "Hiba", "nom": "Kadiri", "sexe": "F", "grp": groupe_1ac, "dn": date(2013, 10, 16), "parent": None, "impaye": "OK"},

            # TC-Sciences (7 élèves)
            {"prenom": "Aya", "nom": "Benjelloun", "sexe": "F", "grp": groupe_tc, "dn": date(2010, 4, 18), "parent": parent_nadia, "impaye": "OK"},
            {"prenom": "Houda", "nom": "Kabbaj", "sexe": "F", "grp": groupe_tc, "dn": date(2010, 9, 12), "parent": None, "impaye": "RETARD_J12"},
            {"prenom": "Anas", "nom": "Touimi", "sexe": "M", "grp": groupe_tc, "dn": date(2010, 2, 24), "parent": None, "impaye": "OK"},
            {"prenom": "Sara", "nom": "Guessous", "sexe": "F", "grp": groupe_tc, "dn": date(2010, 6, 30), "parent": None, "impaye": "OK"},
            {"prenom": "Mehdi", "nom": "Sqalli", "sexe": "M", "grp": groupe_tc, "dn": date(2010, 8, 14), "parent": None, "impaye": "OK"},
            {"prenom": "Nassim", "nom": "Jouahri", "sexe": "M", "grp": groupe_tc, "dn": date(2010, 11, 2), "parent": None, "impaye": "OK"},
            {"prenom": "Dounia", "nom": "Zerkdi", "sexe": "F", "grp": groupe_tc, "dn": date(2010, 12, 19), "parent": None, "impaye": "OK"},
        ]

        eleves_created = []

        for idx, item in enumerate(STUDENTS, start=1):
            matr = f"AZ-2025-{idx:03d}"
            user_link = user_parent if item.get("link_parent_user") else None
            if user_link:
                Eleve.objects.filter(user=user_link).exclude(matricule=matr).update(user=None)

            el, _ = Eleve.objects.update_or_create(
                matricule=matr,
                defaults={
                    "nom": item["nom"],
                    "prenom": item["prenom"],
                    "sexe": item["sexe"],
                    "date_naissance": item["dn"],
                    "is_active": True,
                    "user": user_link,
                }
            )

            # Photo de profil élève selon cycle (primaire vs secondaire) et sexe
            is_primary = item["grp"].niveau.degre.code in ["PRIMAIRE", "MATERNELLE"]
            if is_primary:
                photo_file = "eleve_garcon_ce.jpg" if item["sexe"] == "M" else "eleve_fille_cp.jpg"
            else:
                photo_file = "eleve_ado_garcon.jpg" if item["sexe"] == "M" else "eleve_ado_fille.jpg"

            set_profile_photo(el, "photo", photo_file)
            if user_link:
                set_profile_photo(UserSecurityProfile.get_for(user_link), "avatar", photo_file)

            # Rattachement au parent si applicable
            if item.get("parent"):
                ParentEleve.objects.get_or_create(
                    parent=item["parent"],
                    eleve=el,
                    defaults={"lien": "PERE" if item["parent"].nom == "El Mansouri" else "MERE"}
                )

            # Frais inscription
            frais_niv = FraisNiveau.objects.get(annee=annee, niveau=item["grp"].niveau)
            frais_ins_du = frais_niv.frais_inscription
            frais_ins_paye = frais_ins_du if item["impaye"] != "INSCRIPTION_RESTE" else Decimal("1000.00")

            insc, _ = Inscription.objects.update_or_create(
                eleve=el,
                annee=annee,
                defaults={
                    "groupe": item["grp"],
                    "periode": s1,
                    "statut": "VALIDEE",
                    "frais_inscription_du": frais_ins_du,
                    "frais_inscription_paye": frais_ins_paye,
                    "frais_scolarite_mensuel": frais_niv.frais_scolarite_mensuel,
                    "montant_total": frais_ins_du + (frais_niv.frais_scolarite_mensuel * Decimal("10")),
                }
            )

            eleves_created.append((el, insc, item))

        # -------------------------------------------------------------
        # 6. ÉCHÉANCIERS SUR 10 MOIS & TRANSACTIONS ENCAISSÉES
        # -------------------------------------------------------------
        self.stdout.write("--> 6/8 Generation des echeanciers de 10 mois et des transactions...")

        # Mois 1 (Sep 2025) à 10 (Juin 2026)
        MOIS_CONFIG = [
            (1, date(2025, 9, 5)),
            (2, date(2025, 10, 5)),
            (3, date(2025, 11, 5)),
            (4, date(2025, 12, 5)),
            (5, date(2026, 1, 5)),
            (6, date(2026, 2, 5)),
            (7, date(2026, 3, 5)),
            (8, date(2026, 4, 5)),
            (9, date(2026, 5, 5)),
            (10, date(2026, 6, 5)),
        ]

        # MODES DE PAIEMENT
        MODES = ["ESPECES", "CHEQUE", "VIREMENT"]

        for el, insc, meta in eleves_created:
            mensuel_du = insc.frais_scolarite_mensuel
            impaye_type = meta["impaye"]

            for mois_idx, d_ech in MOIS_CONFIG:
                ech, _ = EcheanceMensuelle.objects.update_or_create(
                    inscription=insc,
                    mois_index=mois_idx,
                    defaults={
                        "eleve": el,
                        "annee": annee,
                        "groupe": insc.groupe,
                        "date_echeance": d_ech,
                        "montant_du": mensuel_du,
                        "montant_paye": Decimal("0.00"),
                        "statut": "A_PAYER",
                    }
                )

                # Déterminer si ce mois est réglé ou en retard selon le profil démo
                est_paye = False
                montant_verse = Decimal("0.00")

                if impaye_type == "OK":
                    if mois_idx in (1, 2):
                        est_paye = True
                        montant_verse = mensuel_du
                elif impaye_type == "PARTIEL":
                    if mois_idx in (1, 2):
                        est_paye = True
                        montant_verse = mensuel_du
                    elif mois_idx == 3:
                        montant_verse = Decimal("400.00")
                elif impaye_type == "RETARD_J20":
                    if mois_idx == 1:
                        est_paye = True
                        montant_verse = mensuel_du
                elif impaye_type == "RETARD_J12":
                    if mois_idx in (1, 2):
                        est_paye = True
                        montant_verse = mensuel_du
                elif impaye_type == "INSCRIPTION_RESTE":
                    if mois_idx in (1, 2):
                        est_paye = True
                        montant_verse = mensuel_du

                if montant_verse > Decimal("0.00"):
                    mode_used = MODES[(el.id + mois_idx) % 3]
                    ref_doc = (
                        f"CHQ-AWB-{10000 + el.id * 17}" if mode_used == "CHEQUE"
                        else (f"VIR-BP-{50000 + el.id * 23}" if mode_used == "VIREMENT" else "")
                    )
                    tx_ref = f"TX-{annee.date_debut.year}-{el.id}-{mois_idx}"

                    if not Paiement.objects.filter(reference=tx_ref).exists():
                        Paiement.objects.create(
                            inscription=insc,
                            nature="SCOLARITE",
                            echeance=ech,
                            montant=montant_verse,
                            mode=mode_used,
                            reference=tx_ref,
                            note=f"Reglement scolarite {ech.mois_nom} ({ref_doc})" if ref_doc else f"Reglement scolarite {ech.mois_nom}",
                        )

                    if not TransactionFinance.objects.filter(reference=tx_ref).exists():
                        tx = TransactionFinance.objects.create(
                            inscription=insc,
                            parent=meta.get("parent"),
                            type_transaction="SCOLARITE",
                            montant_total=montant_verse,
                            mode=mode_used,
                            reference=tx_ref,
                            note=f"Reglement scolarite {ech.mois_nom} ({ref_doc})" if ref_doc else f"Reglement scolarite {ech.mois_nom}",
                        )

                        TransactionLigne.objects.create(
                            transaction=tx,
                            echeance=ech,
                            montant=montant_verse,
                            libelle=f"Mensualite {ech.mois_nom}",
                        )

        # -------------------------------------------------------------
        # 7. EMPLOI DU TEMPS (SÉANCES) & ABSENCES
        # -------------------------------------------------------------
        self.stdout.write("--> 7/8 Creation des seances d'emploi du temps et releves de presences...")

        SEANCES_DATA = [
            (groupe_cp, "LUN", time(8, 30), time(10, 30), "Mathematiques", "Salle 1"),
            (groupe_cp, "MAR", time(10, 30), time(12, 30), "Francais", "Salle 1"),
            (groupe_ce1, "LUN", time(10, 30), time(12, 30), "Mathematiques", "Salle 2"),
            (groupe_ce1, "MER", time(8, 30), time(10, 30), "Francais", "Salle 2"),
            (groupe_1ac, "MAR", time(8, 30), time(10, 30), "Mathematiques", "Salle 10"),
            (groupe_1ac, "JEU", time(10, 30), time(12, 30), "Mathematiques", "Salle 10"),
            (groupe_tc, "LUN", time(14, 30), time(16, 30), "Mathematiques", "Salle 20"),
            (groupe_tc, "VEN", time(8, 30), time(10, 30), "Mathematiques", "Salle 20"),
        ]

        seances_crees = []
        for grp, j, h0, h1, mat, sal in SEANCES_DATA:
            seance_obj, _ = Seance.objects.update_or_create(
                annee=annee,
                groupe=grp,
                jour=j,
                heure_debut=h0,
                heure_fin=h1,
                defaults={"enseignant": ens_prof, "matiere": mat, "salle": sal}
            )
            seances_crees.append(seance_obj)

        # Relevés d'absences & retards
        today = timezone.localdate()
        
        el_mehdi = next((e[0] for e in eleves_created if e[0].prenom == "Mehdi" and e[0].nom == "El Mansouri"), None)
        el_ayoub = next((e[0] for e in eleves_created if e[0].prenom == "Ayoub"), None)
        el_houda = next((e[0] for e in eleves_created if e[0].prenom == "Houda"), None)

        if el_mehdi:
            Absence.objects.update_or_create(
                eleve=el_mehdi, date=today - timedelta(days=2),
                defaults={"annee": annee, "groupe": groupe_ce1, "type": "RET", "justifie": True, "motif": "Consultation medicale"}
            )
        if el_ayoub:
            Absence.objects.update_or_create(
                eleve=el_ayoub, date=today - timedelta(days=1),
                defaults={"annee": annee, "groupe": groupe_1ac, "type": "ABS", "justifie": False, "motif": "Non justifiee"}
            )
            Absence.objects.update_or_create(
                eleve=el_ayoub, date=today - timedelta(days=5),
                defaults={"annee": annee, "groupe": groupe_1ac, "type": "ABS", "justifie": False, "motif": "Absence non signalee"}
            )
        if el_houda:
            Absence.objects.update_or_create(
                eleve=el_houda, date=today,
                defaults={"annee": annee, "groupe": groupe_tc, "type": "RET", "justifie": True, "motif": "Retard transport"}
            )

        # -------------------------------------------------------------
        # 8. ÉVALUATIONS & NOTES PÉDAGOGIQUES
        # -------------------------------------------------------------
        self.stdout.write("--> 8/8 Saisie d'evaluations et de notes pour les bulletins scolaires...")

        eval_math_ce1, _ = Evaluation.objects.update_or_create(
            periode=s1,
            groupe=groupe_ce1,
            matiere=mat_math,
            type="CC",
            date=date(2025, 10, 20),
            defaults={
                "titre": "Controle Continu 1 - Calcul & Numeration",
                "enseignant": ens_prof,
                "coefficient": Decimal("1.00"),
                "note_max": 20,
            }
        )

        eval_fr_ce1, _ = Evaluation.objects.update_or_create(
            periode=s1,
            groupe=groupe_ce1,
            matiere=mat_fr,
            type="CC",
            date=date(2025, 10, 25),
            defaults={
                "titre": "Controle Continu 1 - Grammaire & Orthographe",
                "enseignant": ens_prof,
                "coefficient": Decimal("1.00"),
                "note_max": 20,
            }
        )

        # Notes pour les élèves de CE1-A
        NOTES_SAMPLE = [16.5, 14.0, 18.0, 15.5, 13.0, 17.5, 19.0, 15.0]
        ce1_students = [e[0] for e in eleves_created if e[1].groupe == groupe_ce1]

        for i, student in enumerate(ce1_students):
            val_math = Decimal(str(NOTES_SAMPLE[i % len(NOTES_SAMPLE)]))
            val_fr = Decimal(str(min(val_math + Decimal("0.5"), Decimal("20.00"))))

            Note.objects.update_or_create(
                evaluation=eval_math_ce1,
                eleve=student,
                defaults={"valeur": val_math}
            )
            Note.objects.update_or_create(
                evaluation=eval_fr_ce1,
                eleve=student,
                defaults={"valeur": val_fr}
            )

        self.stdout.write(self.style.SUCCESS("""
+--------------------------------------------------------------------------+
|                  ATLAS SCHOOL ERP - SEED TERMINE AVEC SUCCES             |
+--------------------------------------------------------------------------+

RESUME DES COMPTES DE DEMONSTRATION (Mot de passe : Demo2026!*) :
  - Direction / Superadmin  : admin@demo.ma
  - Comptable / Caisse       : caisse@demo.ma
  - Enseignant              : prof@demo.ma
  - Parent / Eleve          : parent@demo.ma

DONNEES INJECTEES :
  - 1 Annee Scolaire active (2025-2026)
  - 4 Degres & 4 Niveaux (CP, CE1, 1ere AC, Tronc Commun)
  - 30 Eleves avec dossiers d'inscriptions actifs
  - 2 Fratries completes reliees aux parents demo
  - 300 Echeances mensuelles generees (10 mois)
  - Transactions d'encaissements en Especes, Cheques et Virements
  - Impayes realistes en retard (J+20, J+12, J+5, Acompte partiel)
  - Seances d'emploi du temps, feuilles d'absences, evaluations et notes
        """))
