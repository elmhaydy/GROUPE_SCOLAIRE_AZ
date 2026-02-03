from django.db import transaction
from core.models import AnneeScolaire, Groupe, EnseignantGroupe

def sync_enseignant_groupe_from_matiere(matiere):
    """
    ✅ SAFE:
    - N'ajoute JAMAIS un prof à de nouveaux groupes.
    - Ne crée des lignes (matiere_fk = matiere) QUE pour les groupes déjà affectés au prof
      via la ligne group-only (matiere_fk NULL).
    - Ne supprime que les lignes de CETTE matière sur l'année active.
    """
    annee = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee:
        return

    niveaux = list(matiere.niveaux.all())
    enseignants = list(matiere.enseignants.all())

    # Si matière pas configurée => on supprime uniquement ses lignes (année active)
    if not niveaux or not enseignants:
        EnseignantGroupe.objects.filter(annee=annee, matiere_fk=matiere).delete()
        return

    # Groupes éligibles = groupes de l'année active dont le niveau est dans niveaux
    groupes_eligibles = set(
        Groupe.objects.filter(annee=annee, niveau__in=niveaux).values_list("id", flat=True)
    )

    with transaction.atomic():
        # Pour chaque enseignant: on ne garde que SES groupes déjà affectés (group-only)
        for ens in enseignants:
            groupes_deja_affectes = set(
                EnseignantGroupe.objects.filter(
                    annee=annee,
                    enseignant=ens,
                    matiere_fk__isnull=True,   # ✅ group-only = source de vérité
                ).values_list("groupe_id", flat=True)
            )

            groupes_cibles = groupes_deja_affectes.intersection(groupes_eligibles)

            # Existing matière rows for this teacher+matiere
            existing_pairs = set(
                EnseignantGroupe.objects.filter(
                    annee=annee,
                    enseignant=ens,
                    matiere_fk=matiere,
                ).values_list("groupe_id", flat=True)
            )

            # ✅ delete rows for groups no longer in cible
            to_delete = existing_pairs - groupes_cibles
            if to_delete:
                EnseignantGroupe.objects.filter(
                    annee=annee,
                    enseignant=ens,
                    matiere_fk=matiere,
                    groupe_id__in=list(to_delete),
                ).delete()

            # ✅ create missing rows
            to_create = groupes_cibles - existing_pairs
            for gid in to_create:
                EnseignantGroupe.objects.get_or_create(
                    annee=annee,
                    enseignant=ens,
                    groupe_id=gid,
                    matiere_fk=matiere,
                )
