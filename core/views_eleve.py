# core/views_eleve.py
from decimal import Decimal
from datetime import date
from decimal import Decimal
import calendar
from decimal import Decimal
from django.db.models import Prefetch
from datetime import timedelta, date as date_cls
from django.db.models import Q
from django.shortcuts import render
from django.utils.dateparse import parse_date
from decimal import Decimal
from dataclasses import dataclass
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.db.models import F
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce

from django.utils.dateparse import parse_date
from core.models import CahierTexte, CoursResumePDF, Matiere

from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from django.contrib import messages
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect
from core.models import ParentEleve
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import Avis, Inscription, Eleve , EcheanceMensuelle

from core.models import (
    AnneeScolaire, Inscription, Periode, Note, Absence
)
from accounts.decorators import eleve_required
from core.models import (
    Eleve, Inscription, Paiement, Absence, AnneeScolaire, Periode, Avis, Note, Seance
)
from datetime import datetime, date as date_cls

from accounts.decorators import eleve_required
from core.models import Seance
from django.shortcuts import render
def _mois_index_courant_annee_scolaire(today, annee_active):
    """
    Convertit la date du jour en mois_index scolaire (1..10 : Sep..Jun)
    en se basant sur annee_active.date_debut (ex: 2025-09-01).
    """
    if not annee_active or not annee_active.date_debut:
        return None

    start_year = annee_active.date_debut.year
    # mapping mois calendrier -> mois_index scolaire
    # Sep(9)=1 ... Dec(12)=4 ... Jan(1)=5 ... Jun(6)=10
    cal_to_index = {9: 1, 10: 2, 11: 3, 12: 4, 1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10}

    idx = cal_to_index.get(today.month)
    if idx is None:
        # Juillet/Août hors période scolaire => on peut retourner 10 (fin) ou None
        return None

    # Sécurise l'année : Sep->Dec doivent être sur start_year, Jan->Jun sur start_year+1
    if today.month in (9, 10, 11, 12) and today.year != start_year:
        # si ton annee_active n'est pas cohérente avec today, on laisse quand même
        pass
    if today.month in (1, 2, 3, 4, 5, 6) and today.year not in (start_year, start_year + 1):
        pass

    return idx

def _get_eleve_or_forbidden(request):
    eleve = Eleve.objects.filter(user=request.user).first()
    if not eleve:
        messages.error(request, "⚠️ Aucun profil élève lié à ce compte.")
        return None
    return eleve

def _get_active_annee():
    return AnneeScolaire.objects.filter(is_active=True).first()

def _get_active_inscription(eleve, annee_active):
    if not annee_active:
        return None
    return (
        Inscription.objects
        .select_related("annee", "groupe", "groupe__niveau", "groupe__niveau__degre")
        .filter(eleve=eleve, annee=annee_active)
        .first()
    )

@eleve_required
def eleve_profil(request):
    eleve = _get_eleve_or_forbidden(request)
    if not eleve:
        return render(request, "eleve/forbidden.html")

    annee_active = _get_active_annee()
    inscription = _get_active_inscription(eleve, annee_active)

    parents = (
        ParentEleve.objects
        .select_related("parent")
        .filter(eleve=eleve)
        .order_by("lien", "id")
    )

    return render(request, "eleve/profil.html", {
        "eleve": eleve,
        "annee_active": annee_active,
        "inscription": inscription,
        "parents": parents,  # ✅ IMPORTANT
    })


@dataclass
class PaiementVirtual:
    date_paiement: object
    nature: str
    mode: str
    montant: Decimal
    reference: str
    note: str

    # pour template (comme un vrai Paiement)
    def get_nature_display(self):
        return "Frais d'inscription" if self.nature == "INSCRIPTION" else "Frais de scolarité"

    def get_mode_display(self):
        return self.mode or "—"


