from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_smssettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="parent",
            name="sms_optin",
            field=models.BooleanField(default=True),
        ),
    ]
