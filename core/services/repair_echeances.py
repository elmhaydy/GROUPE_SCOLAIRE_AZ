from django.db import transaction
from core.models import EcheanceMensuelle

@transaction.atomic
def repair_snapshots_all():
    qs = EcheanceMensuelle.objects.select_related("inscription").all()
    fixed = 0
    for e in qs:
        insc = e.inscription
        changed = False

        if e.eleve_id != insc.eleve_id:
            e.eleve_id = insc.eleve_id
            changed = True

        if e.annee_id != insc.annee_id:
            e.annee_id = insc.annee_id
            changed = True

        if e.groupe_id != insc.groupe_id:
            e.groupe_id = insc.groupe_id
            changed = True

        if changed:
            e.save(update_fields=["eleve_id", "annee_id", "groupe_id"])
            fixed += 1

    return fixed
