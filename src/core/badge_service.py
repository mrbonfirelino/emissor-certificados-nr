"""Cracha de Identificacao (ReportLab) — NRs capacitadas + ASO + assinatura.

Layout paisagem 12x7,8cm baseado no modelo XLSX do cliente (CRACHA ALTEC
DETALHADO): cabecalho com logo + titulo, NOME/FUNCAO, foto 3x4 (esquerda) com
bloco ASO abaixo, texto de autorizacao + tabela de NRs (ate 8) a direita,
emissao + espaco de assinatura do colaborador e rodape de proibicao (vermelho).

Layout retrato 7,8x12cm (CRACHA-VERTICAL): mesmo conteudo reorganizado em
coluna unica — foto maior a esquerda com bloco ASO/Emissao ao lado, tabela de
NRs em tela cheia e assinatura em tela cheia. A orientacao e definida pelas
dimensoes do template (card_width_mm/card_height_mm).
"""

import re
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

from src.utils.paths import get_crachas_dir, get_logo_path

# dimensões do crachá (mm)
W_MM, H_MM = 120.0, 78.0
MAX_NRS = 8

PRIMARY = HexColor("#1B3A5C")
TEXT = HexColor("#111111")
MUTED = HexColor("#777777")
RED = HexColor("#C00000")
ZEBRA = HexColor("#EAF0F6")
YELLOW = HexColor("#FFF59D")
GRID = HexColor("#BBBBBB")


def _iso_to_br(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    try:
        d = date.fromisoformat(str(iso)[:10])
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)


def _sanitize_filename(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"[\s]+", "_", s)[:50]


def build_badge_data(
    employees: list,
    options: dict,
    history_repo=None,
    aso_repo=None,
) -> List[dict]:
    """
    Monta os dados de cada cracha a partir das opcoes da revisao:
    options = {"data_emissao": "YYYY-MM-DD", "nrs": {employee_id: [nr_code, ...]}}

    NRs: ultima emissao de cada NR do funcionario (mesma regra dos Vencimentos);
    data de capacitacao = data do treinamento, validade = data + validade_meses.
    ASO: vigente (mais recente) — numero + vencimento.
    """
    if history_repo is None:
        from src.core.history_repo import HistoryRepository
        history_repo = HistoryRepository()
    if aso_repo is None:
        from src.core.aso_repo import AsoRepository
        aso_repo = AsoRepository()

    try:
        certs = history_repo.get_certificates_with_expiration(only_latest=True)
    except Exception:
        certs = []
    try:
        asos = {a["employee_id"]: a for a in aso_repo.get_asos_with_expiration(only_latest=True)}
    except Exception:
        asos = {}

    certs_by_emp = {}
    for c in certs:
        certs_by_emp.setdefault(c["employee_id"], {})[c["nr_code"]] = c

    nrs_opt = options.get("nrs") or {}
    data_emissao = options.get("data_emissao") or date.today().isoformat()

    dados = []
    for emp in employees:
        disp = certs_by_emp.get(emp.id, {})
        sel_codes = [nr for nr in nrs_opt.get(emp.id, nrs_opt.get(str(emp.id), [])) if nr in disp]
        # ordena por data do treinamento (mais recente primeiro), limita MAX_NRS
        sel_codes = sorted(sel_codes, key=lambda nr: disp[nr]["data_fim"], reverse=True)[:MAX_NRS]
        nrs = [
            {
                "nr_code": nr,
                "data_capacitacao": disp[nr]["data_fim"],
                "data_validade": disp[nr]["data_validade"],
            }
            for nr in sel_codes
        ]
        aso = asos.get(emp.id)
        dados.append({
            "employee": emp,
            "data_emissao": data_emissao,
            "nrs": nrs,
            "aso_number": (aso or {}).get("cert_number") or (aso or {}).get("aso_number"),
            "aso_validade": (aso or {}).get("data_validade"),
        })
    return dados


def _fit_image(img_reader, box_x, box_y, box_w, box_h, c: pdfcanvas.Canvas):
    iw, ih = img_reader.getSize()
    ratio = min(box_w / iw, box_h / ih)
    dw, dh = iw * ratio, ih * ratio
    dx = box_x + (box_w - dw) / 2
    dy = box_y + (box_h - dh) / 2
    c.drawImage(img_reader, dx, dy, dw, dh, mask="auto")


