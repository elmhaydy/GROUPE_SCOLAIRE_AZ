# core/pdf/transaction.py
from io import BytesIO
from decimal import Decimal
from datetime import datetime

from django.contrib.staticfiles import finders
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from core.models import TempPassword


# =========================
# Utils
# =========================
def _D(x):
    try:
        return Decimal(str(x or "0").replace(",", "."))
    except Exception:
        return Decimal("0.00")


def _money(x):
    return f"{_D(x):.2f} MAD"


def _ellipsize(text, max_w, font="Helvetica", size=9):
    s = str(text or "")
    if stringWidth(s, font, size) <= max_w:
        return s
    while s and stringWidth(s + "…", font, size) > max_w:
        s = s[:-1]
    return (s + "…") if s else ""


def _card(c, x, y_top, w, h, bg="#ffffff"):
    c.setFillColor(colors.HexColor("#e5e7eb"))
    c.roundRect(x - 0.8, y_top - h - 0.8, w + 1.6, h + 1.6, 6 * mm, fill=1, stroke=0)

    c.setFillColor(colors.HexColor(bg))
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.setLineWidth(0.9)
    c.roundRect(x, y_top - h, w, h, 6 * mm, fill=1, stroke=1)

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)


def _line(c, x1, y, x2, color_hex="#e2e8f0", lw=0.9):
    c.setStrokeColor(colors.HexColor(color_hex))
    c.setLineWidth(lw)
    c.line(x1, y, x2, y)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)


def _pill(c, x, y, text, wmm=76, bg="#eef2ff", fg="#4f46e5"):
    c.setFillColor(colors.HexColor(bg))
    c.roundRect(x, y, wmm * mm, 8 * mm, 4 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(fg))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 4 * mm, y + 2.2 * mm, _ellipsize(text, (wmm * mm) - 8 * mm, "Helvetica-Bold", 9))
    c.setFillColor(colors.black)


def _section(c, x, y, t, accent="#4f46e5"):
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawString(x, y, t)
    c.setStrokeColor(colors.HexColor(accent))
    c.setLineWidth(1.2)
    c.line(x, y - 2 * mm, x + 26 * mm, y - 2 * mm)
    c.setLineWidth(0.5)
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)


def _kv(c, x, y, label, value, max_w=75 * mm, highlight=False):
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(x, y, str(label).upper())

    c.setFont("Helvetica-Bold" if highlight else "Helvetica", 10 if highlight else 9)
    c.setFillColor(colors.HexColor("#4f46e5" if highlight else "#0f172a"))
    c.drawString(
        x,
        y - 4 * mm,
        _ellipsize(value, max_w, "Helvetica-Bold" if highlight else "Helvetica", 10 if highlight else 9),
    )
    c.setFillColor(colors.black)


def _table(c, x, y_top, col_ws, headers, rows, row_h):
    # header
    c.setFont("Helvetica-Bold", 9)
    curx = x
    for i, head in enumerate(headers):
        c.setFillColor(colors.HexColor("#f8fafc"))
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.rect(curx, y_top - row_h, col_ws[i], row_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.drawString(curx + 2 * mm, y_top - row_h + 2.0 * mm, _ellipsize(head, col_ws[i] - 4 * mm, "Helvetica-Bold", 9))
        curx += col_ws[i]

    # body
    c.setFont("Helvetica", 9)
    y = y_top - row_h
    for r in rows:
        y -= row_h
        curx = x
        for i, cell in enumerate(r):
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.HexColor("#e2e8f0"))
            c.rect(curx, y, col_ws[i], row_h, fill=1, stroke=1)
            c.setFillColor(colors.HexColor("#0f172a"))
            c.drawString(curx + 2 * mm, y + 2.0 * mm, _ellipsize(cell, col_ws[i] - 4 * mm, "Helvetica", 9))
            curx += col_ws[i]

    c.setFillColor(colors.black)
    return y


# =========================
# Smart rows
# =========================
def _months_compact(months):
    months = [m for m in months if m and m != "—"]
    if not months:
        return ""
    s = ", ".join(months)
    if len(s) <= 60:
        return s
    return f"{months[0]} → {months[-1]} ({len(months)} mois)"


