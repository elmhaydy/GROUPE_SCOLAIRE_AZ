from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_remove_inscription_tarification_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SmsSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider_name", models.CharField(default="bulksms", max_length=80)),
                ("api_key", models.CharField(blank=True, default="", max_length=255)),
                ("sender_name", models.CharField(blank=True, default="AZ", max_length=20)),
                ("enable_absence", models.BooleanField(default=True)),
                ("enable_paiement", models.BooleanField(default=True)),
                ("enable_impaye", models.BooleanField(default=True)),
                ("optin_default", models.BooleanField(default=True)),
                ("quiet_start", models.TimeField(default=datetime.time(21, 0))),
                ("quiet_end", models.TimeField(default=datetime.time(7, 0))),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Paramètres SMS"},
        ),
    ]