def _wrap_text(c, text, font, size, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        tent = (cur + " " + w).strip()
        if c.stringWidth(tent, font, size) <= max_w:
            cur = tent
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_badge(c: pdfcanvas.Canvas, emp, badge: dict, cracha_number: str,
               logo_path: Optional[Path]):
    """Desenha um cracha ocupando a pagina inteira (120x78mm)."""
    c.saveState()

    # fundo + borda
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.8)
    c.roundRect(0.4 * mm, 0.4 * mm, (W_MM - 0.8) * mm, (H_MM - 0.8) * mm, 1.5 * mm,
                stroke=1, fill=1)

    # ── Cabecalho (titulo + logo) ──
    if logo_path and Path(logo_path).exists():
        try:
            c.drawImage(ImageReader(str(logo_path)), 4 * mm, 68.5 * mm,
                        24 * mm, 8 * mm, mask="auto", preserveAspectRatio=True)
        except Exception:
            pass
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(PRIMARY)
    c.drawCentredString(66 * mm, 71 * mm, "Cartão de Identificação")
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.6)
    c.line(2 * mm, 67.5 * mm, (W_MM - 2) * mm, 67.5 * mm)

    # ── Nome / Funcao ──
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(4 * mm, 63.5 * mm, "NOME:")
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(15 * mm, 63.5 * mm, (emp.nome or "").upper()[:42])
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(4 * mm, 59.5 * mm, "FUNÇÃO:")
    c.setFont("Helvetica-Bold", 7)
    c.drawString(16.5 * mm, 59.5 * mm, (emp.funcao or "-").upper()[:38])
    c.setLineWidth(0.4)
    c.line(2 * mm, 57.5 * mm, (W_MM - 2) * mm, 57.5 * mm)

    # ── Coluna esquerda: foto 3x4 + bloco ASO ──
    fx, fy, fw, fh = 4 * mm, 29 * mm, 21 * mm, 27 * mm
    drawn = False
    if getattr(emp, "foto", None):
        try:
            import io
            img = ImageReader(io.BytesIO(emp.foto))
            c.setFillColor(HexColor("#FFFFFF"))
            c.rect(fx, fy, fw, fh, stroke=0, fill=1)
            _fit_image(img, fx, fy, fw, fh, c)
            drawn = True
        except Exception:
            drawn = False
    if not drawn:
        c.setFillColor(HexColor("#F0F0F0"))
        c.setStrokeColor(HexColor("#999999"))
        c.setLineWidth(0.5)
        c.rect(fx, fy, fw, fh, stroke=1, fill=1)
        c.setFillColor(HexColor("#999999"))
        c.setFont("Helvetica", 6)
        c.drawCentredString(fx + fw / 2, fy + fh / 2 - 2, "SEM FOTO")
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.5)
    c.rect(fx, fy, fw, fh, stroke=1, fill=0)

    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(fx, 23 * mm, "ASO Vence:")
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(RED if _aso_vencido(badge.get("aso_validade")) else TEXT)
    c.drawString(fx, 19 * mm, _iso_to_br(badge.get("aso_validade")))
    c.setFont("Helvetica", 5)
    c.setFillColor(MUTED)
    c.drawString(fx, 15.5 * mm, f"Nº {badge.get('aso_number') or '—'}")

    # ── Coluna direita: autorizacao + tabela de NRs ──
    tx0, tx1 = 28 * mm, 116 * mm
    auth = ("O portador desta identificação está autorizado a operar os "
            "equipamentos e/ou áreas abaixo relacionadas, conforme capacitações:")
    c.setFont("Helvetica", 5.2)
    c.setFillColor(TEXT)
    y = 55.5 * mm
    for ln in _wrap_text(c, auth, "Helvetica", 5.2, tx1 - tx0)[:2]:
        c.drawString(tx0, y, ln)
        y -= 3 * mm

    # cabecalho da tabela
    ty = 47.5 * mm
    c.setFillColor(PRIMARY)
    c.rect(tx0, ty, tx1 - tx0, 4.2 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 6)
    c.drawString(tx0 + 1.5 * mm, ty + 1.3 * mm, "Capacitação")
    c.drawCentredString(78 * mm, ty + 1.3 * mm, "Data")
    c.drawCentredString(102 * mm, ty + 1.3 * mm, "Validade")

    # linhas de NR (ate MAX_NRS, preenchidas com grade mesmo quando vazias)
    row_h = 3.9 * mm
    for i in range(MAX_NRS):
        ry = ty - row_h * (i + 1)
        if i % 2 == 1:
            c.setFillColor(ZEBRA)
            c.rect(tx0, ry, tx1 - tx0, row_h, stroke=0, fill=1)
        c.setStrokeColor(GRID)
        c.setLineWidth(0.25)
        c.line(tx0, ry, tx1, ry)
        if i < len(badge["nrs"]):
            nr = badge["nrs"][i]
            vencido = _vencido(nr["data_validade"])
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 6.2)
            c.drawString(tx0 + 1.5 * mm, ry + 1.2 * mm, nr["nr_code"])
            c.setFont("Helvetica", 6.2)
            c.setFillColor(RED if vencido else TEXT)
            c.drawCentredString(78 * mm, ry + 1.2 * mm, _iso_to_br(nr["data_capacitacao"]))
            c.drawCentredString(102 * mm, ry + 1.2 * mm, _iso_to_br(nr["data_validade"]))
    # moldura da tabela
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.5)
    c.rect(tx0, ty - row_h * MAX_NRS, tx1 - tx0, 4.2 * mm + row_h * MAX_NRS, stroke=1, fill=0)

    # ── Emissao + assinatura ──
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(4 * mm, 11.5 * mm, f"Emissão: {_iso_to_br(badge['data_emissao'])}")

    c.setFillColor(YELLOW)
    c.rect(62 * mm, 8 * mm, 52 * mm, 6 * mm, stroke=0, fill=1)
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.4)
    c.rect(62 * mm, 8 * mm, 52 * mm, 6 * mm, stroke=1, fill=0)
    c.setFillColor(TEXT)
    c.setFont("Helvetica", 6.5)
    c.drawString(39 * mm, 10 * mm, "Ass Colaborador:")

    # ── Rodape ──
    c.setFont("Helvetica-Bold", 5.2)
    c.setFillColor(RED)
    c.drawCentredString(W_MM / 2 * mm, 4.5 * mm,
                        "É expressamente proibido executar atividades com treinamento e ASO fora do prazo")
    c.setFont("Helvetica", 4.5)
    c.setFillColor(MUTED)
    c.drawRightString(117 * mm, 1.8 * mm, cracha_number)
    c.setFont("Helvetica", 4.5)
    c.drawString(3 * mm, 1.8 * mm, "ALTEC")

    c.restoreState()


