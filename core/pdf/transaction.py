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


def _months_compact(months):
    months = [m for m in months if m and m != "—"]
    if not months:
        return ""
    s = ", ".join(months)
    if len(s) <= 60:
        return s
    return f"{months[0]} → {months[-1]} ({len(months)} mois)"


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
# Wrap 2 lignes (table)
# =========================
def _wrap_text_2lines(text, max_w, font="Helvetica", size=9):
    s = str(text or "").strip()
    if not s:
        return ("", "")
    if stringWidth(s, font, size) <= max_w:
        return (s, "")

    words = s.split()
    line1 = ""
    i = 0
    while i < len(words):
        cand = (line1 + " " + words[i]).strip()
        if stringWidth(cand, font, size) <= max_w:
            line1 = cand
            i += 1
        else:
            break

    rest = " ".join(words[i:]).strip()
    if not rest:
        return (line1, "")

    if stringWidth(rest, font, size) <= max_w:
        line2 = rest
    else:
        line2 = _ellipsize(rest, max_w, font, size)

    if not line1:
        return (_ellipsize(s, max_w, font, size), "")

    return (line1, line2)


def _table_wrap2(c, x, y_top, col_ws, headers, rows, row_h, wrap_cols=None, mono_cols=None, font_size=9, font_size2=8.0):
    wrap_cols = set(wrap_cols or [])
    mono_cols = set(mono_cols or [])

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
    y = y_top - row_h
    for r in rows:
        y -= row_h
        curx = x
        for i, cell in enumerate(r):
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.HexColor("#e2e8f0"))
            c.rect(curx, y, col_ws[i], row_h, fill=1, stroke=1)

            pad = 2 * mm
            max_w = col_ws[i] - 0 * pad
            text = str(cell or "")

            if i in wrap_cols:
                font1 = "Courier" if i in mono_cols else "Helvetica"
                font2 = "Courier" if i in mono_cols else "Helvetica"

                c.setFillColor(colors.HexColor("#0f172a"))
                c.setFont(font1, font_size)
                l1, l2 = _wrap_text_2lines(text, max_w, font1, font_size)
                c.drawString(curx + pad, y + row_h - 4.3 * mm, l1)

                if l2:
                    c.setFont(font2, font_size2)
                    c.setFillColor(colors.HexColor("#334155"))
                    c.drawString(curx + pad, y + row_h - 8.2 * mm, l2)
            else:
                c.setFillColor(colors.HexColor("#0f172a"))
                c.setFont("Helvetica", font_size)
                c.drawString(curx + pad, y + 2.0 * mm, _ellipsize(text, max_w, "Helvetica", 9))

            curx += col_ws[i]

    c.setFillColor(colors.black)
    return y


def _table_simple(c, x, y_top, col_ws, headers, rows, row_h):
    c.setFont("Helvetica-Bold", 9)
    curx = x
    for i, head in enumerate(headers):
        c.setFillColor(colors.HexColor("#f8fafc"))
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.rect(curx, y_top - row_h, col_ws[i], row_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.drawString(curx + 2 * mm, y_top - row_h + 2.0 * mm, _ellipsize(head, col_ws[i] - 4 * mm, "Helvetica-Bold", 9))
        curx += col_ws[i]

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


def _mini_table_portail(c, x, y_top, w_login, w_pwd, rows, row_h):
    """
    Mini-table ultra compacte (sans header), 1 ligne par élève.
    rows = [[login, pwd], ...]
    """
    border = colors.HexColor("#e2e8f0")
    text1 = colors.HexColor("#0f172a")
    text2 = colors.HexColor("#334155")

    y = y_top
    for login, pwd in rows:
        y -= row_h

        c.setFillColor(colors.white)
        c.setStrokeColor(border)
        c.rect(x, y, w_login, row_h, fill=1, stroke=1)
        c.rect(x + w_login, y, w_pwd, row_h, fill=1, stroke=1)

        c.setFillColor(text1)
        c.setFont("Helvetica", 7.6)
        c.drawString(x + 2 * mm, y + 1.6 * mm, _ellipsize(login, w_login - 4 * mm, "Helvetica", 7.6))

        c.setFillColor(text2)
        c.setFont("Courier", 7.6)
        c.drawString(x + w_login + 2 * mm, y + 1.6 * mm, _ellipsize(pwd, w_pwd - 4 * mm, "Courier", 7.6))

    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)
    return y


