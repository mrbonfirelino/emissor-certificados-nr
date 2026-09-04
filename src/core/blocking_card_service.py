import io
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

from src.utils.paths import get_templates_dir, get_logo_path, get_cartoes_dir
from src.utils.validators import formatar_telefone


def _hex(color_str: str):
    try:
        return HexColor(color_str)
    except Exception:
        return HexColor("#333333")


def load_card_templates() -> Dict[str, dict]:
    """Carrega templates de cartao: JSON (templates/cards/*.card.json) + PPTX (templates/cards/pptx/*.card.json)."""
    cards_dir = get_templates_dir() / "cards"
    templates = {}
    if cards_dir.exists():
        for f in sorted(cards_dir.glob("*.card.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if "card_code" in data:
                    templates[data["card_code"]] = data
            except Exception:
                continue
    try:
        from src.core.pptx_card_service import load_pptx_card_templates
        templates.update(load_pptx_card_templates())
    except Exception:
        pass
    return templates


def load_card_template(card_code: str) -> Optional[dict]:
    return load_card_templates().get(card_code)


def compute_grid(template: dict) -> Tuple[int, int]:
    """
    Calcula automaticamente colunas x linhas de cartoes por folha A4
    com base no tamanho do cartao do template.
    """
    cw = float(template.get("card_width_mm", 85.6))
    ch = float(template.get("card_height_mm", 54))
    gap = float(template.get("gap_mm", 5))
    margins = template.get("page_margins_mm", {"top": 10, "bottom": 10, "left": 10, "right": 10})

    avail_w = 210.0 - float(margins.get("left", 10)) - float(margins.get("right", 10))
    avail_h = 297.0 - float(margins.get("top", 10)) - float(margins.get("bottom", 10))

    cell_w = cw + gap
    cell_h = ch + gap
    cols = max(1, int((avail_w + gap) // cell_w))
    rows = max(1, int((avail_h + gap) // cell_h))
    return cols, rows


def validate_employees_for_cards(employees: list, template: Optional[dict] = None) -> Tuple[list, List[str]]:
    """
    Separa funcionarios validos dos invalidos conforme o template:
    - PPTX: exige apenas os campos que o template usa (foto/telefone)
    - Cracha: nenhum campo obrigatorio (foto opcional, vira placeholder)
    - JSON (default): exige telefone E foto
    Retorna (validos, mensagens_faltantes).
    """
    if template and template.get("template_type") == "pptx":
        from src.core.pptx_card_service import validate_employees_for_pptx
        return validate_employees_for_pptx(employees, template)
    if template and template.get("template_type") == "cracha":
        return list(employees), []
    valid, missing = [], []
    for emp in employees:
        faltas = []
        if not getattr(emp, "telefone", None):
            faltas.append("telefone")
        if not getattr(emp, "foto", None):
            faltas.append("foto 3x4")
        if faltas:
            missing.append(f"{emp.nome}: sem {' e '.join(faltas)}")
        else:
            valid.append(emp)
    return valid, missing


def _sanitize_filename(name: str) -> str:
    s = re.sub(r'[^\w\s-]', '', name).strip()
    return re.sub(r'[\s]+', '_', s)[:50]


def _fit_image(img_reader, box_x, box_y, box_w, box_h, c: pdfcanvas.Canvas):
    """Desenha imagem completa dentro do box sem distorcer, centralizada."""
    iw, ih = img_reader.getSize()
    ratio = min(box_w / iw, box_h / ih)
    dw, dh = iw * ratio, ih * ratio
    dx = box_x + (box_w - dw) / 2
    dy = box_y + (box_h - dh) / 2
    c.drawImage(img_reader, dx, dy, dw, dh, mask='auto')


def _draw_card(c: pdfcanvas.Canvas, x: float, y: float, template: dict, emp, logo_path: Optional[Path]):
    """
    Desenha um cartao na posicao (x, y) = canto inferior esquerdo (pontos).
    Layout por secoes empilhadas de cima para baixo, com divisórias.
    """
    cw = float(template.get("card_width_mm", 90)) * mm
    ch = float(template.get("card_height_mm", 120)) * mm
    border = template.get("border", {})
    bw = float(border.get("width", 2.0))
    bcolor = _hex(border.get("color", "#111111"))
    radius = float(border.get("corner_radius_mm", 1.5)) * mm
    div_w = float(template.get("divider_width", 1.2))

    c.saveState()
    # fundo branco + borda externa
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(bcolor)
    c.setLineWidth(bw)
    c.roundRect(x, y, cw, ch, radius, stroke=1, fill=1)

    # area util interna (desconta borda)
    inner_x = x + bw / 2
    inner_top = y + ch - bw / 2
    inner_w = cw - bw

    sections = template.get("sections", [])
    cursor_top = inner_top  # y do topo da secao atual (pontos)

    for sec in sections:
        sec_type = sec.get("type", "")
        sec_h = float(sec.get("height_mm", 0)) * mm
        sec_y = cursor_top - sec_h  # y da base da secao

        if sec_type == "header":
            cfg = template.get("header", {})
            # furo (visual) — circulo verde com cruz
            hole = cfg.get("hole", {})
            if hole.get("enabled", True):
                hx = x + float(hole.get("x_mm", 7)) * mm
                hy = sec_y + sec_h / 2  # centro vertical da secao
                d = float(hole.get("diameter_mm", 9)) * mm
                ring = _hex(hole.get("ring_color", "#1E7A1E"))
                rw = float(hole.get("ring_width", 2.6))
                c.setStrokeColor(ring)
                c.setLineWidth(rw)
                c.circle(hx, hy, d / 2, stroke=1, fill=0)
                # cruz interna
                crw = float(hole.get("cross_width", 2.4))
                arm = d * float(hole.get("cross_arm_ratio", 0.40))
                c.setLineWidth(crw)
                c.line(hx - arm, hy, hx + arm, hy)
                c.line(hx, hy - arm, hx, hy + arm)

            # logo ALTEC (obrigatorio) — posicionada dentro do header
            logo_cfg = cfg.get("logo", {})
            if logo_path and Path(logo_path).exists():
                lw = float(logo_cfg.get("width_mm", 26)) * mm
                lh = float(logo_cfg.get("height_mm", 11)) * mm
                lx = x + float(logo_cfg.get("x_mm", 58)) * mm
                lyc = sec_y + float(logo_cfg.get("y_center_mm", sec_h / 2 / mm)) * mm
                c.drawImage(ImageReader(str(logo_path)), lx, lyc - lh / 2, lw, lh,
                            mask='auto', preserveAspectRatio=True)

        elif sec_type == "danger_band":
            cfg = template.get("danger_band", {})
            text = cfg.get("text", "PERIGO")
            font = cfg.get("font", "Helvetica-Bold")
            fs = float(cfg.get("font_size", 20))
            bwm = float(cfg.get("border_width_mm", 1.2)) * mm
            pad = float(cfg.get("padding_mm", 10)) * mm
            rect_h = min(float(cfg.get("rect_height_mm", 11)) * mm, sec_h)
            radius = float(cfg.get("corner_radius_mm", 2)) * mm

            # largura da faixa = texto + padding dos dois lados (clamp na largura util)
            text_w = c.stringWidth(text, font, fs)
            red_w = min(text_w + 2 * pad, inner_w - 4 * mm)
            red_x = x + (cw - red_w) / 2
            red_y = sec_y + (sec_h - rect_h) / 2

            # moldura preta (contraste) + faixa vermelha, cantos arredondados
            c.setFillColor(_hex(cfg.get("border_color", "#111111")))
            c.roundRect(red_x, red_y, red_w, rect_h, radius, stroke=0, fill=1)
            c.setFillColor(_hex(cfg.get("color", "#D40000")))
            c.roundRect(red_x + bwm, red_y + bwm, red_w - 2 * bwm, rect_h - 2 * bwm,
                        max(radius - bwm, 0.5 * mm), stroke=0, fill=1)
            c.setFont(font, fs)
            c.setFillColor(_hex(cfg.get("text_color", "#FFFFFF")))
            c.drawCentredString(x + cw / 2, sec_y + sec_h / 2 - fs * 0.36, text)

        elif sec_type == "photo":
            cfg = template.get("photo", {})
            fw = float(cfg.get("width_mm", 30)) * mm
            fh = min(float(cfg.get("height_mm", 34)) * mm, sec_h)
            fx = x + (cw - fw) / 2
            fy = sec_y + (sec_h - fh) / 2
            drawn = False
            if getattr(emp, "foto", None):
                try:
                    img = ImageReader(io.BytesIO(emp.foto))
                    c.setFillColor(HexColor("#FFFFFF"))
                    c.rect(fx, fy, fw, fh, stroke=0, fill=1)
                    _fit_image(img, fx, fy, fw, fh, c)
                    drawn = True
                except Exception:
                    drawn = False
            if not drawn:
                c.setFillColor(_hex("#F0F0F0"))
                c.setStrokeColor(_hex("#999999"))
                c.setLineWidth(0.5)
                c.rect(fx, fy, fw, fh, stroke=1, fill=1)
                c.setFillColor(_hex("#999999"))
                c.setFont("Helvetica", 6)
                c.drawCentredString(fx + fw / 2, fy + fh / 2 - 2, cfg.get("placeholder_text", "SEM FOTO"))
            else:
                fbw = float(cfg.get("border_width", 0.8))
                if fbw > 0:
                    c.setStrokeColor(_hex(cfg.get("border_color", "#111111")))
                    c.setLineWidth(fbw)
                    c.rect(fx, fy, fw, fh, stroke=1, fill=0)

        elif sec_type == "message":
            cfg = template.get("message", {})
            l1 = cfg.get("line1", {})
            l2 = cfg.get("line2", {})
            if l1.get("text"):
                fs1 = float(l1.get("size", 8.5))
                c.setFont(l1.get("font", "Helvetica"), fs1)
                c.setFillColor(_hex(l1.get("color", "#111111")))
                c.drawCentredString(x + cw / 2, sec_y + sec_h * 0.62, l1.get("text"))
            if l2.get("text"):
                fs2 = float(l2.get("size", 13))
                c.setFont(l2.get("font", "Helvetica-Bold"), fs2)
                c.setFillColor(_hex(l2.get("color", "#111111")))
                c.drawCentredString(x + cw / 2, sec_y + sec_h * 0.25, l2.get("text"))

        elif sec_type == "employee":
            cfg = template.get("employee", {})
            nome_cfg = cfg.get("nome", {})
            funcao_cfg = cfg.get("funcao", {})
            nome = (emp.nome or "").upper()
            if int(nome_cfg.get("max_chars", 30) or 0):
                nome = nome[:int(nome_cfg["max_chars"])]
            funcao = (emp.funcao or "-").upper()
            if int(funcao_cfg.get("max_chars", 28) or 0):
                funcao = funcao[:int(funcao_cfg["max_chars"])]
            fs_n = float(nome_cfg.get("size", 9))
            fs_f = float(funcao_cfg.get("size", 8.5))
            c.setFont(nome_cfg.get("font", "Helvetica-Bold"), fs_n)
            c.setFillColor(_hex(nome_cfg.get("color", "#111111")))
            c.drawCentredString(x + cw / 2, sec_y + sec_h * 0.60, nome)
            c.setFont(funcao_cfg.get("font", "Helvetica"), fs_f)
            c.setFillColor(_hex(funcao_cfg.get("color", "#111111")))
            c.drawCentredString(x + cw / 2, sec_y + sec_h * 0.25, funcao)

        elif sec_type == "phone":
            cfg = template.get("phone", {})
            tel = formatar_telefone(emp.telefone) if getattr(emp, "telefone", None) else "-"
            if cfg.get("space_before_hyphen") and "-" in tel:
                tel = tel.replace("-", " - ")
            fs = float(cfg.get("size", 11))
            py = sec_y + sec_h * 0.40
            label = cfg.get("label", "Tel: ")
            c.setFont(cfg.get("font", "Helvetica-Bold"), fs)
            c.setFillColor(_hex(cfg.get("color", "#111111")))
            if cfg.get("centered", True):
                c.drawCentredString(x + cw / 2, py, label + tel)
            else:
                px = x + float(cfg.get("x_mm", 6)) * mm
                c.drawString(px, py, label + tel)

        # divisória horizontal entre seções (exceto após a última)
        if div_w > 0 and sec is not sections[-1]:
            c.setStrokeColor(bcolor)
            c.setLineWidth(div_w)
            c.line(inner_x, sec_y, x + cw - bw / 2, sec_y)

        cursor_top = sec_y

    c.restoreState()


def generate_cards(
    employees: list,
    template: dict,
    single_pdf: bool = True,
    output_dir: Optional[Path] = None,
    options: Optional[dict] = None,
    one_per_page: bool = False,
) -> Tuple[List[Path], List[str]]:
    """
    Gera cartoes de bloqueio em PDF.

    - Template JSON (ReportLab):
      - single_pdf=True: um PDF unico com N cartoes por folha (grid automatico)
      - single_pdf=False: um PDF por funcionario (1 cartao centralizado por folha)
    - Template PPTX (PowerPoint):
      - single_pdf=True: um PDF unico (folha do template, ou 1 cartao/pagina
        se one_per_page=True)
      - single_pdf=False: um PDF por funcionario (cartao recortado)

    options (PPTX): {"setor": str, "papeis": {employee_id: "LIDER"|"LIDERADO"}}

    Retorna (caminhos_gerados, faltantes_msg).
    """
    if template.get("template_type") == "pptx":
        from src.core.pptx_card_service import generate_pptx_cards
        return generate_pptx_cards(
            employees, template,
            options=options,
            single_pdf=single_pdf,
            one_per_page=one_per_page,
            output_dir=output_dir,
        )

    if template.get("template_type") == "cracha":
        from src.core.badge_service import generate_badges
        return generate_badges(
            employees, template,
            options=options or {},
            single_pdf=single_pdf,
            output_dir=output_dir,
        )

    valid, missing = validate_employees_for_cards(employees, template)
    if not valid:
        return [], missing

    card_code = template.get("card_code", "CARD")
    cliente_dir = output_dir or get_cartoes_dir()
    cliente_dir.mkdir(parents=True, exist_ok=True)

    logo_path = get_logo_path()
    if not Path(logo_path).exists():
        logo_path = None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated: List[Path] = []

    cw = float(template.get("card_width_mm", 85.6)) * mm
    ch = float(template.get("card_height_mm", 54)) * mm
    margins = template.get("page_margins_mm", {"top": 10, "bottom": 10, "left": 10, "right": 10})
    gap = float(template.get("gap_mm", 5)) * mm

    if single_pdf:
        cols, rows = compute_grid(template)
        lote_dir = output_dir or (get_cartoes_dir() / "LOTES")
        lote_dir.mkdir(parents=True, exist_ok=True)
        out = lote_dir / f"CARTOES_{card_code}_{timestamp}.pdf"
        c = pdfcanvas.Canvas(str(out), pagesize=A4)
        page_w, page_h = A4
        start_x = float(margins.get("left", 10)) * mm
        start_y_top = page_h - float(margins.get("top", 10)) * mm
        for i, emp in enumerate(valid):
            idx = i % (cols * rows)
            col = idx % cols
            row = idx // cols
            x = start_x + col * (cw + gap)
            y = start_y_top - (row + 1) * ch - row * gap
            _draw_card(c, x, y, template, emp, logo_path)
            if idx == cols * rows - 1 or i == len(valid) - 1:
                c.showPage()
        c.save()
        generated.append(out)
    else:
        page_w, page_h = A4
        for emp in valid:
            emp_dir = output_dir or (get_cartoes_dir() / _pasta_cartao(emp))
            emp_dir.mkdir(parents=True, exist_ok=True)
            out = emp_dir / f"CARTAO_{_sanitize_filename(emp.nome)}_{card_code}.pdf"
            c = pdfcanvas.Canvas(str(out), pagesize=A4)
            x = (page_w - cw) / 2
            y = (page_h - ch) / 2
            _draw_card(c, x, y, template, emp, logo_path)
            c.showPage()
            c.save()
            generated.append(out)

    _disparar_sync(generated, valid, single_pdf)

    return generated, missing


def _pasta_cartao(emp) -> str:
    """Subpasta do funcionario em data/cartoes (CPF so em colisao)."""
    from src.utils.folder_utils import employee_folder_name
    from src.core.employee_repo import EmployeeRepository
    return employee_folder_name(emp, EmployeeRepository().get_all(limit=1000000))


def _disparar_sync(generated: List[Path], valid, single_pdf: bool):
    """Espelha cartoes gerados na rede (best-effort, thread a parte)."""
    try:
        from src.core import network_sync
        if not generated:
            return
        if single_pdf:
            network_sync.run_async(network_sync.sync_card_lote, generated[0])
        else:
            for out, emp in zip(generated, valid):
                network_sync.run_async(network_sync.sync_card, out, emp)
    except Exception:
        pass
