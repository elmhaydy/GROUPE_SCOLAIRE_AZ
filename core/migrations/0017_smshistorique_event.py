from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_smstemplate"),
    ]

    operations = [
        migrations.AddField(
            model_name="smshistorique",
            name="event",
            field=models.CharField(choices=[("absence", "Absence/Retard"), ("paiement", "Paiement/Reçu"), ("impaye", "Impayé/Relance"), ("autre", "Autre")], db_index=True, default="autre", max_length=20),
        ),
    ]