def _split_lines(tx):
    lignes_qs = getattr(tx, "lignes", None)
    lignes = list(lignes_qs.all()) if hasattr(lignes_qs, "all") else (list(lignes_qs) if lignes_qs else [])

    ins_lines, sco_lines, tr_lines, other_lines = [], [], [], []
    for ln in lignes:
        if getattr(ln, "echeance_id", None):
            sco_lines.append(ln)
        elif getattr(ln, "echeance_transport_id", None):
            tr_lines.append(ln)
        elif (getattr(ln, "echeance", None) is None) and (getattr(ln, "echeance_transport", None) is None):
            ins_lines.append(ln)
        else:
            other_lines.append(ln)

    return lignes, ins_lines, sco_lines, tr_lines, other_lines


def _rows_summary(tx, hard_max_rows=21):
    _, ins_lines, sco_lines, tr_lines, other_lines = _split_lines(tx)

    row_ins = None
    row_sco = None
    row_tr = None
    rows_other = []

    ins_total = sum((_D(getattr(x, "montant", None)) for x in ins_lines), Decimal("0.00"))
    if ins_total > 0:
        row_ins = ["—", "Frais d'inscription", _money(ins_total)]

    if sco_lines:
        months, sco_total = [], Decimal("0.00")
        for x in sco_lines:
            e = getattr(x, "echeance", None)
            months.append(getattr(e, "mois_nom", "—"))
            sco_total += _D(getattr(x, "montant", None))
        suffix = _months_compact(months)
        lib = f"Scolarité ({len(sco_lines)} mois)"
        if suffix:
            lib = f"{lib} — {suffix}"
        row_sco = ["—", lib, _money(sco_total)]

    if tr_lines:
        months, tr_total = [], Decimal("0.00")
        for x in tr_lines:
            e = getattr(x, "echeance_transport", None)
            months.append(getattr(e, "mois_nom", "—"))
            tr_total += _D(getattr(x, "montant", None))
        suffix = _months_compact(months)
        lib = f"Transport ({len(tr_lines)} mois)"
        if suffix:
            lib = f"{lib} — {suffix}"
        row_tr = ["—", lib, _money(tr_total)]

    for x in other_lines[:5]:
        lib = (getattr(x, "libelle", "") or "Autre").strip()
        rows_other.append(["—", lib, _money(_D(getattr(x, "montant", None)))])

    # ✅ ordre lisible
    rows = []
    if row_ins:
        rows.append(row_ins)
    if row_sco:
        rows.append(row_sco)
    if row_tr:
        rows.append(row_tr)
    rows.extend(rows_other)

    return rows[:hard_max_rows]


def _rows_detailed(tx, hard_max_rows=21):
    lignes, _, _, _, _ = _split_lines(tx)

    rows = []
    for ln in lignes[:hard_max_rows]:
        if getattr(ln, "echeance_id", None):
            mois = getattr(getattr(ln, "echeance", None), "mois_nom", "—")
            lib = (getattr(ln, "libelle", "") or f"Scolarité — {mois}")
        elif getattr(ln, "echeance_transport_id", None):
            mois = getattr(getattr(ln, "echeance_transport", None), "mois_nom", "—")
            lib = (getattr(ln, "libelle", "") or f"Transport — {mois}")
        else:
            mois = "—"
            lib = (getattr(ln, "libelle", "") or "Frais d'inscription")

        rows.append([str(mois), str(lib), _money(_D(getattr(ln, "montant", None)))])
    return rows


def _build_rows_for_fit(tx, max_rows_fit, hard_max_rows=21):
    """
    Si le détaillé ne rentre pas, on bascule sur le résumé (ins/sco/tr).
    """
    tx_type = (getattr(tx, "type_transaction", "") or "").upper()
    detailed = _rows_detailed(tx, hard_max_rows=hard_max_rows)

    if tx_type == "PACK" or len(detailed) > 8:
        return _rows_summary(tx, hard_max_rows=hard_max_rows)

    if len(detailed) > max_rows_fit:
        return _rows_summary(tx, hard_max_rows=hard_max_rows)

    return detailed


