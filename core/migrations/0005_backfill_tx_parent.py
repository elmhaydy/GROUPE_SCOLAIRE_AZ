from django.db import migrations

PRIORITY = {"PERE": 1, "MERE": 2, "TUTEUR": 3, "AUTRE": 4}

def forwards(apps, schema_editor):
    TransactionFinance = apps.get_model("core", "TransactionFinance")
    ParentEleve = apps.get_model("core", "ParentEleve")

    qs = TransactionFinance.objects.select_related("inscription").filter(parent__isnull=True)
    for tx in qs.iterator():
        eleve_id = tx.inscription.eleve_id

        liens = list(
            ParentEleve.objects
            .select_related("parent")
            .filter(eleve_id=eleve_id, parent__is_active=True)
        )
        if not liens:
            continue

        liens.sort(key=lambda x: PRIORITY.get(x.lien, 99))
        tx.parent_id = liens[0].parent_id
        tx.save(update_fields=["parent"])

def backwards(apps, schema_editor):
    TransactionFinance = apps.get_model("core", "TransactionFinance")
    TransactionFinance.objects.update(parent=None)

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_transactionfinance_parent"),  # ← adapte
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