def _vencido(data_validade_iso) -> bool:
    try:
        return date.fromisoformat(str(data_validade_iso)[:10]) < date.today()
    except Exception:
        return False


def _aso_vencido(data_validade_iso) -> bool:
    return _vencido(data_validade_iso)


# ── Layout RETRATO 7,8x12cm (CRACHA-VERTICAL) ────────────────────────────────

VW_MM, VH_MM = 78.0, 120.0


def draw_badge_vertical(c: pdfcanvas.Canvas, emp, badge: dict, cracha_number: str,
                        logo_path: Optional[Path]):
    """Desenha um cracha retrato ocupando a pagina inteira (78x120mm)."""
    c.saveState()

    # fundo + borda
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.8)
    c.roundRect(0.4 * mm, 0.4 * mm, (VW_MM - 0.8) * mm, (VH_MM - 0.8) * mm, 1.5 * mm,
                stroke=1, fill=1)

    # ── Cabecalho (titulo + logo) ──
    if logo_path and Path(logo_path).exists():
        try:
            c.drawImage(ImageReader(str(logo_path)), 4 * mm, 112.5 * mm,
                        20 * mm, 7 * mm, mask="auto", preserveAspectRatio=True)
        except Exception:
            pass
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(PRIMARY)
    c.drawCentredString(40 * mm, 115 * mm, "Cartão de Identificação")
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.6)
    c.line(2 * mm, 111.5 * mm, (VW_MM - 2) * mm, 111.5 * mm)

    # ── Nome / Funcao ──
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(4 * mm, 107.5 * mm, "NOME:")
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(15 * mm, 107.5 * mm, (emp.nome or "").upper()[:36])
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(4 * mm, 103.5 * mm, "FUNÇÃO:")
    c.setFont("Helvetica-Bold", 7)
    c.drawString(16.5 * mm, 103.5 * mm, (emp.funcao or "-").upper()[:32])
    c.setLineWidth(0.4)
    c.line(2 * mm, 101.5 * mm, (VW_MM - 2) * mm, 101.5 * mm)

    # ── Foto 3x4 (esquerda) + bloco ASO/Emissao (direita) ──
    fx, fy, fw, fh = 4 * mm, 67 * mm, 24 * mm, 32 * mm
    drawn = False
    if getattr(emp, "foto", None):
        try:
            import io
            img = ImageReader(io.BytesIO(emp.foto))
            c.setFillColor(HexColor("#FFFFFF"))
            c.rect(fx, fy, fw, fh, stroke=0, fill=1)
            _fit_image(img, fx, fy, fw, fh, c)
            drawn = True
        except Exception:
            drawn = False
    if not drawn:
        c.setFillColor(HexColor("#F0F0F0"))
        c.setStrokeColor(HexColor("#999999"))
        c.setLineWidth(0.5)
        c.rect(fx, fy, fw, fh, stroke=1, fill=1)
        c.setFillColor(HexColor("#999999"))
        c.setFont("Helvetica", 6)
        c.drawCentredString(fx + fw / 2, fy + fh / 2 - 2, "SEM FOTO")
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.5)
    c.rect(fx, fy, fw, fh, stroke=1, fill=0)

    bx = 30 * mm
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(bx, 95 * mm, "ASO Vence:")
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(RED if _aso_vencido(badge.get("aso_validade")) else TEXT)
    c.drawString(bx, 91.5 * mm, _iso_to_br(badge.get("aso_validade")))
    c.setFont("Helvetica", 5)
    c.setFillColor(MUTED)
    c.drawString(bx, 88 * mm, f"Nº {badge.get('aso_number') or '—'}")
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(bx, 84 * mm, f"Emissão: {_iso_to_br(badge['data_emissao'])}")

    # ── Autorizacao (tela cheia) ──
    tx0, tx1 = 4 * mm, 74 * mm
    auth = ("O portador desta identificação está autorizado a operar os "
            "equipamentos e/ou áreas abaixo relacionadas, conforme capacitações:")
    c.setFont("Helvetica", 5.2)
    c.setFillColor(TEXT)
    y = 63.5 * mm
    for ln in _wrap_text(c, auth, "Helvetica", 5.2, tx1 - tx0)[:3]:
        c.drawString(tx0, y, ln)
        y -= 3 * mm

    # ── Tabela de NRs (tela cheia, 8 linhas) ──
    ty = 54 * mm
    row_h = 4.2 * mm
    c.setFillColor(PRIMARY)
    c.rect(tx0, ty, tx1 - tx0, 4.2 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 6)
    c.drawString(tx0 + 1.5 * mm, ty + 1.3 * mm, "Capacitação")
    c.drawCentredString(49 * mm, ty + 1.3 * mm, "Data")
    c.drawCentredString(68 * mm, ty + 1.3 * mm, "Validade")

    for i in range(MAX_NRS):
        ry = ty - row_h * (i + 1)
        if i % 2 == 1:
            c.setFillColor(ZEBRA)
            c.rect(tx0, ry, tx1 - tx0, row_h, stroke=0, fill=1)
        c.setStrokeColor(GRID)
        c.setLineWidth(0.25)
        c.line(tx0, ry, tx1, ry)
        if i < len(badge["nrs"]):
            nr = badge["nrs"][i]
            vencido = _vencido(nr["data_validade"])
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 6.2)
            c.drawString(tx0 + 1.5 * mm, ry + 1.4 * mm, nr["nr_code"])
            c.setFont("Helvetica", 6.2)
            c.setFillColor(RED if vencido else TEXT)
            c.drawCentredString(49 * mm, ry + 1.4 * mm, _iso_to_br(nr["data_capacitacao"]))
            c.drawCentredString(68 * mm, ry + 1.4 * mm, _iso_to_br(nr["data_validade"]))
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.5)
    c.rect(tx0, ty - row_h * MAX_NRS, tx1 - tx0, 4.2 * mm + row_h * MAX_NRS, stroke=1, fill=0)

    # ── Assinatura (tela cheia) ──
    c.setFillColor(TEXT)
    c.setFont("Helvetica", 6.5)
    c.drawString(4 * mm, 16.5 * mm, "Ass Colaborador:")
    c.setFillColor(YELLOW)
    c.rect(4 * mm, 8 * mm, 70 * mm, 6.5 * mm, stroke=0, fill=1)
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.4)
    c.rect(4 * mm, 8 * mm, 70 * mm, 6.5 * mm, stroke=1, fill=0)

    # ── Rodape ──
    proib = "É expressamente proibido executar atividades com treinamento e ASO fora do prazo"
    size = 5.0
    while size > 3.5 and c.stringWidth(proib, "Helvetica-Bold", size) > 72 * mm:
        size -= 0.2
    c.setFont("Helvetica-Bold", size)
    c.setFillColor(RED)
    c.drawCentredString(VW_MM / 2 * mm, 4.5 * mm, proib)
    c.setFont("Helvetica", 4.5)
    c.setFillColor(MUTED)
    c.drawRightString(75 * mm, 1.8 * mm, cracha_number)
    c.drawString(3 * mm, 1.8 * mm, "ALTEC")

    c.restoreState()


