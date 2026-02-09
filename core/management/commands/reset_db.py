from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps

class Command(BaseCommand):
    help = "Reset TOTAL des données métier (finance, scolarité, pédagogie…)"

    def del_model(self, app_label, model_name):
        try:
            M = apps.get_model(app_label, model_name)
        except LookupError:
            return 0
        qs = M.objects.all()
        n = qs.count()
        if n:
            qs.delete()
        return n

    @transaction.atomic
    def handle(self, *args, **options):

        # ======================
        # FINANCE (ordre critique PROTECT)
        # ======================

        # 0) RemboursementFinanceLigne protège TransactionLigne
        self.del_model("core", "RemboursementFinanceLigne")

        # 1) Lignes TX qui protègent les échéances
        self.del_model("core", "TransactionLigne")

        # 2) Parents finance
        self.del_model("core", "RemboursementFinance")
        self.del_model("core", "TransactionFinance")

        # 3) Autres finance
        self.del_model("core", "Paiement")
        self.del_model("core", "RelanceMensuelle")
        self.del_model("core", "Relance")
        self.del_model("core", "Recouvrement")

        # 4) Echéances (après suppression des lignes)
        self.del_model("core", "EcheanceTransportMensuelle")
        self.del_model("core", "EcheanceMensuelle")

        # ======================
        # PEDAGOGIE / ABSENCES / COMMUNICATION
        # ======================
        self.del_model("core", "Note")
        self.del_model("core", "Evaluation")
        self.del_model("core", "CahierTexte")
        self.del_model("core", "CoursResumePDF")

        self.del_model("core", "Absence")
        self.del_model("core", "AbsenceProf")

        self.del_model("core", "SmsHistorique")
        self.del_model("core", "Avis")

        # ======================
        # SCOLARITE / LIENS
        # ======================
        self.del_model("core", "Inscription")
        self.del_model("core", "ParentEleve")
        self.del_model("core", "ProfGroupe")
        self.del_model("core", "EnseignantGroupe")

        # ======================
        # PERSONNES
        # ======================
        self.del_model("core", "Eleve")
        self.del_model("core", "Parent")
        self.del_model("core", "Enseignant")

        # ======================
        # STRUCTURE / PARAMETRAGE
        # ======================
        self.del_model("core", "FraisNiveau")
        self.del_model("core", "Matiere")
        self.del_model("core", "Periode")
        self.del_model("core", "Depense")
        self.del_model("core", "Groupe")
        self.del_model("core", "Niveau")
        self.del_model("core", "Degre")
        self.del_model("core", "AnneeScolaire")

        self.stdout.write(self.style.SUCCESS("✅ RESET TOTAL TERMINÉ"))