@eleve_required
def eleve_paiements(request):
    eleve = _get_eleve_or_forbidden(request)
    if not eleve:
        return render(request, "eleve/forbidden.html")

    annee_active = _get_active_annee()
    inscription = _get_active_inscription(eleve, annee_active)

    # ======================
    # PAIEMENTS (vrais)
    # ======================
    paiements_qs = (
        Paiement.objects
        .select_related("inscription", "echeance")
        .filter(inscription__eleve=eleve)
    )
    if annee_active:
        paiements_qs = paiements_qs.filter(inscription__annee=annee_active)
    paiements_qs = paiements_qs.order_by("-date_paiement", "-id")

    # ======================
    # SUIVI + KPI (source = inscription + échéances)
    # ======================
    suivi = []
    bloc_inscription = None

    total_paye = Decimal("0.00")
    dernier_paiement = None

    paiements_virtual = []

    if inscription:
        paid_insc = inscription.frais_inscription_paye or Decimal("0.00")
        due_insc = inscription.frais_inscription_du or Decimal("0.00")
        reste_insc = inscription.reste_inscription

        bloc_inscription = {
            "paid": paid_insc,
            "due": due_insc,
            "reste": reste_insc,
            "status": "PAYE" if reste_insc <= Decimal("0.00") else "A_PAYER",
        }

        echeances_qs = (
            EcheanceMensuelle.objects
            .filter(eleve_id=inscription.eleve_id, annee_id=inscription.annee_id)
            .order_by("mois_index", "date_echeance", "id")
        )

        total_sco_paye = (
            echeances_qs.aggregate(
                s=Coalesce(
                    Sum("montant_paye"),
                    Decimal("0.00"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )["s"] or Decimal("0.00")
        )
        total_paye = paid_insc + total_sco_paye

        # dernier paiement : vrai si existe sinon dernière échéance payée
        dernier_paiement = paiements_qs.first()
        if not dernier_paiement:
            last_e = (
                echeances_qs
                .filter(montant_paye__gt=Decimal("0.00"))
                .order_by("-date_echeance", "-mois_index", "-id")
                .first()
            )
            if last_e:
                dernier_paiement = PaiementVirtual(
                    date_paiement=last_e.date_echeance,
                    nature="SCOLARITE",
                    mode="—",
                    montant=last_e.montant_paye or Decimal("0.00"),
                    reference="—",
                    note="",
                )

        # suivi cards
        for e in echeances_qs:
            label = f"{e.mois_nom} {e.date_echeance.year}"
            suivi.append({
                "label": label,
                "due": e.montant_du or Decimal("0.00"),
                "paid": e.montant_paye or Decimal("0.00"),
                "reste": e.reste,
                "status": e.statut,
            })

        # ✅ FALLBACK TABLE : si aucun Paiement, générer depuis inscription + échéances payées
        if paiements_qs.count() == 0:
            # frais inscription
            if paid_insc > 0:
                paiements_virtual.append(PaiementVirtual(
                    date_paiement=inscription.date_inscription,
                    nature="INSCRIPTION",
                    mode="—",
                    montant=paid_insc,
                    reference="—",
                    note="(historique reconstruit)"
                ))

            # échéances payées
            for e in echeances_qs:
                if (e.montant_paye or Decimal("0.00")) > 0:
                    paiements_virtual.append(PaiementVirtual(
                        date_paiement=e.date_echeance,
                        nature="SCOLARITE",
                        mode="—",
                        montant=e.montant_paye or Decimal("0.00"),
                        reference=f"{e.mois_nom} {e.date_echeance.year}",
                        note="(historique reconstruit)"
                    ))

            # ordre desc date
            paiements_virtual.sort(key=lambda x: str(x.date_paiement), reverse=True)

    else:
        # pas d'inscription => KPI via paiements
        total_paye = (
            paiements_qs.aggregate(
                s=Coalesce(
                    Sum("montant"),
                    Decimal("0.00"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )["s"] or Decimal("0.00")
        )
        dernier_paiement = paiements_qs.first()

    # ✅ la table affichera soit les paiements vrais, soit la liste virtuelle
    paiements = list(paiements_qs) if paiements_qs.exists() else paiements_virtual

    return render(request, "eleve/paiements.html", {
        "eleve": eleve,
        "annee_active": annee_active,
        "inscription": inscription,

        "paiements": paiements,
        "total_paye": total_paye,
        "dernier_paiement": dernier_paiement,

        "suivi": suivi,
        "bloc_inscription": bloc_inscription,
    })

@eleve_required
def eleve_absences(request):
    eleve = _get_eleve_or_forbidden(request)
    if not eleve:
        return render(request, "eleve/forbidden.html")

    annee_active = _get_active_annee()
    inscription = _get_active_inscription(eleve, annee_active)

    absences = Absence.objects.select_related("seance").filter(eleve=eleve)
    if annee_active and inscription:
        absences = absences.filter(annee=annee_active, groupe=inscription.groupe)
    absences = absences.order_by("-date", "-id")

    return render(request, "eleve/absences.html", {
        "eleve": eleve,
        "annee_active": annee_active,
        "inscription": inscription,
        "absences": absences,
    })

@eleve_required
def eleve_notes(request):
    eleve = _get_eleve_or_forbidden(request)
    if not eleve:
        return render(request, "eleve/forbidden.html")

    annee_active = _get_active_annee()
    inscription = _get_active_inscription(eleve, annee_active)

    notes = Note.objects.select_related("evaluation", "evaluation__matiere", "evaluation__periode").filter(eleve=eleve)

    if inscription:
        # filtre sur le groupe de l'année active
        notes = notes.filter(evaluation__groupe=inscription.groupe)

    notes = notes.order_by("-evaluation__date", "-id")

    return render(request, "eleve/notes.html", {
        "eleve": eleve,
        "annee_active": annee_active,
        "inscription": inscription,
        "notes": notes,
    })


@eleve_required
def eleve_avis(request):
    eleve = _get_eleve_or_forbidden(request)
    if not eleve:
        return render(request, "eleve/forbidden.html")

    annee_active = _get_active_annee()
    inscription = _get_active_inscription(eleve, annee_active)

    # ✅ filtres
    q = (request.GET.get("q") or "").strip()

    # ✅ semaine (date => lundi..dimanche)
    week_str = (request.GET.get("week") or "").strip()
    week_date = parse_date(week_str) if week_str else None
    if not week_date:
        week_date = date_cls.today()

    week_start = week_date - timedelta(days=week_date.weekday())
    week_end = week_start + timedelta(days=6)

    days = [week_start + timedelta(days=i) for i in range(7)]
    grouped = {d: [] for d in days}

    avis_qs = Avis.objects.filter(visible_parent=True)

    if inscription:
        degre_id = inscription.groupe.niveau.degre_id
        niveau_id = inscription.groupe.niveau_id
        groupe_id = inscription.groupe_id

        avis_qs = avis_qs.filter(
            Q(cible_type="TOUS")
            | Q(cible_type="DEGRE", degre_id=degre_id)
            | Q(cible_type="NIVEAU", niveau_id=niveau_id)
            | Q(cible_type="GROUPE", groupe_id=groupe_id)
            | Q(cible_type="ELEVE", eleve_id=eleve.id)
        )
    else:
        avis_qs = avis_qs.filter(cible_type="TOUS")

    # ✅ filtre semaine (date_publication)
    avis_qs = avis_qs.filter(date_publication__date__range=(week_start, week_end))

    # ✅ recherche serveur
    if q:
        avis_qs = avis_qs.filter(
            Q(titre__icontains=q) | Q(contenu__icontains=q)
        )

    avis_qs = avis_qs.order_by("date_publication", "id")

    # ✅ groupement par jour (date_publication.date())
    for a in avis_qs:
        d = a.date_publication.date()
        if d in grouped:
            grouped[d].append(a)

    prev_week = (week_start - timedelta(days=7)).isoformat()
    next_week = (week_start + timedelta(days=7)).isoformat()

    return render(request, "eleve/avis.html", {
        "eleve": eleve,
        "annee_active": annee_active,
        "inscription": inscription,

        "items": avis_qs,
        "q": q,

        "week_selected": week_date.isoformat(),
        "week_start": week_start,
        "week_end": week_end,
        "days": days,
        "grouped": grouped,
        "prev_week": prev_week,
        "next_week": next_week,
    })


@eleve_required
def eleve_edt(request):
    eleve = _get_eleve_or_forbidden(request)
    if not eleve:
        return render(request, "eleve/forbidden.html")

    annee_active = _get_active_annee()
    inscription = _get_active_inscription(eleve, annee_active)

    jours = ["LUN", "MAR", "MER", "JEU", "VEN", "SAM"]
    jours_labels = {
        "LUN": "Lundi",
        "MAR": "Mardi",
        "MER": "Mercredi",
        "JEU": "Jeudi",
        "VEN": "Vendredi",
        "SAM": "Samedi",
    }

    # ✅ Créneaux fixes (1h / 2h)
    creneaux = [
        ("08:30", "09:30"),
        ("09:30", "10:30"),
        ("10:30", "11:30"),
        ("11:30", "12:30"),
        ("12:30", "13:30"),
        ("13:30", "14:30"),
        ("14:30", "15:30"),
        ("15:30", "16:30"),
    ]
    creneaux_keys = [f"{a}-{b}" for a, b in creneaux]

    # grid[key][jour] = {seance, span, part}
    grid = {k: {} for k in creneaux_keys}

    seances = []
    if inscription and annee_active:
        seances = (
            Seance.objects
            .select_related("enseignant")
            .filter(annee=annee_active, groupe=inscription.groupe)
            .order_by("jour", "heure_debut", "heure_fin")
        )

    # --- helpers ---
    def t(hhmm: str):
        h, m = hhmm.split(":")
        return datetime.combine(date_cls.today(), datetime.strptime(hhmm, "%H:%M").time())

    # map "08:30-09:30" -> (dt_start, dt_end)
    slots = []
    for a, b in creneaux:
        slots.append((f"{a}-{b}", t(a), t(b)))

    def overlaps(a0, a1, b0, b1):
        return a0 < b1 and b0 < a1  # intersection

    # --- fill grid ---
    for s in seances:
        if not s.heure_debut or not s.heure_fin:
            continue

        s0 = datetime.combine(date_cls.today(), s.heure_debut)
        s1 = datetime.combine(date_cls.today(), s.heure_fin)

        # prendre tous les slots intersectés par la séance
        touched = [key for (key, x0, x1) in slots if overlaps(s0, s1, x0, x1)]

        # si rien, on ignore (horaire hors grille)
        if not touched:
            continue

        # On place la séance sur chaque slot touché
        # part = 1er slot => on affiche matière/prof
        # part = suivants => on met un marqueur "↳ suite" (optionnel)
        for idx, key in enumerate(touched):
            grid[key][s.jour] = {
                "seance": s,
                "part": "FIRST" if idx == 0 else "CONT",
                "count": len(touched),
            }

    return render(request, "eleve/edt.html", {
        "eleve": eleve,
        "annee_active": annee_active,
        "inscription": inscription,
        "jours": jours,
        "jours_labels": jours_labels,
        "creneaux": creneaux_keys,
        "grid": grid,
    })


def _to20(note_val: Decimal, note_max: int) -> Decimal:
    if not note_max or note_max <= 0:
        return Decimal("0")
    # normalise sur 20
    return (Decimal(note_val) * Decimal("20")) / Decimal(note_max)

@login_required
def bulletin(request):
    # 1) élève connecté
    eleve = getattr(request.user, "eleve_profile", None)
    if not eleve:
        return render(request, "eleve/bulletin.html", {
            "error": "Aucun profil élève lié à ce compte."
        })

    # 2) année active + inscription active (par année)
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    inscription = None
    if annee_active:
        inscription = (
            Inscription.objects.select_related("groupe", "groupe__niveau", "annee")
            .filter(eleve=eleve, annee=annee_active)
            .first()
        )

    periodes = []
    if annee_active:
        periodes = list(Periode.objects.filter(annee=annee_active).order_by("ordre"))

    # 3) période sélectionnée
    periode_id = request.GET.get("periode") or ""
    periode_sel = None
    if periodes:
        if periode_id:
            periode_sel = next((p for p in periodes if str(p.id) == str(periode_id)), None)
        if not periode_sel:
            periode_sel = periodes[0]  # défaut: S1

    rows = []
    recap = {
        "moyenne_generale": None,
        "total_coefs": Decimal("0"),
        "nb_notes": 0,
        "best": None,
    }

    abs_stats = {
        "absences": 0,
        "retards": 0,
    }

    if inscription and periode_sel:
        # 4) notes du semestre (par groupe + période)
        notes_qs = (
            Note.objects.select_related(
                "evaluation",
                "evaluation__matiere",
                "evaluation__periode",
                "evaluation__groupe",
            )
            .filter(
                eleve=eleve,
                evaluation__groupe=inscription.groupe,
                evaluation__periode=periode_sel,
            )
            .order_by("evaluation__matiere__nom", "-evaluation__date")
        )

        # 5) groupement par matière + moyenne pondérée
        bucket = {}  # {matiere_id: {...}}
        for n in notes_qs:
            ev = n.evaluation
            mat = ev.matiere

            note20 = _to20(n.valeur, ev.note_max)
            mat_coef = Decimal(str(mat.coefficient or 1))
            ev_coef = Decimal(str(ev.coefficient or 1))
            w = mat_coef * ev_coef  # poids

            if mat.id not in bucket:
                bucket[mat.id] = {
                    "matiere": mat.nom,
                    "matiere_coef": mat_coef,
                    "sum_w": Decimal("0"),
                    "sum_vw": Decimal("0"),
                    "items": [],
                    "best20": None,
                }

            b = bucket[mat.id]
            b["sum_w"] += w
            b["sum_vw"] += (note20 * w)
            b["items"].append({
                "date": ev.date,
                "titre": ev.titre,
                "type": ev.get_type_display(),
                "coef": ev_coef,
                "note": n.valeur,
                "note_max": ev.note_max,
                "note20": note20,
                "enseignant": (f"{ev.enseignant.prenom} {ev.enseignant.nom}" if ev.enseignant else "—"),
            })

            b["best20"] = note20 if b["best20"] is None else max(b["best20"], note20)

            recap["nb_notes"] += 1
            recap["best"] = note20 if recap["best"] is None else max(recap["best"], note20)

        # construire rows + moyenne générale pondérée par matière (coef matière)
        sum_general = Decimal("0")
        sum_general_w = Decimal("0")

        for _, b in sorted(bucket.items(), key=lambda kv: kv[1]["matiere"]):
            avg = (b["sum_vw"] / b["sum_w"]) if b["sum_w"] > 0 else None

            # poids global: coef matière (pas * coeff eval sinon double pondération)
            mw = b["matiere_coef"]
            if avg is not None:
                sum_general += (avg * mw)
                sum_general_w += mw

            rows.append({
                "matiere": b["matiere"],
                "coef": b["matiere_coef"],
                "moyenne20": avg,
                "best20": b["best20"],
                "nb": len(b["items"]),
                "items": b["items"],
            })

        if sum_general_w > 0:
            recap["moyenne_generale"] = (sum_general / sum_general_w)
            recap["total_coefs"] = sum_general_w

        # 6) absences/retards (si dates semestre renseignées)
        if periode_sel.date_debut and periode_sel.date_fin:
            abs_qs = Absence.objects.filter(
                eleve=eleve,
                annee=annee_active,
                date__gte=periode_sel.date_debut,
                date__lte=periode_sel.date_fin,
            )
            abs_stats["absences"] = abs_qs.filter(type="ABS").count()
            abs_stats["retards"] = abs_qs.filter(type="RET").count()
        # =========================
        # ✅ Moyenne de la CLASSE (groupe)
        # Méthode: moyenne des moyennes générales des élèves du groupe
        # =========================

        # On récupère toutes les notes du groupe pour la période
        class_notes_qs = (
            Note.objects.select_related(
                "eleve",
                "evaluation",
                "evaluation__matiere",
                "evaluation__periode",
                "evaluation__groupe",
            )
            .filter(
                evaluation__groupe=inscription.groupe,
                evaluation__periode=periode_sel,
            )
            .order_by("eleve_id", "evaluation__matiere__nom", "-evaluation__date")
        )

        # per eleve -> per matiere accum (sum_vw, sum_w, mat_coef)
        per_eleve = {}  # {eleve_id: {"mats": {mat_id: {...}}}}

        for n in class_notes_qs:
            ev = n.evaluation
            mat = ev.matiere

            note20 = _to20(n.valeur, ev.note_max)

            mat_coef = Decimal(str(mat.coefficient or 1))
            ev_coef = Decimal(str(ev.coefficient or 1))
            w = mat_coef * ev_coef  # poids intra matière

            e = per_eleve.setdefault(n.eleve_id, {"mats": {}})
            mats = e["mats"]

            b = mats.get(mat.id)
            if not b:
                b = {"mat_coef": mat_coef, "sum_w": Decimal("0"), "sum_vw": Decimal("0")}
                mats[mat.id] = b

            b["sum_w"] += w
            b["sum_vw"] += (note20 * w)

        # Calcul moyenne générale par élève puis moyenne de classe
        sum_class = Decimal("0")
        count_class = 0

        for eleve_id, data in per_eleve.items():
            mats = data["mats"]
            sum_general = Decimal("0")
            sum_general_w = Decimal("0")

            for _, b in mats.items():
                if b["sum_w"] <= 0:
                    continue
                avg_mat = b["sum_vw"] / b["sum_w"]   # moyenne matière /20
                mw = b["mat_coef"]                   # poids global = coef matière
                sum_general += (avg_mat * mw)
                sum_general_w += mw

            if sum_general_w > 0:
                avg_eleve = sum_general / sum_general_w
                sum_class += avg_eleve
                count_class += 1

        recap["moyenne_classe"] = (sum_class / Decimal(str(count_class))) if count_class > 0 else None

    return render(request, "eleve/bulletin.html", {
        "annee_active": annee_active,
        "inscription": inscription,
        "periodes": periodes,
        "periode_sel": periode_sel,
        "rows": rows,
        "recap": recap,
        "abs_stats": abs_stats,
        "moyenne_classe": recap["moyenne_classe"],
    })

    path("avis/<int:pk>/", views_eleve.eleve_avis_detail, name="avis_detail"),
    

@login_required
def eleve_avis_detail(request, pk):
    # retrouver l'élève depuis le user
    eleve = getattr(request.user, "eleve_profile", None)
    if not eleve:
        # fallback si ton projet gère autrement
        eleve = Eleve.objects.filter(user=request.user).first()

    # inscription active (si tu l’utilises pour filtrer les avis de groupe/niveau)
    inscription = (
        Inscription.objects.filter(eleve=eleve)
        .select_related("annee", "groupe", "groupe__niveau", "groupe__niveau__degre")
        .order_by("-annee__date_debut")
        .first()
    )

    # ✅ On récupère l’avis
    avis = get_object_or_404(Avis, pk=pk)

    # ✅ Sécurité: vérifier que cet avis est visible pour cet élève
    # (adapte si ton eleve_avis utilise déjà une logique précise)
    ok = False
    if avis.cible_type == "TOUS":
        ok = True
    elif avis.cible_type == "ELEVE" and eleve and avis.eleve_id == eleve.id:
        ok = True
    elif inscription:
        if avis.cible_type == "DEGRE" and avis.degre_id == inscription.groupe.niveau.degre_id:
            ok = True
        elif avis.cible_type == "NIVEAU" and avis.niveau_id == inscription.groupe.niveau_id:
            ok = True
        elif avis.cible_type == "GROUPE" and avis.groupe_id == inscription.groupe_id:
            ok = True

    if not ok or (avis.visible_parent is False and request.user.groups.filter(name="PARENT").exists()):
        # si pas autorisé -> 404 (propre)
        avis = get_object_or_404(Avis, pk=-1)

    return render(request, "eleve/avis_detail.html", {
        "avis": avis,
        "inscription": inscription,
    })


@eleve_required
def eleve_dashboard(request):
    eleve = _get_eleve_or_forbidden(request)
    if not eleve:
        return render(request, "eleve/forbidden.html")

    annee_active = _get_active_annee()
    inscription = _get_active_inscription(eleve, annee_active)
    
    # =============================
    # ✅ KPI — Total payé + Dernier paiement
    # Source de vérité: inscription + échéances
    # =============================
    total_paye = Decimal("0.00")
    dernier_paiement = None

    if inscription:
        # Frais inscription payé
        paid_insc = inscription.frais_inscription_paye or Decimal("0.00")

        # Échéances de l'année active
        echeances_qs = (
            EcheanceMensuelle.objects
            .filter(eleve_id=inscription.eleve_id, annee_id=inscription.annee_id)
        )

        # Total scolarité payé (somme des échéances)
        total_sco_paye = (
            echeances_qs.aggregate(
                s=Coalesce(
                    Sum("montant_paye"),
                    Decimal("0.00"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )["s"] or Decimal("0.00")
        )

        total_paye = paid_insc + total_sco_paye

        # Dernier paiement: priorité aux objets Paiement si existants
        paiements_qs = Paiement.objects.filter(inscription__eleve=eleve)
        if annee_active:
            paiements_qs = paiements_qs.filter(inscription__annee=annee_active)
        dernier_paiement = paiements_qs.order_by("-date_paiement", "-id").first()

        # Fallback: dernière échéance payée (si table Paiement vide)
        if not dernier_paiement:
            last_e = (
                echeances_qs
                .filter(montant_paye__gt=Decimal("0.00"))
                .order_by("-date_echeance", "-mois_index", "-id")
                .first()
            )
            if last_e:
                class _Last:
                    montant = last_e.montant_paye or Decimal("0.00")
                    date_paiement = last_e.date_echeance
                    def get_mode_display(self): return "—"
                dernier_paiement = _Last()

    else:
        # Pas d'inscription active => fallback sur Paiement
        paiements_qs = Paiement.objects.filter(inscription__eleve=eleve)
        if annee_active:
            paiements_qs = paiements_qs.filter(inscription__annee=annee_active)

        total_paye = (
            paiements_qs.aggregate(
                s=Coalesce(
                    Sum("montant"),
                    Decimal("0.00"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )["s"] or Decimal("0.00")
        )
        dernier_paiement = paiements_qs.order_by("-date_paiement", "-id").first()

    # =============================
    # ✅ KPI — Impayés (retard uniquement)
    # =============================
    total_impaye_retard = Decimal("0.00")
    mois_retard = []

    today = timezone.localdate()

    if inscription and annee_active:
        mois_idx_courant = _mois_index_courant_annee_scolaire(today, annee_active)

        if mois_idx_courant:
            echeances_retard = (
                EcheanceMensuelle.objects
                .filter(
                    eleve_id=inscription.eleve_id,
                    annee_id=inscription.annee_id,
                    mois_index__lt=mois_idx_courant,
                )
                .order_by("mois_index", "date_echeance", "id")
            )

            for e in echeances_retard:
                r = e.reste or Decimal("0.00")
                if r > 0:
                    total_impaye_retard += r
                    mois_retard.append({
                        "mois_nom": e.mois_nom,
                        "date": e.date_echeance,
                        "reste": r,
                        "statut": e.statut,
                    })

    # =============================
    # ABSENCES
    # =============================
    absences = Absence.objects.filter(eleve=eleve)
    if annee_active and inscription:
        absences = absences.filter(annee=annee_active, groupe=inscription.groupe)
    absences = absences.order_by("-date", "-id")[:8]

    # =============================
    # AVIS
    # =============================
    avis_qs = Avis.objects.filter(visible_parent=True)
    if inscription:
        degre_id = inscription.groupe.niveau.degre_id
        niveau_id = inscription.groupe.niveau_id
        groupe_id = inscription.groupe_id
        avis_qs = avis_qs.filter(
            Q(cible_type="TOUS")
            | Q(cible_type="DEGRE", degre_id=degre_id)
            | Q(cible_type="NIVEAU", niveau_id=niveau_id)
            | Q(cible_type="GROUPE", groupe_id=groupe_id)
            | Q(cible_type="ELEVE", eleve_id=eleve.id)
        )
    else:
        avis_qs = avis_qs.filter(cible_type="TOUS")
    avis = avis_qs.order_by("-date_publication", "-id")[:5]

    # =============================
    # NOTES
    # =============================
    notes_recent = (
        Note.objects
        .filter(eleve=eleve)
        .select_related("evaluation", "evaluation__periode", "evaluation__matiere")
        .order_by("-evaluation__date", "-id")[:6]
    )

    # =============================
    # EDT aujourd'hui (séances)
    # =============================
    seances_today = []
    if inscription and annee_active:
        map_py_to_jour = {0: "LUN", 1: "MAR", 2: "MER", 3: "JEU", 4: "VEN", 5: "SAM"}
        jour_code = map_py_to_jour.get(timezone.localdate().weekday())
        if jour_code:
            seances_today = list(
                Seance.objects.filter(
                    annee=annee_active,
                    groupe=inscription.groupe,
                    jour=jour_code
                ).order_by("heure_debut")
            )

    # =============================
    # Cahier + Résumés PDF (mini-lists)
    # =============================
    cahier_items = []
    resumes_items = []

    if inscription and annee_active:
        cahier_items = (
            CahierTexte.objects
            .select_related("matiere", "groupe", "annee")
            .filter(annee=annee_active, groupe=inscription.groupe, is_published=True)
            .order_by("-date", "-id")[:6]
        )

        resumes_items = (
            CoursResumePDF.objects
            .select_related("matiere", "groupe", "annee")
            .filter(annee=annee_active, groupe=inscription.groupe, is_published=True)
            .order_by("-date", "-id")[:6]
        )

    return render(request, "eleve/dashboard.html", {
        "eleve": eleve,
        "annee_active": annee_active,
        "inscription": inscription,

        # ✅ KPIs
        "total_paye": total_paye,
        "dernier_paiement": dernier_paiement,
        "total_impaye_retard": total_impaye_retard,
        "mois_retard": mois_retard,

        # mini-lists
        "cahier_items": cahier_items,
        "resumes_items": resumes_items,

        # autres blocs
        "absences": absences,
        "avis": avis,
        "notes_recent": notes_recent,
        "seances_today": seances_today,
    })

@eleve_required
def eleve_cahier(request):
    eleve = _get_eleve_or_forbidden(request)
    if not eleve:
        return render(request, "eleve/forbidden.html")

    annee_active = _get_active_annee()
    inscription = _get_active_inscription(eleve, annee_active)

    # Filtres
    q = (request.GET.get("q") or "").strip()
    matiere_id = (request.GET.get("matiere") or "").strip()

    # ✅ Semaine (on utilise un input date; on calcule le lundi de la semaine)
    week_str = (request.GET.get("week") or "").strip()
    week_date = parse_date(week_str) if week_str else None
    if not week_date:
        week_date = date_cls.today()

    week_start = week_date - timedelta(days=week_date.weekday())  # Lundi
    week_end = week_start + timedelta(days=6)                     # Dimanche

    items = CahierTexte.objects.none()
    matieres = Matiere.objects.none()

    # ✅ Jours de la semaine (liste de dates)
    days = [week_start + timedelta(days=i) for i in range(7)]
    grouped = {d: [] for d in days}

    if inscription and annee_active:
        base = (
            CahierTexte.objects
            .select_related("matiere", "groupe", "annee")
            .filter(
                annee=annee_active,
                groupe=inscription.groupe,
                is_published=True,
                date__range=(week_start, week_end),   # ✅ uniquement la semaine choisie
            )
        )

        # Matières dispo dans le cahier de ce groupe (sur toute l'année)
        # (Si tu veux seulement sur la semaine: remplace "base_all" par "base")
        base_all = (
            CahierTexte.objects
            .filter(annee=annee_active, groupe=inscription.groupe, is_published=True)
        )
        matieres_ids = base_all.values_list("matiere_id", flat=True).distinct()
        matieres = Matiere.objects.filter(id__in=matieres_ids).order_by("nom")

        if q:
            base = base.filter(
                Q(titre__icontains=q) |
                Q(contenu__icontains=q) |
                Q(devoir__icontains=q) |
                Q(matiere__nom__icontains=q)
            )

        if matiere_id:
            base = base.filter(matiere_id=matiere_id)

        items = base.order_by("date", "id")  # ✅ ordre naturel dans la semaine

        # ✅ Groupement par jour
        for c in items:
            if c.date in grouped:
                grouped[c.date].append(c)

    # ✅ Navigation semaine précédente/suivante
    prev_week = (week_start - timedelta(days=7)).isoformat()
    next_week = (week_start + timedelta(days=7)).isoformat()

    return render(request, "eleve/cahier.html", {
        "eleve": eleve,
        "annee_active": annee_active,
        "inscription": inscription,

        "items": items,
        "matieres": matieres,

        "q": q,
        "matiere_selected": matiere_id,

        # semaine
        "week_selected": week_date.isoformat(),
        "week_start": week_start,
        "week_end": week_end,
        "days": days,
        "grouped": grouped,
        "prev_week": prev_week,
        "next_week": next_week,
    })


@eleve_required
def eleve_resumes(request):
    eleve = _get_eleve_or_forbidden(request)
    if not eleve:
        return render(request, "eleve/forbidden.html")

    annee_active = _get_active_annee()
    inscription = _get_active_inscription(eleve, annee_active)

    q = (request.GET.get("q") or "").strip()
    matiere_id = (request.GET.get("matiere") or "").strip()

    # ✅ Semaine (date choisie => on calcule lundi→dimanche)
    week_str = (request.GET.get("week") or "").strip()
    week_date = parse_date(week_str) if week_str else None
    if not week_date:
        week_date = date_cls.today()

    week_start = week_date - timedelta(days=week_date.weekday())  # Lundi
    week_end = week_start + timedelta(days=6)                     # Dimanche

    days = [week_start + timedelta(days=i) for i in range(7)]
    grouped = {d: [] for d in days}

    items = CoursResumePDF.objects.none()
    matieres = Matiere.objects.none()

    if inscription and annee_active:
        base = (
            CoursResumePDF.objects
            .select_related("matiere", "groupe", "annee")
            .filter(
                annee=annee_active,
                groupe=inscription.groupe,
                is_published=True,
                date__range=(week_start, week_end),
            )
        )

        # matières disponibles (sur l'année)
        base_all = (
            CoursResumePDF.objects
            .filter(annee=annee_active, groupe=inscription.groupe, is_published=True)
        )
        matieres_ids = base_all.values_list("matiere_id", flat=True).distinct()
        matieres = Matiere.objects.filter(id__in=matieres_ids).order_by("nom")

        if q:
            base = base.filter(
                Q(titre__icontains=q) |
                Q(matiere__nom__icontains=q)
            )

        if matiere_id:
            base = base.filter(matiere_id=matiere_id)

        items = base.order_by("date", "id")

        for r in items:
            if r.date in grouped:
                grouped[r.date].append(r)

    prev_week = (week_start - timedelta(days=7)).isoformat()
    next_week = (week_start + timedelta(days=7)).isoformat()

    return render(request, "eleve/resumes.html", {
        "eleve": eleve,
        "annee_active": annee_active,
        "inscription": inscription,

        "items": items,
        "matieres": matieres,

        "q": q,
        "matiere_selected": matiere_id,

        "week_selected": week_date.isoformat(),
        "week_start": week_start,
        "week_end": week_end,
        "days": days,
        "grouped": grouped,
        "prev_week": prev_week,
        "next_week": next_week,
    })
