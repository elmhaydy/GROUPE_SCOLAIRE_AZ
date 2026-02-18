# core/pdf/transaction.py
from io import BytesIO
from decimal import Decimal
from datetime import datetime
from collections import defaultdict

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
    """
    ⚠️ Utilisé UNIQUEMENT pour des champs non critiques (jamais pour les mois).
    """
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


# =========================
# No-ellipsis months wrapping
# =========================
MONTH_ABBR = {
    "Janvier": "Jan", "Février": "Fév", "Fevrier": "Fév", "Mars": "Mar", "Avril": "Avr",
    "Mai": "Mai", "Juin": "Jun", "Juillet": "Jul", "Août": "Aoû", "Aout": "Aoû",
    "Septembre": "Sep", "Octobre": "Oct", "Novembre": "Nov", "Décembre": "Déc", "Decembre": "Déc",
}


def _mabbr(m):
    m = (m or "").strip()
    return MONTH_ABBR.get(m, m[:3] if len(m) > 3 else m)


def _months_tokens_unique(months):
    toks = [_mabbr(m) for m in (months or []) if m and m != "—"]
    out, seen = [], set()
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _split_tokens_to_lines(tokens, max_w, font="Helvetica", size=7.6, max_lines=4):
    """
    Split tokens in lines WITHOUT cutting tokens and WITHOUT ellipsis.
    tokens: ["Sep","Oct","Nov",...]
    return list[str]
    """
    if not tokens:
        return ["—"]

    lines = []
    cur = ""

    for t in tokens:
        cand = (cur + "," + t) if cur else t
        if stringWidth(cand, font, size) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = t
            if len(lines) >= max_lines:
                # stop adding more lines => caller MUST paginate (we won't cut)
                return lines

    if cur:
        lines.append(cur)

    return lines


# =========================
# Helpers (modes + recu + login)
# =========================
def _mode_value(tx):
    mode_label = getattr(tx, "get_mode_display", None)
    if callable(mode_label):
        return str(mode_label() or "—")
    return str(getattr(tx, "mode", None) or "—")


def _paiement_ref_value(tx):
    return str(getattr(tx, "reference", "") or "—")


def _recu_seq_value(tx, txs=None):
    seq = getattr(tx, "receipt_seq", None)
    if seq:
        try:
            return int(seq)
        except Exception:
            pass
    if txs:
        for t in txs:
            s = getattr(t, "receipt_seq", None)
            if s:
                try:
                    return int(s)
                except Exception:
                    continue
    return None


def _recu_value(tx, batch_token: str = "", txs=None):
    for attr in ("numero_recu", "recu_numero", "receipt_no", "receipt_number", "code_recu"):
        v = getattr(tx, attr, None)
        if v:
            return str(v)

    dt = getattr(tx, "created_at", None) or getattr(tx, "date_transaction", None) or datetime.now()
    year = dt.year

    seq = _recu_seq_value(tx, txs=txs)
    if seq is not None:
        return f"AZ-PAY-{year}-{seq:04d}"

    return f"AZ-PAY-{year}-TEMP"


def _login_pwd_from_inscription(insc):
    eleve = insc.eleve
    login = str(getattr(eleve, "matricule", "—") or "—")
    pwd = "—"
    user = getattr(eleve, "user", None)
    if user:
        tp = TempPassword.objects.filter(user=user).first()
        if tp and tp.password:
            pwd = str(tp.password)
    return login, pwd


# =========================
# Build compact rows (but full months, no loss)
# rows => [EleveLabel, Type, MonthsTokens(list), Total]
# =========================
def _extract_ln_kind_and_month(ln):
    amount = _D(getattr(ln, "montant", None))

    e1 = getattr(ln, "echeance", None)
    if e1 and getattr(e1, "mois_nom", None):
        return ("SCOL", str(e1.mois_nom), amount)

    e2 = getattr(ln, "echeance_transport", None)
    if e2 and getattr(e2, "mois_nom", None):
        return ("TR", str(e2.mois_nom), amount)

    lib = (getattr(ln, "libelle", "") or "").lower()
    if "inscription" in lib or "inscri" in lib:
        return ("INS", "", amount)

    return ("AUT", "", amount)