def _pick_shown_rows(table_rows, max_rows_fit):
    """
    ✅ Priorité en cas de coupe:
    1) Scolarité
    2) Transport
    3) Frais d'inscription
    4) Autres
    """
    if len(table_rows) <= max_rows_fit:
        return table_rows

    def kind(row):
        lib = str(row[1] or "")
        if "Scolarité" in lib:
            return 0
        if "Transport" in lib:
            return 1
        if "Frais d'inscription" in lib:
            return 2
        return 3

    ordered = sorted(table_rows, key=kind)

    # Si on n'a que 2 lignes possibles et qu'on a sco+tr+ins,
    # on garde sco + tr (plus important) et on laisse tomber inscription.
    if max_rows_fit == 2:
        has_sco = any("Scolarité" in str(r[1]) for r in table_rows)
        has_tr = any("Transport" in str(r[1]) for r in table_rows)
        if has_sco and has_tr:
            sco = next((r for r in ordered if "Scolarité" in str(r[1])), None)
            tr = next((r for r in ordered if "Transport" in str(r[1])), None)
            kept = [x for x in [sco, tr] if x]
            return kept[:2]

    return ordered[:max_rows_fit]


# =========================
# PDF builder
# =========================
def build_transaction_pdf_bytes(tx) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    COLOR_PRIMARY = "#4f46e5"
    COLOR_ACCENT = "#a855f7"
    COLOR_BORDER = "#e2e8f0"
    COLOR_SOFT = "#f8fafc"

    logo_img = None
    logo_path = finders.find("img/logo_AZ.png")
    if logo_path:
        try:
            logo_img = ImageReader(logo_path)
        except Exception:
            logo_img = None

    blur_img = None
    blur_path = finders.find("img/logo_AZ_blur.png")
    if blur_path:
        try:
            blur_img = ImageReader(blur_path)
        except Exception:
            blur_img = None

    insc = tx.inscription
    eleve = insc.eleve
    annee = insc.annee
    groupe = insc.groupe
    niveau = getattr(groupe, "niveau", None)
    degre = getattr(niveau, "degre", None)

    created = getattr(tx, "created_at", None) or getattr(tx, "date_transaction", None) or datetime.now()
    date_txt = created.strftime("%Y-%m-%d %H:%M")
    code = f"AZ-TX-{created.year}-{tx.id:06d}"

    type_label = getattr(tx, "get_type_transaction_display", None)
    type_value = type_label() if callable(type_label) else (getattr(tx, "type_transaction", None) or "—")

    mode_label = getattr(tx, "get_mode_display", None)
    mode_value = mode_label() if callable(mode_label) else (getattr(tx, "mode", None) or "—")

    reference = getattr(tx, "reference", "") or "—"
    total = _D(getattr(tx, "montant_total", None))

    portal_url = "https://groupescolaireaz.cloud/"
    login = getattr(eleve, "matricule", "—")
    pwd = "—"
    user = getattr(eleve, "user", None)
    if user:
        tp = TempPassword.objects.filter(user=user).first()
        if tp and tp.password:
            pwd = tp.password

    def draw_one(y_top):
        margin_x = 12 * mm
        card_w = w - 2 * margin_x
        card_h = 134 * mm

        _card(c, margin_x, y_top, card_w, card_h)

        # header bandeau
        c.setFillColor(colors.HexColor(COLOR_SOFT))
        c.roundRect(margin_x, y_top - 18 * mm, card_w, 18 * mm, 6 * mm, fill=1, stroke=0)
        c.setFillColor(colors.black)

        if logo_img:
            c.drawImage(logo_img, margin_x + 9 * mm, y_top - 15.2 * mm, width=12 * mm, height=12 * mm, mask="auto")

        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor(COLOR_PRIMARY))
        c.drawString(margin_x + 24 * mm, y_top - 8.0 * mm, "REÇU DE TRANSACTION")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawString(margin_x + 24 * mm, y_top - 13.0 * mm, "Groupe Scolaire AZ • Finance")
        c.setFillColor(colors.black)

        _pill(c, margin_x + card_w - 92 * mm, y_top - 14.5 * mm, code, wmm=80, bg="#f5f3ff", fg=COLOR_ACCENT)
        _pill(c, margin_x + card_w - 92 * mm, y_top - 24.5 * mm, str(type_value), wmm=80, bg="#eef2ff", fg=COLOR_PRIMARY)

        # watermark
        if blur_img or logo_img:
            try:
                c.saveState()
                c.setFillAlpha(0.06)
                wm = blur_img if blur_img else logo_img
                wm_w = 92 * mm
                wm_h = 92 * mm
                cx = margin_x + (card_w - wm_w) / 2
                cy = (y_top - card_h) + (card_h - wm_h) / 2
                c.drawImage(wm, cx, cy, width=wm_w, height=wm_h, mask="auto")
                c.restoreState()
            except Exception:
                pass

        _line(c, margin_x + 10 * mm, y_top - 28 * mm, margin_x + card_w - 10 * mm, COLOR_BORDER)

        left_x = margin_x + 12 * mm
        right_x = margin_x + (card_w / 2) + 6 * mm

        # élève
        _section(c, left_x, y_top - 36 * mm, "ÉLÈVE", accent=COLOR_PRIMARY)
        _kv(c, left_x, y_top - 42 * mm, "Matricule", getattr(eleve, "matricule", "—"), highlight=True)
        _kv(
            c,
            left_x + 48 * mm,
            y_top - 42 * mm,
            "Nom",
            f"{getattr(eleve,'nom','—')} {getattr(eleve,'prenom','')}".strip(),
            max_w=70 * mm,
        )

        cls = f"{getattr(degre,'nom','—')} • {getattr(niveau,'nom','—')} • {getattr(groupe,'nom','—')}"
        _kv(c, left_x, y_top - 58 * mm, "Année", getattr(annee, "nom", "—"))
        _kv(c, left_x + 48 * mm, y_top - 58 * mm, "Classe", cls, max_w=75 * mm)

        # paiement
        _section(c, right_x, y_top - 36 * mm, "PAIEMENT", accent=COLOR_PRIMARY)
        _kv(c, right_x, y_top - 42 * mm, "Date", date_txt, max_w=60 * mm)
        _kv(c, right_x + 48 * mm, y_top - 42 * mm, "Mode", mode_value, max_w=45 * mm)
        _kv(c, right_x, y_top - 58 * mm, "Référence", reference, max_w=60 * mm)
        _kv(c, right_x + 48 * mm, y_top - 58 * mm, "Total", _money(total), highlight=True, max_w=45 * mm)

        _line(c, margin_x + 10 * mm, y_top - 66 * mm, margin_x + card_w - 10 * mm, COLOR_BORDER)

        # détails
        _section(c, left_x, y_top - 74 * mm, "DÉTAILS", accent=COLOR_PRIMARY)

        headers = ["Mois", "Libellé", "Montant payé"]
        col_ws = [28 * mm, 92 * mm, 32 * mm]
        table_top = y_top - 78 * mm

        # ✅ plus compact => plus de lignes affichées
        row_h = 6.2 * mm

        footer_y = (y_top - card_h) + 8 * mm

        # ✅ portail compact (1 seule ligne utile) => + place tableau
        portal_h = 12.5 * mm
        safe_bottom = footer_y + 11 * mm + portal_h

        max_rows_fit = int(max(1, (table_top - safe_bottom) / row_h))

        table_rows = _build_rows_for_fit(tx, max_rows_fit=max_rows_fit, hard_max_rows=21)
        shown = _pick_shown_rows(table_rows, max_rows_fit)

        _table(c, left_x, table_top, col_ws, headers, shown, row_h=row_h)

        # accès portail (compact)
        box_w = card_w - 24 * mm
        box_x = left_x
        box_y_top = safe_bottom

        c.setFillColor(colors.HexColor("#f8fafc"))
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.roundRect(box_x, box_y_top - portal_h, box_w, portal_h, 6 * mm, fill=1, stroke=1)

        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(box_x + 6 * mm, box_y_top - 6.4 * mm, "ACCÈS PORTAIL")

        c.setFont("Helvetica", 9)
        # ✅ tout sur 1 ligne (gain de place)
        c.drawString(box_x + 6 * mm, box_y_top - 10.6 * mm, f"Site : {portal_url}   |   Login : {login}")
        c.drawRightString(box_x + box_w - 6 * mm, box_y_top - 10.6 * mm, f"Mot de passe : {pwd}")

        # footer
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawString(left_x, footer_y, "Signature / Cachet : _________________________________")
        c.drawRightString(margin_x + card_w - 12 * mm, footer_y, "Groupe Scolaire AZ")
        c.setFillColor(colors.black)

    # 2 copies sur 1 page A4
    top_y = h - 10 * mm
    draw_one(top_y)

    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setDash(3, 3)
    c.line(12 * mm, h / 2, w - 12 * mm, h / 2)
    c.setDash()
    c.setStrokeColor(colors.black)

    bottom_y = (h / 2) - 5 * mm
    draw_one(bottom_y)

    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
