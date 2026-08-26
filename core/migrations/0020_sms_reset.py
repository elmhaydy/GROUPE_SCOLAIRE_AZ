from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_smshistorique_event"),
    ]

    operations = [
        migrations.RunSQL("DROP TABLE IF EXISTS core_smstemplate CASCADE;", reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL("DROP TABLE IF EXISTS core_smsproviderconfig CASCADE;", reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL("DROP TABLE IF EXISTS core_smscampaign CASCADE;", reverse_sql=migrations.RunSQL.noop),

        migrations.CreateModel(
            name="SmsProviderConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=80)),
                ("provider_type", models.CharField(choices=[("twilio", "Twilio"), ("mock", "Mock")], default="mock", max_length=20)),
                ("api_key", models.CharField(blank=True, default="", max_length=255)),
                ("sender_id", models.CharField(blank=True, default="", max_length=32)),
                ("is_active", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuration SMS",
                "verbose_name_plural": "Configurations SMS",
                "ordering": ["-is_active", "nom"],
            },
        ),

        migrations.CreateModel(
            name="SmsTemplate",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=120)),
                ("code", models.CharField(db_index=True, max_length=60, unique=True)),
                ("type_template", models.CharField(choices=[("absence", "Absence"), ("impaye", "Impayé"), ("info", "Information"), ("inscription", "Inscription"), ("manuel", "Manuel")], db_index=True, default="manuel", max_length=20)),
                ("contenu", models.TextField(help_text="Variables : {nom_parent}, {nom_eleve}, {niveau}, {groupe}, {montant}, {date}, {annee}")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sms_templates_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Template SMS",
                "verbose_name_plural": "Templates SMS",
                "ordering": ["code"],
            },
        ),

        migrations.CreateModel(
            name="SmsCampaign",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=120)),
                ("type_campagne", models.CharField(default="manuel", max_length=40)),
                ("filtre_json", models.JSONField(blank=True, default=dict)),
                ("total_envoyes", models.PositiveIntegerField(default=0)),
                ("total_echecs", models.PositiveIntegerField(default=0)),
                ("statut", models.CharField(choices=[("draft", "Brouillon"), ("running", "En cours"), ("done", "Terminé"), ("failed", "Échec")], default="draft", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cree_par", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sms_campaigns", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Campagne SMS",
                "verbose_name_plural": "Campagnes SMS",
                "ordering": ["-created_at"],
            },
        ),

        migrations.AddField(
            model_name="smshistorique",
            name="eleve",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sms", to="core.eleve"),
        ),
        migrations.AddField(
            model_name="smshistorique",
            name="inscription",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sms", to="core.inscription"),
        ),
        migrations.AddField(
            model_name="smshistorique",
            name="envoye_par",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sms_envoyes", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="smshistorique",
            name="type_envoi",
            field=models.CharField(choices=[("manuel", "Manuel"), ("groupe", "Groupe"), ("auto", "Automatique")], default="manuel", max_length=10),
        ),
        migrations.AlterField(
            model_name="smshistorique",
            name="status",
            field=models.CharField(choices=[("QUEUED", "En file"), ("SENT", "Envoyé"), ("FAILED", "Échec")], default="QUEUED", max_length=10),
        ),
    ]
