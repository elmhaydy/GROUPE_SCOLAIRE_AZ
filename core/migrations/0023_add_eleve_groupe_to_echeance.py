from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_add_annee_to_echeance"),
    ]

    operations = [
        # DB locale/prod a déjà eleve_id / groupe_id => noop
    ]