def _rows_for_inscription(insc, lignes):
    """
    Retourne plusieurs lignes par élève:
      - INS (si existe)
      - SCOL (mois listés)
      - TR (mois listés)
      - AUT (si existe)
    Eleve label = Nom + (NIVEAU)
    """
    eleve = insc.eleve
    grp = getattr(insc, "groupe", None)
    niv = getattr(grp, "niveau", None) if grp else None
    niveau_name = getattr(niv, "nom", "—")

    nom = f"{getattr(eleve,'nom','—')} {getattr(eleve,'prenom','')}".strip()
    eleve_label = f"{nom} ({niveau_name})"

    buckets = {
        "INS": {"months": [], "sum": Decimal("0.00")},
        "SCOL": {"months": [], "sum": Decimal("0.00")},
        "TR": {"months": [], "sum": Decimal("0.00")},
        "AUT": {"months": [], "sum": Decimal("0.00")},
    }

    for ln in lignes:
        kind, month, amount = _extract_ln_kind_and_month(ln)
        if kind not in buckets:
            kind = "AUT"
        buckets[kind]["sum"] += amount
        if month:
            buckets[kind]["months"].append(month)

    out = []
    first = True
    for kind in ("INS", "SCOL", "TR", "AUT"):
        s = buckets[kind]["sum"]
        if s <= 0:
            continue

        tokens = []
        if kind in ("SCOL", "TR"):
            tokens = _months_tokens_unique(buckets[kind]["months"])

        label = kind
        if kind == "INS":
            label = "INSCRIPTION"
        elif kind == "SCOL":
            label = "SCOLARITÉ"
        elif kind == "TR":
            label = "TRANSPORT"
        out.append([ eleve_label if first else "", label, tokens, _money(s) ])
        first = False

    return out


def _build_rows_and_portal_from_transactions(transactions):
    insc_map = defaultdict(list)
    for tx in transactions:
        insc_map[tx.inscription].append(tx)

    rows = []
    portal_rows = []
    for insc, txs in insc_map.items():
        lignes = []
        for tx in txs:
            qs = getattr(tx, "lignes", None)
            if hasattr(qs, "all"):
                lignes.extend(list(qs.all()))
            elif qs:
                lignes.extend(list(qs))

        rows.extend(_rows_for_inscription(insc, lignes))
        portal_rows.append(list(_login_pwd_from_inscription(insc)))

    return rows, portal_rows


# =========================
# Images
# =========================
def _load_images():
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

    return logo_img, blur_img


def _draw_common_header(c, x, y_top, w_card, h_card, title, code, badge):
    COLOR_PRIMARY = "#4f46e5"
    COLOR_ACCENT = "#a855f7"
    COLOR_BORDER = "#e2e8f0"
    COLOR_SOFT = "#f8fafc"

    logo_img, blur_img = _load_images()

    c.setFillColor(colors.HexColor(COLOR_SOFT))
    c.roundRect(x, y_top - 18 * mm, w_card, 18 * mm, 6 * mm, fill=1, stroke=0)

    if logo_img:
        c.drawImage(logo_img, x + 9 * mm, y_top - 15.2 * mm, width=12 * mm, height=12 * mm, mask="auto")

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor(COLOR_PRIMARY))
    c.drawString(x + 24 * mm, y_top - 8.0 * mm, title)

    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(x + 24 * mm, y_top - 13.0 * mm, "Groupe Scolaire AZ • Finance")

    _pill(c, x + w_card - 92 * mm, y_top - 14.5 * mm, code, wmm=80, bg="#f5f3ff", fg=COLOR_ACCENT)
    _pill(c, x + w_card - 92 * mm, y_top - 24.5 * mm, badge, wmm=80, bg="#eef2ff", fg=COLOR_PRIMARY)

    # watermark
    if blur_img or logo_img:
        try:
            c.saveState()
            c.setFillAlpha(0.06)
            wm = blur_img if blur_img else logo_img
            wm_w = 92 * mm
            wm_h = 92 * mm
            cx = x + (w_card - wm_w) / 2
            cy = (y_top - h_card) + (h_card - wm_h) / 2
            c.drawImage(wm, cx, cy, width=wm_w, height=wm_h, mask="auto")
            c.restoreState()
        except Exception:
            pass

    _line(c, x + 10 * mm, y_top - 28 * mm, x + w_card - 10 * mm, COLOR_BORDER)


