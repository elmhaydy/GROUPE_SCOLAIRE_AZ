from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_parent_sms_optin"),
    ]

    operations = [
        migrations.CreateModel(
            name="SmsTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event", models.CharField(choices=[("absence", "Absence/Retard"), ("paiement", "Paiement/Reçu"), ("impaye", "Impayé/Relance")], max_length=20, unique=True)),
                ("title", models.CharField(default="", max_length=80)),
                ("text", models.TextField(help_text="Placeholders disponibles : {eleve}, {groupe}, {type}, {date}, {montant}, {ref}")),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Template SMS",
                "verbose_name_plural": "Templates SMS",
            },
        ),
    ]