# =========================
# Helpers (modes + login)
# =========================
def _mode_value(tx):
    mode_label = getattr(tx, "get_mode_display", None)
    if callable(mode_label):
        return str(mode_label() or "—")
    return str(getattr(tx, "mode", None) or "—")


def _paiement_ref_value(tx):
    """
    Référence de paiement (banque/espèce/chèque/etc).
    Exemple chez toi: 4321
    """
    return str(getattr(tx, "reference", "") or "—")


def _recu_seq_value(tx, txs=None):
    """
    ✅ Numéro de reçu INCRÉMENTAL PAR REÇU
    - On utilise receipt_seq (doit être stocké en DB)
    - Pour batch : toutes les tx du batch doivent avoir le même receipt_seq
    """
    # 1) champ direct sur tx
    seq = getattr(tx, "receipt_seq", None)
    if seq:
        try:
            return int(seq)
        except Exception:
            pass

    # 2) si batch : chercher sur la 1ère tx qui a receipt_seq
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
    """
    ✅ Référence REÇU (badge violet) : AZ-PAY-YYYY-0001
    Basée sur receipt_seq => 1 numéro pour tout le batch.
    """
    # priorité: champ reçu custom si tu en as un (optionnel)
    for attr in ("numero_recu", "recu_numero", "receipt_no", "receipt_number", "code_recu"):
        v = getattr(tx, attr, None)
        if v:
            return str(v)

    # année (on garde année civile du paiement)
    try:
        year = (getattr(tx, "date_transaction", None) or datetime.now()).year
    except Exception:
        year = datetime.now().year

    # ✅ receipt_seq (le vrai incrément “par reçu”)
    seq = _recu_seq_value(tx, txs=txs)
    if seq is not None:
        return f"AZ-PAY-{year}-{seq:04d}"  # 0001..9999 (change 04d si tu veux 06d)

    # fallback si receipt_seq pas encore défini (évite uuid)
    # => on met un code lisible temporaire
    bt = batch_token or str(getattr(tx, "batch_token", "") or "")
    if bt:
        return f"AZ-PAY-{year}-TEMP"
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
# ✅ BATCH RECEIPT PDF 

