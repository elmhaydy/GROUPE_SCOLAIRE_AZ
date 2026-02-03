from io import BytesIO
from decimal import Decimal
from django.http import HttpResponse
from django.conf import settings
from reportlab.lib.utils import ImageReader
from django.contrib.staticfiles import finders

from core.models import TempPassword

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth


def _header(c, title: str, subtitle: str = ""):
    w, h = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(18 * mm, h - 18 * mm, title)

    if subtitle:
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.grey)
        c.drawString(18 * mm, h - 24 * mm, subtitle)
        c.setFillColor(colors.black)

    # ligne
    c.setStrokeColor(colors.lightgrey)
    c.line(18 * mm, h - 27 * mm, w - 18 * mm, h - 27 * mm)
    c.setStrokeColor(colors.black)


def _footer(c):
    w, _ = A4
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawRightString(w - 18 * mm, 12 * mm, "Groupe Scolaire AZ")
    c.setFillColor(colors.black)


def _table(c, x, y, cols, rows, col_widths):
    """
    Table simple (sans Platypus) : colonnes fixes, lignes.
    y = top start
    """
    c.setFont("Helvetica-Bold", 9)
    row_h = 7 * mm

    # header
    cur_x = x
    for i, col in enumerate(cols):
        c.setFillColor(colors.whitesmoke)
        c.rect(cur_x, y - row_h, col_widths[i], row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawString(cur_x + 2 * mm, y - row_h + 2 * mm, str(col)[:60])
        cur_x += col_widths[i]

    # body
    c.setFont("Helvetica", 9)
    y_cursor = y - row_h
    for r in rows:
        y_cursor -= row_h
        cur_x = x
        for i, cell in enumerate(r):
            c.rect(cur_x, y_cursor, col_widths[i], row_h, fill=0, stroke=1)
            c.drawString(cur_x + 2 * mm, y_cursor + 2 * mm, str(cell)[:80])
            cur_x += col_widths[i]

    return y_cursor


def pdf_response(filename: str, draw_fn):
    """
    draw_fn(canvas) doit dessiner le document.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    draw_fn(c)

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


# ============================================================
# PDF templates
# ============================================================
from datetime import datetime
from reportlab.pdfbase.pdfmetrics import stringWidth

def paiement_recu_pdf(p, total_paye, reste):
    def draw(c):
        w, h = A4

        # =========================
        # Portail + login + mdp (TempPassword)
        # =========================
        portal_url = "https://groupescolaireaz.cloud/"
        login = getattr(p.inscription.eleve, "matricule", "—")

        pwd = "—"
        user = getattr(p.inscription.eleve, "user", None)
        if user:
            tp = TempPassword.objects.filter(user=user).first()
            if tp and tp.password:
                pwd = tp.password

        # =========================
        # Mois / libellés
        # =========================
        mois_label = "—"
        mois_montant = f"{p.montant} MAD"

        if getattr(p, "nature", "") == "SCOLARITE" and getattr(p, "echeance_id", None):
            ech = p.echeance
            mois_label = f"{ech.mois_nom} — échéance : {ech.date_echeance}"
            mois_montant = f"{ech.montant_du} MAD"
        elif getattr(p, "nature", "") == "INSCRIPTION":
            mois_label = "Frais d’inscription"
            mois_montant = f"{p.montant} MAD"
        else:
            if getattr(p, "echeance_id", None):
                ech = p.echeance
                mois_label = f"{ech.mois_nom} — échéance : {ech.date_echeance}"
                mois_montant = f"{ech.montant_du} MAD"
            else:
                mois_label = "Paiement"
                mois_montant = f"{p.montant} MAD"

        # =========================
        # Mode label (IMPORTANT)
        # =========================
        mode_label = getattr(p, "get_mode_display", None)
        mode_value = mode_label() if callable(mode_label) else (getattr(p, "mode", None) or "—")

        nature_label = getattr(p, "get_nature_display", None)
        nature_value = nature_label() if callable(nature_label) else (getattr(p, "nature", None) or "—")

        # =========================
        # Logo
        # =========================
        logo_path = finders.find("img/logo_AZ.png")
        logo_img = None
        if logo_path:
            try:
                logo_img = ImageReader(logo_path)
            except Exception:
                logo_img = None

        # =========================
        # Palette AZ NEBULA (print safe)
        # =========================
        COLOR_PRIMARY = "#4f46e5"     # indigo premium
        COLOR_ACCENT  = "#a855f7"     # violet nebula
        COLOR_OK      = "#059669"     # green
        COLOR_TEXT    = "#0f172a"
        COLOR_MUTED   = "#475569"
        COLOR_BORDER  = "#e2e8f0"
        COLOR_SOFT    = "#f8fafc"
        COLOR_PILL_BG = "#eef2ff"

        # =========================
        # Helpers
        # =========================
        def ellipsize(text, max_w, font="Helvetica", size=9):
            s = str(text or "")
            if stringWidth(s, font, size) <= max_w:
                return s
            while s and stringWidth(s + "…", font, size) > max_w:
                s = s[:-1]
            return (s + "…") if s else ""

        def modern_box(x, y_top, bw, bh, bg="#ffffff"):
            # shadow (safe)
            c.setFillColor(colors.HexColor("#e5e7eb"))
            c.roundRect(x - 0.8, y_top - bh - 0.8, bw + 1.6, bh + 1.6, 5*mm, fill=1, stroke=0)

            c.setFillColor(colors.HexColor(bg))
            c.setStrokeColor(colors.HexColor(COLOR_BORDER))
            c.setLineWidth(0.9)
            c.roundRect(x, y_top - bh, bw, bh, 5*mm, fill=1, stroke=1)
            c.setLineWidth(0.5)
            c.setStrokeColor(colors.black)

        def pill(x, y, text, bg=COLOR_PILL_BG, fg=COLOR_PRIMARY, wmm=85):
            c.setFillColor(colors.HexColor("#e5e7eb"))
            c.roundRect(x - 0.6, y - 0.6, wmm*mm, 8*mm, 4*mm, fill=1, stroke=0)

            c.setFillColor(colors.HexColor(bg))
            c.roundRect(x, y, wmm*mm, 8*mm, 4*mm, fill=1, stroke=0)

            c.setFillColor(colors.HexColor(fg))
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x + 4*mm, y + 2.2*mm, ellipsize(text, (wmm*mm) - 8*mm, "Helvetica-Bold", 9))
            c.setFillColor(colors.black)

        def line(x1, y, x2):
            c.setStrokeColor(colors.HexColor(COLOR_BORDER))
            c.setLineWidth(0.9)
            c.line(x1, y, x2, y)
            c.setLineWidth(0.5)
            c.setStrokeColor(colors.black)

        def section_title(x, y, t):
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.HexColor(COLOR_TEXT))
            c.drawString(x, y, t)
            c.setStrokeColor(colors.HexColor(COLOR_PRIMARY))
            c.setLineWidth(1.2)
            c.line(x, y - 2*mm, x + 26*mm, y - 2*mm)
            c.setLineWidth(0.5)
            c.setFillColor(colors.black)

        def kv(x, y, label, value, highlight=False, max_w=70*mm):
            c.setFont("Helvetica", 7.5)
            c.setFillColor(colors.HexColor(COLOR_MUTED))
            c.drawString(x, y, str(label).upper())

            c.setFont("Helvetica-Bold" if highlight else "Helvetica", 10 if highlight else 9)
            c.setFillColor(colors.HexColor(COLOR_PRIMARY if highlight else COLOR_TEXT))
            c.drawString(x, y - 4*mm, ellipsize(value, max_w, "Helvetica-Bold" if highlight else "Helvetica", 10 if highlight else 9))
            c.setFillColor(colors.black)

        def row_money(x, y, label, value, strong=False):
            c.setFont("Helvetica-Bold" if strong else "Helvetica", 10 if strong else 9)
            c.setFillColor(colors.HexColor(COLOR_TEXT))
            c.drawString(x, y, label)
            c.drawRightString(x + 80*mm, y, str(value))
            c.setFillColor(colors.black)

        # =========================
        # Code reçu (vérification)
        # =========================
        # Exemple: AZ-2026-000123
        year = getattr(p, "date_paiement", None)
        year = year.year if year else datetime.now().year
        code_recu = f"AZ-{year}-{int(p.id):06d}"

        # =========================
        # 1 reçu (carte)
        # =========================
        def draw_receipt(y_top):
            margin_x = 15 * mm
            receipt_w = w - 2 * margin_x
            receipt_h = 128 * mm  # ✅ fit parfait pour 2 reçus

            modern_box(margin_x, y_top, receipt_w, receipt_h, bg="#ffffff")

            # header zone
            if logo_img:
                c.drawImage(logo_img, margin_x + 10*mm, y_top - 22*mm, width=18*mm, height=18*mm, mask="auto")

            c.setFont("Helvetica-Bold", 15)
            c.setFillColor(colors.HexColor(COLOR_PRIMARY))
            c.drawString(margin_x + 31*mm, y_top - 13*mm, "REÇU DE PAIEMENT")

            c.setFont("Helvetica", 8.5)
            c.setFillColor(colors.HexColor(COLOR_MUTED))
            c.drawString(margin_x + 31*mm, y_top - 18*mm, "Groupe Scolaire AZ • Administration")
            c.setFillColor(colors.black)

            # top pills
            pill(margin_x + receipt_w - 94*mm, y_top - 23*mm, f"{code_recu}", bg="#f5f3ff", fg=COLOR_ACCENT, wmm=88)
            pill(margin_x + receipt_w - 94*mm, y_top - 33*mm, f"{nature_value}", bg=COLOR_PILL_BG, fg=COLOR_PRIMARY, wmm=88)

            line(margin_x + 10*mm, y_top - 36*mm, margin_x + receipt_w - 10*mm)

            left_x = margin_x + 12*mm
            right_x = margin_x + receipt_w/2 + 8*mm

            # ELEVE
            section_title(left_x, y_top - 44*mm, "ÉLÈVE")
            kv(left_x, y_top - 50*mm, "Matricule", getattr(p.inscription.eleve, "matricule", "—"), highlight=True, max_w=70*mm)
            kv(left_x + 48*mm, y_top - 50*mm, "Nom", f"{getattr(p.inscription.eleve,'nom','')} {getattr(p.inscription.eleve,'prenom','')}", max_w=70*mm)

            kv(left_x, y_top - 66*mm, "Année", getattr(p.inscription.annee, "nom", "—"), max_w=70*mm)
            grp_txt = f"{getattr(p.inscription.groupe.niveau,'nom','—')} / {getattr(p.inscription.groupe,'nom','—')}"
            kv(left_x + 48*mm, y_top - 66*mm, "Groupe", grp_txt, max_w=70*mm)

            # PAIEMENT
            section_title(right_x, y_top - 44*mm, "PAIEMENT")
            kv(right_x, y_top - 50*mm, "Date", str(getattr(p, "date_paiement", "—")), max_w=70*mm)
            kv(right_x + 48*mm, y_top - 50*mm, "Mode", mode_value, max_w=70*mm)

            # Montants
            line(margin_x + 10*mm, y_top - 80*mm, margin_x + receipt_w - 10*mm)

            section_title(left_x, y_top - 88*mm, "ÉCHÉANCE")
            row_money(left_x, y_top - 94*mm, "Période", mois_label, strong=True)
            row_money(left_x, y_top - 101*mm, "Montant du mois", mois_montant, strong=True)
            row_money(left_x, y_top - 108*mm, "Payé (ce reçu)", f"{p.montant} MAD", strong=False)

            # Accès Portail
            line(margin_x + 10*mm, y_top - 114*mm, margin_x + receipt_w - 10*mm)

            section_title(left_x, y_top - 122*mm, "ACCÈS PORTAIL")
            c.setFont("Helvetica", 8.5)
            c.setFillColor(colors.HexColor(COLOR_TEXT))
            c.drawString(left_x, y_top - 128*mm, f"Site : {portal_url}")
            c.drawString(left_x, y_top - 134*mm, f"Login : {login}")
            c.drawString(right_x, y_top - 128*mm, f"Mot de passe : {pwd}")
            c.setFillColor(colors.black)

            # Footer signature
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.HexColor(COLOR_MUTED))
            c.drawString(left_x, y_top - 142*mm, "Signature / Cachet : _________________________________")
            c.setFillColor(colors.black)

        # =========================
        # 2 reçus sur 1 page A4
        # =========================
        top_y = h - 10*mm
        draw_receipt(top_y)

        # ligne de coupe
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.setDash(3, 3)
        c.line(15*mm, h/2, w - 15*mm, h/2)
        c.setDash()

        bottom_y = (h/2) - 5*mm
        draw_receipt(bottom_y)

    return pdf_response(f"recu_paiement_{p.id}.pdf", draw)


def paiement_recu_batch_pdf(first_paiement, paiements_qs, total_batch: Decimal, batch_token: str):
    """
    - first_paiement: un Paiement (le premier du batch)
    - paiements_qs: queryset/list des paiements du batch (triés par mois_index si possible)
    - total_batch: total du batch
    - batch_token: token du batch
    => PDF A4 avec 2 copies identiques (haut/bas)
    """
    def draw(c):
        w, h = A4

        p0 = first_paiement
        insc = p0.inscription
        eleve = insc.eleve

        # infos
        portal_url = "https://groupescolaireaz.cloud/"
        login = getattr(eleve, "matricule", "—")

        # mdp (TempPassword)
        pwd = "—"
        user = getattr(eleve, "user", None)
        if user:
            tp = TempPassword.objects.filter(user=user).first()
            if tp and tp.password:
                pwd = tp.password

        mode_label = getattr(p0, "get_mode_display", None)
        mode_value = mode_label() if callable(mode_label) else (getattr(p0, "mode", None) or "—")

        year = getattr(p0, "date_paiement", None)
        year = year.year if year else datetime.now().year
        code_recu = f"AZB-{year}-{str(batch_token)[:8].upper()}"

        # Logo
        logo_path = finders.find("img/logo_AZ.png")
        logo_img = None
        if logo_path:
            try:
                logo_img = ImageReader(logo_path)
            except Exception:
                logo_img = None

        # Palette
        COLOR_PRIMARY = "#4f46e5"
        COLOR_ACCENT  = "#a855f7"
        COLOR_TEXT    = "#0f172a"
        COLOR_MUTED   = "#475569"
        COLOR_BORDER  = "#e2e8f0"
        COLOR_SOFT    = "#f8fafc"

        def ellipsize(text, max_w, font="Helvetica", size=9):
            s = str(text or "")
            if stringWidth(s, font, size) <= max_w:
                return s
            while s and stringWidth(s + "…", font, size) > max_w:
                s = s[:-1]
            return (s + "…") if s else ""

        def modern_box(x, y_top, bw, bh, bg="#ffffff"):
            c.setFillColor(colors.HexColor("#e5e7eb"))
            c.roundRect(x - 0.8, y_top - bh - 0.8, bw + 1.6, bh + 1.6, 5*mm, fill=1, stroke=0)

            c.setFillColor(colors.HexColor(bg))
            c.setStrokeColor(colors.HexColor(COLOR_BORDER))
            c.setLineWidth(0.9)
            c.roundRect(x, y_top - bh, bw, bh, 5*mm, fill=1, stroke=1)

            c.setLineWidth(0.5)
            c.setStrokeColor(colors.black)

        def pill(x, y, text, bg="#eef2ff", fg=COLOR_PRIMARY, wmm=88):
            c.setFillColor(colors.HexColor("#e5e7eb"))
            c.roundRect(x - 0.6, y - 0.6, wmm*mm, 8*mm, 4*mm, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(bg))
            c.roundRect(x, y, wmm*mm, 8*mm, 4*mm, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(fg))
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x + 4*mm, y + 2.2*mm, ellipsize(text, (wmm*mm) - 8*mm, "Helvetica-Bold", 9))
            c.setFillColor(colors.black)

        def line(x1, y, x2):
            c.setStrokeColor(colors.HexColor(COLOR_BORDER))
            c.setLineWidth(0.9)
            c.line(x1, y, x2, y)
            c.setLineWidth(0.5)
            c.setStrokeColor(colors.black)

        def section_title(x, y, t):
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.HexColor(COLOR_TEXT))
            c.drawString(x, y, t)
            c.setStrokeColor(colors.HexColor(COLOR_PRIMARY))
            c.setLineWidth(1.2)
            c.line(x, y - 2*mm, x + 28*mm, y - 2*mm)
            c.setLineWidth(0.5)
            c.setFillColor(colors.black)

        def kv(x, y, label, value, max_w=72*mm, highlight=False):
            c.setFont("Helvetica", 7.5)
            c.setFillColor(colors.HexColor(COLOR_MUTED))
            c.drawString(x, y, str(label).upper())

            c.setFont("Helvetica-Bold" if highlight else "Helvetica", 10 if highlight else 9)
            c.setFillColor(colors.HexColor(COLOR_ACCENT if highlight else COLOR_TEXT))
            c.drawString(x, y - 4*mm, ellipsize(value, max_w, "Helvetica-Bold" if highlight else "Helvetica", 10 if highlight else 9))
            c.setFillColor(colors.black)

        def draw_table(x, y_top, col_w, rows, row_h=7*mm):
            """
            Table simple (header + body)
            y_top = haut de la table
            """
            headers = ["Mois", "Montant", "Date"]
            # header
            c.setFont("Helvetica-Bold", 9)
            curx = x
            for i, head in enumerate(headers):
                c.setFillColor(colors.HexColor(COLOR_SOFT))
                c.setStrokeColor(colors.HexColor(COLOR_BORDER))
                c.rect(curx, y_top - row_h, col_w[i], row_h, fill=1, stroke=1)
                c.setFillColor(colors.HexColor(COLOR_TEXT))
                c.drawString(curx + 2*mm, y_top - row_h + 2.2*mm, head)
                curx += col_w[i]

            # body
            c.setFont("Helvetica", 9)
            y = y_top - row_h
            for r in rows:
                y -= row_h
                curx = x
                for i, cell in enumerate(r):
                    c.setFillColor(colors.white)
                    c.setStrokeColor(colors.HexColor(COLOR_BORDER))
                    c.rect(curx, y, col_w[i], row_h, fill=1, stroke=1)
                    c.setFillColor(colors.HexColor(COLOR_TEXT))
                    c.drawString(curx + 2*mm, y + 2.2*mm, ellipsize(cell, col_w[i] - 4*mm, "Helvetica", 9))
                    curx += col_w[i]
            c.setFillColor(colors.black)
            return y

        # Construire rows
        rows = []
        for p in paiements_qs:
            mois = "—"
            if getattr(p, "echeance_id", None) and getattr(p.echeance, "mois_nom", None):
                mois = p.echeance.mois_nom
            rows.append([
                str(mois),
                f"{p.montant} MAD",
                str(getattr(p, "date_paiement", "—")),
            ])

        def draw_batch_receipt(y_top):
            margin_x = 15*mm
            receipt_w = w - 2*margin_x
            receipt_h = 128*mm

            modern_box(margin_x, y_top, receipt_w, receipt_h, bg="#ffffff")

            # header
            if logo_img:
                c.drawImage(logo_img, margin_x + 10*mm, y_top - 22*mm, width=18*mm, height=18*mm, mask="auto")

            c.setFont("Helvetica-Bold", 15)
            c.setFillColor(colors.HexColor(COLOR_PRIMARY))
            c.drawString(margin_x + 31*mm, y_top - 13*mm, "REÇU BATCH (MULTI-MOIS)")

            c.setFont("Helvetica", 8.5)
            c.setFillColor(colors.HexColor(COLOR_MUTED))
            c.drawString(margin_x + 31*mm, y_top - 18*mm, "Groupe Scolaire AZ • Paiement groupé")
            c.setFillColor(colors.black)

            pill(margin_x + receipt_w - 94*mm, y_top - 23*mm, code_recu, bg="#f5f3ff", fg=COLOR_ACCENT, wmm=88)
            pill(margin_x + receipt_w - 94*mm, y_top - 33*mm, f"Mode: {mode_value}", bg="#eef2ff", fg=COLOR_PRIMARY, wmm=88)

            line(margin_x + 10*mm, y_top - 36*mm, margin_x + receipt_w - 10*mm)

            left_x = margin_x + 12*mm
            right_x = margin_x + receipt_w/2 + 8*mm

            section_title(left_x, y_top - 44*mm, "ÉLÈVE")
            kv(left_x, y_top - 50*mm, "Matricule", getattr(eleve, "matricule", "—"), highlight=True)
            kv(left_x + 48*mm, y_top - 50*mm, "Nom", f"{getattr(eleve,'nom','')} {getattr(eleve,'prenom','')}")
            kv(left_x, y_top - 66*mm, "Année", getattr(insc.annee, "nom", "—"))
            kv(left_x + 48*mm, y_top - 66*mm, "Groupe", f"{getattr(insc.groupe,'nom','—')}")

            section_title(right_x, y_top - 44*mm, "BATCH")
            kv(right_x, y_top - 50*mm, "Token", str(batch_token)[:18], max_w=72*mm)
            kv(right_x, y_top - 66*mm, "Total", f"{total_batch} MAD", highlight=True)

            line(margin_x + 10*mm, y_top - 76*mm, margin_x + receipt_w - 10*mm)

            section_title(left_x, y_top - 84*mm, "DÉTAILS MOIS")
            table_top = y_top - 90*mm
            col_w = [45*mm, 35*mm, 35*mm]  # Mois, Montant, Date
            y_end = draw_table(left_x, table_top, col_w, rows, row_h=7*mm)

            # Accès portail
            line(margin_x + 10*mm, y_end - 6*mm, margin_x + receipt_w - 10*mm)
            section_title(left_x, y_end - 14*mm, "ACCÈS PORTAIL")
            c.setFont("Helvetica", 8.5)
            c.setFillColor(colors.HexColor(COLOR_TEXT))
            c.drawString(left_x, y_end - 20*mm, f"Site : {portal_url}")
            c.drawString(left_x, y_end - 26*mm, f"Login : {login}")
            c.drawString(right_x, y_end - 20*mm, f"Mot de passe : {pwd}")
            c.setFillColor(colors.black)

        # 2 copies sur la même page
        top_y = h - 10*mm
        draw_batch_receipt(top_y)

        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.setDash(3, 3)
        c.line(15*mm, h/2, w - 15*mm, h/2)
        c.setDash()

        bottom_y = (h/2) - 5*mm
        draw_batch_receipt(bottom_y)

    return pdf_response(f"recu_batch_{batch_token}.pdf", draw)


def absences_jour_pdf(date_str, annee, groupe_label, absences):
    def draw(c):
        subtitle = f"Date : {date_str}"
        if annee:
            subtitle += f" — Année : {annee.nom}"
        if groupe_label:
            subtitle += f" — Groupe : {groupe_label}"

        _header(c, "Absences du jour", subtitle)

        w, h = A4
        y = h - 38 * mm

        cols = ["Élève", "Type", "Séance", "Justifié", "Motif"]
        col_widths = [55*mm, 18*mm, 40*mm, 18*mm, 45*mm]

        rows = []
        for a in absences:
            seance = "—"
            if a.seance:
                seance = f"{a.seance.get_jour_display()} {a.seance.heure_debut}-{a.seance.heure_fin}"
            rows.append([
                f"{a.eleve.matricule} {a.eleve.nom} {a.eleve.prenom}",
                a.get_type_display(),
                seance,
                "Oui" if a.justifie else "Non",
                a.motif or "—"
            ])

        if not rows:
            c.setFont("Helvetica", 10)
            c.drawString(18*mm, y, "Aucune absence.")
            _footer(c)
            return

        y_end = _table(c, 18*mm, y, cols, rows[:22], col_widths)  # 1 page simple
        _footer(c)

    safe_date = date_str.replace("-", "")
    return pdf_response(f"absences_{safe_date}.pdf", draw)


def impayes_pdf(annee, inscriptions, total_du, total_encaisse, total_impaye):
    def draw(c):
        subtitle = f"Année : {annee.nom}" if annee else "Année : —"
        _header(c, "Impayés", subtitle)

        w, h = A4
        y = h - 38 * mm

        c.setFont("Helvetica", 9)
        c.drawString(18*mm, y, f"Total dû : {total_du} MAD")
        y -= 6*mm
        c.drawString(18*mm, y, f"Total encaissé : {total_encaisse} MAD")
        y -= 6*mm
        c.drawString(18*mm, y, f"Total impayé : {total_impaye} MAD")
        y -= 10*mm

        cols = ["Élève", "Groupe", "Total", "Payé", "Reste"]
        col_widths = [55*mm, 55*mm, 20*mm, 20*mm, 20*mm]

        rows = []
        for insc in inscriptions:
            total = insc.montant_total or Decimal("0.00")
            paye = getattr(insc, "total_paye", Decimal("0.00")) or Decimal("0.00")
            reste = total - paye
            if reste <= 0:
                continue
            rows.append([
                f"{insc.eleve.matricule} {insc.eleve.nom} {insc.eleve.prenom}",
                f"{insc.groupe.niveau.nom} {insc.groupe.nom}",
                f"{total}",
                f"{paye}",
                f"{reste}",
            ])

        if not rows:
            c.setFont("Helvetica", 10)
            c.drawString(18*mm, y, "Aucun impayé.")
            _footer(c)
            return

        _table(c, 18*mm, y, cols, rows[:22], col_widths)
        _footer(c)

    return pdf_response("impayes.pdf", draw)


def eleves_list_pdf(title, eleves):
    def draw(c):
        _header(c, "Liste des élèves", title)

        w, h = A4
        y = h - 38 * mm

        cols = ["Matricule", "Nom", "Prénom", "Téléphone", "Actif"]
        col_widths = [30*mm, 45*mm, 45*mm, 40*mm, 18*mm]

        rows = []
        for e in eleves:
            rows.append([
                e.matricule,
                e.nom,
                e.prenom,
                e.telephone or "—",
                "Oui" if e.is_active else "Non"
            ])

        if not rows:
            c.setFont("Helvetica", 10)
            c.drawString(18*mm, y, "Aucun élève.")
            _footer(c)
            return

        _table(c, 18*mm, y, cols, rows[:22], col_widths)
        _footer(c)

    return pdf_response("eleves.pdf", draw)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors

def bulletin_pdf(eleve, periode, data, groupe=None, rank=None, effectif=None, moyenne_classe=None):
    def draw(c):
        subtitle = f"Période : {periode.nom} — Année : {periode.annee.nom}"
        _header(c, "Bulletin de notes", subtitle)

        w, h = A4
        y = h - 38 * mm

        # Identité élève
        c.setFont("Helvetica-Bold", 10)
        c.drawString(18*mm, y, "Élève")
        y -= 8*mm

        c.setFont("Helvetica", 9)
        c.drawString(18*mm, y, f"Matricule : {eleve.matricule}")
        y -= 6*mm
        c.drawString(18*mm, y, f"Nom : {eleve.nom} {eleve.prenom}")
        y -= 6*mm

        if groupe:
            c.drawString(18*mm, y, f"Groupe : {groupe.nom}")
            y -= 6*mm

        if rank and effectif:
            c.drawString(18*mm, y, f"Rang : {rank} / {effectif}")
            y -= 6*mm

        # ✅ Moyenne de classe (optionnelle)
        if moyenne_classe is not None:
            c.drawString(18*mm, y, f"Moyenne de la classe : {moyenne_classe:.2f} / 20")
            y -= 6*mm

        y -= 6*mm

        rows = data.get("rows", [])
        if not rows:
            c.setFont("Helvetica", 10)
            c.drawString(18*mm, y, "Aucune note disponible pour cette période.")
            _footer(c)
            return

        # Table notes (avec coef)
        cols = ["Matière", "Coef", "Moyenne / 20"]
        col_widths = [95*mm, 20*mm, 45*mm]

        table_rows = []
        for r in rows:
            table_rows.append([r["matiere"], f'{r["coef"]:.2f}', f'{r["moyenne"]:.2f}'])

        y_end = _table(c, 18*mm, y, cols, table_rows[:22], col_widths)
        y = y_end - 10*mm

        # Moyenne générale
        mg = data.get("moyenne_generale")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(
            18*mm, y,
            f"Moyenne générale pondérée : {mg:.2f} / 20" if mg is not None else "Moyenne générale pondérée : —"
        )

        y -= 14*mm
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.grey)
        c.drawString(18*mm, y, "Signature / Cachet : ________________________________")
        c.setFillColor(colors.black)

        _footer(c)

    safe_name = eleve.matricule.replace("/", "_")
    return pdf_response(f"bulletin_{safe_name}_{periode.id}.pdf", draw)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors

def absences_eleve_pdf(eleve, annee, absences, title="Historique des absences"):
    """
    PDF liste absences d'un élève (multi-lignes).
    Simple 1 page (les 22 premières lignes).
    """
    def draw(c):
        subtitle = f"Élève : {eleve.matricule} — {eleve.nom} {eleve.prenom}"
        if annee:
            subtitle += f" — Année : {annee.nom}"
        _header(c, title, subtitle)

        w, h = A4
        y = h - 38 * mm

        cols = ["Date", "Type", "Séance", "Justifié", "Motif"]
        col_widths = [22*mm, 20*mm, 45*mm, 18*mm, 75*mm]

        rows = []
        for a in absences:
            seance = "—"
            if a.seance:
                seance = f"{a.seance.get_jour_display()} {a.seance.heure_debut}-{a.seance.heure_fin}"
            rows.append([
                str(a.date),
                a.get_type_display(),
                seance,
                "Oui" if a.justifie else "Non",
                a.motif or "—"
            ])

        if not rows:
            c.setFont("Helvetica", 10)
            c.drawString(18*mm, y, "Aucune absence.")
            _footer(c)
            return

        _table(c, 18*mm, y, cols, rows[:22], col_widths)
        _footer(c)

    safe = eleve.matricule.replace("/", "_")
    return pdf_response(f"absences_{safe}.pdf", draw)
