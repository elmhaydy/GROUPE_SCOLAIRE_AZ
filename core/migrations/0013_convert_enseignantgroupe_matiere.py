from django.db import migrations


def forwards(apps, schema_editor):
    EnseignantGroupe = apps.get_model("core", "EnseignantGroupe")
    Matiere = apps.get_model("core", "Matiere")

    # map nom -> id (match exact, insensible à la casse)
    mat_map = {}
    for m in Matiere.objects.all().only("id", "nom"):
        if m.nom:
            mat_map[m.nom.strip().lower()] = m.id

    # remplir matiere_fk depuis ancien champ texte "matiere"
    for ag in EnseignantGroupe.objects.all().only("id", "matiere"):
        raw = (ag.matiere or "").strip()
        if not raw:
            continue

        mid = mat_map.get(raw.lower())
        if mid:
            EnseignantGroupe.objects.filter(id=ag.id).update(matiere_fk_id=mid)


def backwards(apps, schema_editor):
    EnseignantGroupe = apps.get_model("core", "EnseignantGroupe")
    EnseignantGroupe.objects.update(matiere_fk=None)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_enseignantgroupe_matiere_fk"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