# =========================
def build_transaction_batch_pdf_bytes(transactions, batch_token: str) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # THEME
    COLOR_PRIMARY = "#4f46e5"
    COLOR_ACCENT  = "#a855f7"
    COLOR_BORDER  = "#e2e8f0"
    COLOR_SOFT    = "#f8fafc"

    # images
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

    now = datetime.now()
    date_txt = now.strftime("%Y-%m-%d %H:%M")

    # ✅ Reçu batch = basé sur batch_token (PAS la référence de paiement)
    code = _recu_value(transactions[0], batch_token=batch_token, txs=transactions) if transactions else "AZ-PAY-—"


    total_global = sum((_D(getattr(tx, "montant_total", None)) for tx in transactions), Decimal("0.00"))

    modes = {_mode_value(tx) for tx in transactions}
    mode_global = next(iter(modes)) if len(modes) == 1 else "Multiple"

    def _months_for_tx(tx):
        months = []
        has_inscription = False

        for ln in tx.lignes.all():
            e1 = getattr(ln, "echeance", None)
            e2 = getattr(ln, "echeance_transport", None)

            if e1 and getattr(e1, "mois_nom", None):
                months.append(e1.mois_nom)
                continue

            if e2 and getattr(e2, "mois_nom", None):
                months.append(e2.mois_nom)
                continue

            # ✅ ligne sans échéance => Inscription (ou pack autre)
            has_inscription = True

        # unique + stable
        out = []
        seen = set()
        for m in months:
            if m and m not in seen:
                seen.add(m)
                out.append(m)

        # ✅ si inscription incluse
        if has_inscription:
            out.insert(0, "Inscription")

        return _months_compact(out) or ("Inscription" if has_inscription else "—")



    def _student_label(tx):
        insc = tx.inscription
        eleve = insc.eleve
        grp = getattr(insc, "groupe", None)
        gname = getattr(grp, "nom", "—")
        matricule = getattr(eleve, "matricule", "—")
        nom = f"{getattr(eleve,'nom','—')} {getattr(eleve,'prenom','')}".strip()
        return f"{matricule} — {nom} • {gname}"

    rows = []
    portal_rows = []

    for tx in transactions:
        insc = tx.inscription
        login, pwd = _login_pwd_from_inscription(insc)
        rows.append([
            _student_label(tx),
            _months_for_tx(tx),
            _money(_D(getattr(tx, "montant_total", None))),
        ])
        portal_rows.append([login, pwd])

    # =========================
    # DRAW ONE (toujours compact demi-page)
    # =========================
    def draw_one(y_top, card_h):
        margin_x = 12 * mm
        card_w = w - 2 * margin_x

        _card(c, margin_x, y_top, card_w, card_h)

        # header band
        c.setFillColor(colors.HexColor(COLOR_SOFT))
        c.roundRect(margin_x, y_top - 18 * mm, card_w, 18 * mm, 6 * mm, fill=1, stroke=0)
        c.setFillColor(colors.black)

        if logo_img:
            c.drawImage(logo_img, margin_x + 9 * mm, y_top - 15.2 * mm, width=12 * mm, height=12 * mm, mask="auto")

        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor(COLOR_PRIMARY))
        c.drawString(margin_x + 24 * mm, y_top - 8.0 * mm, "REÇU PAIEMENT")

        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawString(margin_x + 24 * mm, y_top - 13.0 * mm, "Groupe Scolaire AZ • Finance")
        c.setFillColor(colors.black)

        _pill(c, margin_x + card_w - 92 * mm, y_top - 14.5 * mm, code, wmm=80, bg="#f5f3ff", fg=COLOR_ACCENT)
        _pill(c, margin_x + card_w - 92 * mm, y_top - 24.5 * mm, "PAIEMENT", wmm=80, bg="#eef2ff", fg=COLOR_PRIMARY)

        # watermark
        if blur_img or logo_img:
            try:
                c.saveState()
                c.setFillAlpha(0.07)
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

        # ====== compact spacing
        _section(c, left_x, y_top - 35.0 * mm, "PAIEMENT", accent=COLOR_PRIMARY)
        _kv(c, left_x,            y_top - 41.0 * mm, "Date", date_txt, max_w=55 * mm)
        _kv(c, left_x + 52 * mm,  y_top - 41.0 * mm, "Mode", str(mode_global), max_w=55 * mm)
        _kv(c, left_x + 104 * mm, y_top - 41.0 * mm, "Total", _money(total_global), highlight=True, max_w=50 * mm)

        _section(c, left_x, y_top - 53.0 * mm, "DÉTAILS", accent=COLOR_PRIMARY)

        details_w = card_w - 24 * mm
        w_total = 28 * mm
        w_mode  = 26 * mm
        w_mois  = 52 * mm
        w_eleve = max(58 * mm, details_w - (w_mois + w_mode + w_total))

        headers = ["Élève", "Mois", "Total"]


        w_recu  = 30 * mm
        w_total = 28 * mm
        w_mode  = 26 * mm
        w_mois  = 48 * mm
        w_eleve = max(50 * mm, details_w - (w_recu + w_mois + w_mode + w_total))

        col_ws = [w_eleve, w_mois, w_total]


        # ====== réglage compact pour afficher 5
        MAX_ELEVES_TABLE = 5
        table_row_h = 5.6 * mm
        table_font1 = 7.8
        table_font2 = 7.0

        portal_title_h = 4.6 * mm
        portal_row_h   = 3.6 * mm
        portal_pad_bot = 2.4 * mm

        footer_gap = 5.2 * mm

        table_top = y_top - 54.5 * mm
        footer_y  = (y_top - card_h) + 6.0 * mm

        MAX_PORTAL = min(5, len(portal_rows))
        portal_h = portal_title_h + (MAX_PORTAL * portal_row_h) + portal_pad_bot

        safe_bottom = footer_y + footer_gap + portal_h

        shown_rows = rows[:MAX_ELEVES_TABLE]
        hidden_count = max(0, len(rows) - len(shown_rows))

        _table_wrap2(
            c,
            left_x,
            table_top,
            col_ws,
            headers,
            shown_rows,
            row_h=table_row_h,
            wrap_cols={1},
            font_size=table_font1,
            font_size2=table_font2,
        )

        # ====== portail
        box_w = card_w - 24 * mm
        box_x = left_x
        box_y_top = safe_bottom

        if hidden_count > 0:
            c.setFont("Helvetica", 8.0)
            c.setFillColor(colors.HexColor("#64748b"))
            c.drawString(left_x, box_y_top + 1.4 * mm, f"+ {hidden_count} autre(s) élève(s) non affiché(s)")
            c.setFillColor(colors.black)

        c.setFillColor(colors.HexColor("#f8fafc"))
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.roundRect(box_x, box_y_top - portal_h, box_w, portal_h, 6 * mm, fill=1, stroke=1)

        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(box_x + 6 * mm, box_y_top - 3.9 * mm, "ACCÈS PORTAIL")

        x_table = box_x + 6 * mm
        y_table_top = box_y_top - portal_title_h

        w_login = 44 * mm
        w_pwd = (box_w - 12 * mm) - w_login

        _mini_table_portail(
            c,
            x_table,
            y_table_top,
            w_login,
            w_pwd,
            portal_rows[:MAX_PORTAL],
            row_h=portal_row_h,
        )

        # footer
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawString(left_x, footer_y, "Signature / Cachet : _________________________________")
        c.drawRightString(margin_x + card_w - 12 * mm, footer_y, "Groupe Scolaire AZ")
        c.setFillColor(colors.black)

    # =========================
    # ✅ TOUJOURS 2 COPIES SUR A4 (AUCUNE CONDITION)
    # =========================
    half_card_h = 134 * mm

    top_y = h - 10 * mm
    draw_one(top_y, half_card_h)

    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setDash(3, 3)
    c.line(12 * mm, h / 2, w - 12 * mm, h / 2)
    c.setDash()
    c.setStrokeColor(colors.black)

    bottom_y = (h / 2) - 5 * mm
    draw_one(bottom_y, half_card_h)

    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =========================