# =========================
# Table (NO ellipsis for months)
# Each row is variable height depending on months lines count
# =========================
def _draw_table_paginated(c, x, y_top, w, y_bottom, rows, font_size=7.6):
    """
    Dessine une table sur la zone fournie, et retourne:
      (count_drawn, y_after)
    rows format: [Eleve, Type, tokens(list), Total]
    """
    headers = ["Élève", "Type", "Mois", "Total"]

    # column widths (single column full width)
    w_total = 24 * mm
    w_type = 20 * mm
    w_mois = 50 * mm
    w_eleve = max(55 * mm, w - (w_type + w_mois + w_total))
    col_ws = [w_eleve, w_type, w_mois, w_total]

    base_row_h = 5.8 * mm
    pad = 2 * mm

    # header
    curx = x
    c.setFont("Helvetica-Bold", 9)
    for i, head in enumerate(headers):
        c.setFillColor(colors.HexColor("#f8fafc"))
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.rect(curx, y_top - base_row_h, col_ws[i], base_row_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.drawString(curx + 2 * mm, y_top - base_row_h + 2.0 * mm, head)
        curx += col_ws[i]

    y = y_top - base_row_h
    drawn = 0

    # rows
    for r in rows:
        eleve_txt = str(r[0] or "")
        type_txt = str(r[1] or "")
        tokens = r[2] if isinstance(r[2], list) else []
        total_txt = str(r[3] or "")

        max_w_mois = col_ws[2] - 2 * pad

        # compute months lines WITHOUT cutting
        size_try = font_size
        month_lines = _split_tokens_to_lines(tokens, max_w_mois, "Helvetica", size_try, max_lines=4)

        # If too many lines needed, we paginate instead of cutting
        # We don't try to squeeze infinitely -> correctness > compact
        needed_lines = len(month_lines)
        row_h = base_row_h + max(0, (needed_lines - 1)) * (3.2 * mm)

        if y - row_h < y_bottom:
            break  # stop -> next page chunk

        y -= row_h
        curx = x

        # cell: eleve
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.rect(curx, y, col_ws[0], row_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica", font_size)
        # eleve can be ellipsized (not critical compared to months)
        c.drawString(curx + pad, y + row_h - 4.3 * mm, _ellipsize(eleve_txt, col_ws[0] - 2 * pad, "Helvetica", font_size))
        curx += col_ws[0]

        # cell: type
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.rect(curx, y, col_ws[1], row_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica", font_size)
        c.drawString(curx + pad, y + row_h - 4.3 * mm, type_txt)
        curx += col_ws[1]

        # cell: months (NO ellipsis)
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.rect(curx, y, col_ws[2], row_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica", size_try)
        top_text_y = y + row_h - 4.3 * mm
        if not month_lines:
            month_lines = ["—"]
        for i_line, line in enumerate(month_lines):
            c.drawString(curx + pad, top_text_y - (i_line * 3.2 * mm), line)
        curx += col_ws[2]

        # cell: total
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.rect(curx, y, col_ws[3], row_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica", font_size)
        c.drawRightString(curx + col_ws[3] - pad, y + row_h - 4.3 * mm, total_txt)

        drawn += 1

    return drawn, y


def _chunk_rows_for_halfpage(rows, max_rows_guess=9999):
    """
    We'll paginate by trying to draw in a virtual way.
    Here we just return the list (actual split happens in draw loop).
    """
    return rows


# =========================
# Draw HALF receipt (BATCH) with pagination chunks
# =========================
def _draw_half_receipt_batch(c, y_top, transactions, batch_token: str, rows_chunk, portal_rows):
    w, h = A4
    card_h = 134 * mm
    margin_x = 12 * mm
    card_w = w - 2 * margin_x

    COLOR_PRIMARY = "#4f46e5"
    COLOR_BORDER = "#e2e8f0"

    _card(c, margin_x, y_top, card_w, card_h)

    tx0 = transactions[0]

    # ✅ vraie date transaction (plus ancienne)
    dts = []
    for t in transactions:
        dt = getattr(t, "created_at", None) or getattr(t, "date_transaction", None)
        if dt:
            dts.append(dt)
    created = min(dts) if dts else datetime.now()
    date_txt = created.strftime("%Y-%m-%d %H:%M")

    code = _recu_value(tx0, batch_token=batch_token, txs=transactions)

    total_global = sum((_D(getattr(tx, "montant_total", None)) for tx in transactions), Decimal("0.00"))
    modes = {_mode_value(tx) for tx in transactions}
    mode_global = next(iter(modes)) if len(modes) == 1 else "Multiple"

    _draw_common_header(
        c,
        margin_x,
        y_top,
        card_w,
        card_h,
        title="REÇU PAIEMENT",
        code=code,
        badge="PAIEMENT",
    )

    left_x = margin_x + 12 * mm

    _section(c, left_x, y_top - 35.0 * mm, "PAIEMENT", accent=COLOR_PRIMARY)
    _kv(c, left_x, y_top - 41.0 * mm, "Date", date_txt, max_w=55 * mm)
    _kv(c, left_x + 52 * mm, y_top - 41.0 * mm, "Mode", str(mode_global), max_w=55 * mm)
    ref0 = _paiement_ref_value(tx0)
    _kv(c, left_x + 52 * mm, y_top - 49.0 * mm, "Réf", ref0, max_w=55 * mm)

    _kv(c, left_x + 104 * mm, y_top - 41.0 * mm, "Total", _money(total_global), highlight=True, max_w=50 * mm)

    _section(c, left_x, y_top - 53.0 * mm, "DÉTAILS", accent=COLOR_PRIMARY)

    zone_x = left_x
    zone_w = card_w - 24 * mm
    table_top = y_top - 56.5 * mm

    # portail box
    MAX_PORTAL = min(5, len(portal_rows))
    portal_title_h = 4.4 * mm
    portal_row_h = 3.4 * mm
    portal_pad_bot = 2.2 * mm
    portal_h = portal_title_h + (MAX_PORTAL * portal_row_h) + portal_pad_bot

    footer_y = (y_top - card_h) + 6.0 * mm
    y_bottom = footer_y + 5.2 * mm + portal_h + 1.4 * mm

    # draw table chunk
    drawn, _ = _draw_table_paginated(
        c,
        zone_x,
        table_top,
        zone_w,
        y_bottom,
        rows_chunk,
        font_size=7.6,
    )

    # portail
    box_x = zone_x
    box_w = zone_w
    box_y_top = y_bottom

    c.setFillColor(colors.HexColor("#f8fafc"))
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.roundRect(box_x, box_y_top - portal_h, box_w, portal_h, 6 * mm, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(box_x + 6 * mm, box_y_top - 3.7 * mm, "ACCÈS PORTAIL")

    # mini-table portal
    x_table = box_x + 6 * mm
    y_table_top = box_y_top - portal_title_h
    w_login = 44 * mm
    w_pwd = (box_w - 12 * mm) - w_login

    # draw portal rows (no ellipsis needed here)
    y = y_table_top
    for login, pwd in portal_rows[:MAX_PORTAL]:
        y -= portal_row_h
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.rect(x_table, y, w_login, portal_row_h, fill=1, stroke=1)
        c.rect(x_table + w_login, y, w_pwd, portal_row_h, fill=1, stroke=1)

        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica", 7.6)
        c.drawString(x_table + 2 * mm, y + 1.6 * mm, str(login or "—"))

        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Courier", 7.6)
        c.drawString(x_table + w_login + 2 * mm, y + 1.6 * mm, str(pwd or "—"))

    # footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(left_x, footer_y, "Signature / Cachet : _________________________________")
    c.drawRightString(margin_x + card_w - 12 * mm, footer_y, "Groupe Scolaire AZ")
    c.setFillColor(colors.black)

    return drawn


# =========================
# PUBLIC API: BATCH PDF
# Multi-pages allowed, ALWAYS 2 copies per page, NEVER ellipsis for months
# =========================
def build_transaction_batch_pdf_bytes(transactions, batch_token: str) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    if not transactions:
        c.showPage()
        c.save()
        out = buffer.getvalue()
        buffer.close()
        return out

    # Build full rows + portal rows
    all_rows, portal_rows = _build_rows_and_portal_from_transactions(transactions)

    # Pagination: we draw chunks, each chunk makes 1 PAGE (with 2 copies)
    idx = 0
    n = len(all_rows)

    while idx < n:
        # Try draw a chunk on top half (dry-run style by drawing and counting)
        top_y = h - 10 * mm

        # We attempt with a large slice and rely on _draw_table_paginated to stop when full.
        remaining = all_rows[idx:]
        drawn_top = _draw_half_receipt_batch(c, top_y, transactions, batch_token, remaining, portal_rows)

        # separator line
        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.setDash(3, 3)
        c.line(12 * mm, h / 2, w - 12 * mm, h / 2)
        c.setDash()
        c.setStrokeColor(colors.black)

        # Bottom copy: MUST be identical chunk
        bottom_y = (h / 2) - 5 * mm
        _draw_half_receipt_batch(c, bottom_y, transactions, batch_token, remaining[:drawn_top], portal_rows)

        idx += drawn_top
        c.showPage()

    c.save()
    out = buffer.getvalue()
    buffer.close()
    return out


# =========================
# SINGLE PDF: (2 copies per page, multi-pages if needed)
# For single, usually 1 page, but we respect "no cut, no ..."
# =========================
def build_transaction_pdf_bytes(tx) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # Convert single tx into a "transactions list" for reuse
    transactions = [tx]
    batch_token = ""  # not used

    # Build rows
    insc = tx.inscription
    qs = getattr(tx, "lignes", None)
    lignes = list(qs.all()) if hasattr(qs, "all") else (list(qs) if qs else [])
    all_rows = _rows_for_inscription(insc, lignes)

    portal_rows = [list(_login_pwd_from_inscription(insc))]

    idx = 0
    n = len(all_rows)

    while idx < n:
        top_y = h - 10 * mm
        remaining = all_rows[idx:]

        drawn_top = _draw_half_receipt_batch(c, top_y, transactions, batch_token, remaining, portal_rows)

        c.setStrokeColor(colors.HexColor("#cbd5e1"))
        c.setDash(3, 3)
        c.line(12 * mm, h / 2, w - 12 * mm, h / 2)
        c.setDash()
        c.setStrokeColor(colors.black)

        bottom_y = (h / 2) - 5 * mm
        _draw_half_receipt_batch(c, bottom_y, transactions, batch_token, remaining[:drawn_top], portal_rows)

        idx += drawn_top
        c.showPage()

    c.save()
    out = buffer.getvalue()
    buffer.close()
    return out
