from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_audit_log"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(
                    choices=[
                        ("INFO", "Information"),
                        ("PAIEMENT", "Paiement"),
                        ("ABSENCE", "Absence"),
                        ("IMPAYE", "Impayé"),
                        ("RELANCE", "Relance"),
                        ("AVIS", "Avis"),
                        ("RENOUVELLEMENT", "Renouvellement"),
                        ("SYSTEME", "Système"),
                    ],
                    default="INFO",
                    max_length=20,
                    verbose_name="catégorie",
                )),
                ("title",      models.CharField(max_length=200, verbose_name="titre")),
                ("body",       models.TextField(blank=True, verbose_name="contenu")),
                ("link",       models.CharField(blank=True, max_length=255, verbose_name="lien")),
                ("read",       models.BooleanField(db_index=True, default=False, verbose_name="lue")),
                ("read_at",    models.DateTimeField(blank=True, null=True, verbose_name="lue le")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="créée le")),
                ("recipient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="destinataire",
                )),
                ("eleve", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="notifications",
                    to="core.eleve",
                    verbose_name="élève",
                )),
                ("parent", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="notifications",
                    to="core.parent",
                    verbose_name="parent",
                )),
            ],
            options={
                "verbose_name": "Notification",
                "verbose_name_plural": "Notifications",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="NotificationPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("canal_sms",     models.BooleanField(default=True,  verbose_name="Canal SMS")),
                ("canal_email",   models.BooleanField(default=False, verbose_name="Canal email")),
                ("canal_interne", models.BooleanField(default=True,  verbose_name="Notification interne")),
                ("notif_impaye",         models.BooleanField(default=True, verbose_name="Impayés")),
                ("notif_absence",        models.BooleanField(default=True, verbose_name="Absences")),
                ("notif_retard",         models.BooleanField(default=True, verbose_name="Retards")),
                ("notif_avis",           models.BooleanField(default=True, verbose_name="Avis école")),
                ("notif_renouvellement", models.BooleanField(default=True, verbose_name="Renouvellement inscription")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("parent", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notif_pref",
                    to="core.parent",
                    verbose_name="parent",
                )),
            ],
            options={
                "verbose_name": "Préférences de notification",
                "verbose_name_plural": "Préférences de notification",
            },
        ),
    ]