# Single transaction PDF
# (Mode + Login/Mdp déjà affichés, version stable)
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
    code = _recu_value(tx)


    type_label = getattr(tx, "get_type_transaction_display", None)
    type_value = type_label() if callable(type_label) else (getattr(tx, "type_transaction", None) or "—")

    mode_value = _mode_value(tx)
    reference = _paiement_ref_value(tx)
    total = _D(getattr(tx, "montant_total", None))

    portal_url = "https://groupescolaireaz.cloud/"
    login, pwd = _login_pwd_from_inscription(insc)

    rows = []
    lignes_qs = getattr(tx, "lignes", None)
    lignes = list(lignes_qs.all()) if hasattr(lignes_qs, "all") else (list(lignes_qs) if lignes_qs else [])
    for ln in lignes[:21]:
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



    def draw_one(y_top):
        margin_x = 12 * mm
        card_w = w - 2 * margin_x
        card_h = 134 * mm

        _card(c, margin_x, y_top, card_w, card_h)

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

        _section(c, right_x, y_top - 36 * mm, "PAIEMENT", accent=COLOR_PRIMARY)
        _kv(c, right_x, y_top - 42 * mm, "Date", date_txt, max_w=60 * mm)
        _kv(c, right_x + 48 * mm, y_top - 42 * mm, "Mode", mode_value, max_w=45 * mm)
        _kv(c, right_x, y_top - 58 * mm, "Référence", reference, max_w=60 * mm)
        _kv(c, right_x + 48 * mm, y_top - 58 * mm, "Total", _money(total), highlight=True, max_w=45 * mm)

        _line(c, margin_x + 10 * mm, y_top - 66 * mm, margin_x + card_w - 10 * mm, COLOR_BORDER)

        _section(c, left_x, y_top - 74 * mm, "DÉTAILS", accent=COLOR_PRIMARY)

        headers = ["Mois", "Libellé", "Montant payé"]
        col_ws = [28 * mm, 92 * mm, 32 * mm]
        table_top = y_top - 78 * mm
        row_h = 6.2 * mm

        footer_y = (y_top - card_h) + 8 * mm

        portal_h = 12.5 * mm
        safe_bottom = footer_y + 11 * mm + portal_h
        max_rows_fit = int(max(1, (table_top - safe_bottom) / row_h))
        shown = rows[:max_rows_fit] if len(rows) > max_rows_fit else rows

        _table_simple(c, left_x, table_top, col_ws, headers, shown, row_h=row_h)

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
        c.drawString(box_x + 6 * mm, box_y_top - 10.6 * mm, f"Site : {portal_url}   |   Login : {login}")
        c.drawRightString(box_x + box_w - 6 * mm, box_y_top - 10.6 * mm, f"Mot de passe : {pwd}")

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawString(left_x, footer_y, "Signature / Cachet : _________________________________")
        c.drawRightString(margin_x + card_w - 12 * mm, footer_y, "Groupe Scolaire AZ")
        c.setFillColor(colors.black)

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