def generate_badges(
    employees: list,
    template: dict,
    single_pdf: bool = True,
    options: Optional[dict] = None,
    output_dir: Optional[Path] = None,
    history_repo=None,
    aso_repo=None,
    cracha_repo=None,
) -> Tuple[List[Path], List[str]]:
    """
    Gera crachas (1 por pagina; orientacao e tamanho vem do template:
    card_width_mm x card_height_mm — paisagem 12x7,8 ou retrato 7,8x12).

    - single_pdf=True: um PDF multipagina (lote) em data/crachas/LOTES
    - single_pdf=False: um PDF por funcionario em data/crachas/{Func}/
    - output_dir definido (preview): NAO consome numeracao nem grava no banco
    - gravacao no banco (tabela crachas) apenas na geracao definitiva

    Retorna (caminhos_gerados, faltantes_msg).
    """
    options = options or {}
    record = output_dir is None
    if cracha_repo is None:
        from src.core.cracha_repo import CrachaRepository
        cracha_repo = CrachaRepository()

    dados = build_badge_data(employees, options, history_repo, aso_repo)
    if not dados:
        return [], []

    w_mm = float(template.get("card_width_mm", W_MM))
    h_mm = float(template.get("card_height_mm", H_MM))
    page_size = (w_mm * mm, h_mm * mm)
    draw_fn = draw_badge_vertical if h_mm > w_mm else draw_badge
    logo_path = get_logo_path()
    if not Path(logo_path).exists():
        logo_path = None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    card_code = template.get("card_code", "CRACHA")

    def _numero(recordar: bool) -> str:
        if recordar:
            return cracha_repo.next_cracha_number()
        return cracha_repo.peek_cracha_number()

    generated: List[Path] = []

    if single_pdf:
        lote_dir = (output_dir or (get_crachas_dir() / "LOTES"))
        lote_dir.mkdir(parents=True, exist_ok=True)
        out = lote_dir / f"CRACHAS_{card_code}_{timestamp}.pdf"
        c = pdfcanvas.Canvas(str(out), pagesize=page_size)
        numeros = []
        for badge in dados:
            num = _numero(record)
            numeros.append((badge, num))
            draw_fn(c, badge["employee"], badge, num, logo_path)
            c.showPage()
        c.save()
        generated.append(out)
        if record:
            for badge, num in numeros:
                cracha_repo.save(num, badge["employee"].id, badge["employee"].nome,
                                 badge["data_emissao"], [r["nr_code"] for r in badge["nrs"]],
                                 badge["aso_number"], badge["aso_validade"], str(out))
    else:
        from src.utils.folder_utils import employee_folder_name
        try:
            from src.core.employee_repo import EmployeeRepository
            todos = EmployeeRepository().get_all(limit=1000000)
        except Exception:
            todos = list(employees)
        for badge in dados:
            emp = badge["employee"]
            pasta = employee_folder_name(emp, todos)
            emp_dir = output_dir or (get_crachas_dir() / pasta)
            emp_dir.mkdir(parents=True, exist_ok=True)
            num = _numero(record)
            out = emp_dir / f"CRACHA_{_sanitize_filename(emp.nome)}_{num}.pdf"
            c = pdfcanvas.Canvas(str(out), pagesize=page_size)
            draw_fn(c, emp, badge, num, logo_path)
            c.showPage()
            c.save()
            generated.append(out)
            if record:
                cracha_repo.save(num, emp.id, emp.nome, badge["data_emissao"],
                                 [r["nr_code"] for r in badge["nrs"]], badge["aso_number"],
                                 badge["aso_validade"], str(out))

    _disparar_sync(generated, dados, single_pdf)

    return generated, []


def _disparar_sync(generated: List[Path], dados, single_pdf: bool):
    """Espelha crachas na rede (best-effort, thread a parte)."""
    try:
        from src.core import network_sync
        if not generated:
            return
        if single_pdf:
            network_sync.run_async(network_sync.sync_cracha_lote, generated[0])
        else:
            for out, badge in zip(generated, dados):
                network_sync.run_async(network_sync.sync_cracha, out, badge["employee"])
    except Exception:
        pass
