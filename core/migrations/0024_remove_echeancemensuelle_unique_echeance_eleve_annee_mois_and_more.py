from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_add_eleve_groupe_to_echeance"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # ✅ On ne touche PAS la DB (car sur VPS tout existe déjà)
            database_operations=[],
            # ✅ On met juste à jour l'état Django (migrations/state)
            state_operations=[
                # L'ancienne contrainte "eleve+annee+mois" n'existe pas en prod,
                # mais elle existe dans l'état (code) avant => on la retire du state.
                migrations.RemoveConstraint(
                    model_name="echeancemensuelle",
                    name="unique_echeance_eleve_annee_mois",
                ),

                # Ajout du champ inscription dans le state uniquement
                migrations.AddField(
                    model_name="echeancemensuelle",
                    name="inscription",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="echeances_mensuelles",
                        to="core.inscription",
                    ),
                ),

                # annee nullable (comme ton modèle final)
                migrations.AlterField(
                    model_name="echeancemensuelle",
                    name="annee",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="echeances",
                        to="core.anneescolaire",
                    ),
                ),

                # mois_index + validators
                migrations.AlterField(
                    model_name="echeancemensuelle",
                    name="mois_index",
                    field=models.PositiveSmallIntegerField(
                        validators=[MinValueValidator(1), MaxValueValidator(10)]
                    ),
                ),

                # indexes courts (state)
                migrations.AddIndex(
                    model_name="echeancemensuelle",
                    index=models.Index(fields=["eleve"], name="echm_eleve_idx"),
                ),
                migrations.AddIndex(
                    model_name="echeancemensuelle",
                    index=models.Index(fields=["groupe"], name="echm_groupe_idx"),
                ),

                # contrainte unique (inscription + mois) dans le state
                migrations.AddConstraint(
                    model_name="echeancemensuelle",
                    constraint=models.UniqueConstraint(
                        fields=("inscription", "mois_index"),
                        name="core_echeancemensuelle_inscription_id_mois_index_b5b1172f_uniq",
                    ),
                ),
            ],
        )
    ]

