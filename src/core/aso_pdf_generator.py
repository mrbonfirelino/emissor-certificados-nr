"""Gera o PDF modelo do ASO (Atestado de Saude Ocupacional).

O documento tem um quadro reservado para colar/anexar o ASO real (digitalizado).
"""
from datetime import date
from pathlib import Path
from dateutil.relativedelta import relativedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

PRIMARY = "#1B3A5C"
TEXT = "#333333"
MUTED = "#999999"
BORDER = "#CCCCCC"


def _br(iso: str) -> str:
    if iso and len(iso) == 10 and iso[4] == "-":
        return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
    return iso or "-"


def generate_aso_pdf(output_path: str, aso_number: str, employee, tipo_aso: str,
                     data_exame: str, validade_meses: int = 12,
                     has_doc: bool = False) -> str:
    """Gera o PDF do ASO. employee = Employee (modelo). Retorna o caminho.

    has_doc=True indica que o documento do medico esta anexado nas paginas
    seguintes (v1.16.0) e o quadro reservado muda de texto.
    """
    from src.utils.paths import get_logo_path

    try:
        from src.core.config import load_company_config
        cfg = load_company_config()
        empresa = cfg.empresa_nome if cfg else "Configurar empresa em Configuracoes"
    except Exception:
        empresa = "Configurar empresa em Configuracoes"

    c = pdfcanvas.Canvas(output_path, pagesize=A4)
    W, H = A4
    margem = 15 * mm

    # ── Cabecalho ──
    logo = get_logo_path()
    y = H - margem - 12 * mm
    if logo and logo.exists():
        try:
            from reportlab.lib.utils import ImageReader
            c.drawImage(ImageReader(str(logo)), margem, H - margem - 16 * mm,
                        width=26 * mm, height=16 * mm, mask='auto', preserveAspectRatio=True)
        except Exception:
            pass
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(W - margem, y, empresa)
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawRightString(W - margem, y - 5 * mm, "Documento de gestao de saude ocupacional")

    # ── Titulo ──
    y -= 16 * mm
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W / 2, y, "ATESTADO DE SAUDE OCUPACIONAL (ASO)")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W / 2, y - 6 * mm, f"Tipo: {tipo_aso}")

    # ── Dados do funcionario ──
    y -= 16 * mm
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margem, y, "DADOS DO FUNCIONARIO")
    y -= 2 * mm
    c.setStrokeColor(BORDER)
    c.line(margem, y, W - margem, y)

    from src.utils.validators import formatar_telefone
    linhas = [
        ("Nome", employee.nome, "CPF", employee.cpf or "-"),
        ("Funcao", employee.funcao or "-", "Telefone", formatar_telefone(employee.telefone) if employee.telefone else "-"),
        ("Data de Admissao", _br(getattr(employee, "data_admissao", None)), "Tipo Sanguineo", getattr(employee, "tipo_sanguineo", None) or "-"),
    ]
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    for label1, val1, label2, val2 in linhas:
        c.setFillColor(MUTED)
        c.drawString(margem, y, f"{label1}:")
        c.setFillColor(TEXT)
        c.drawString(margem + 28 * mm, y, str(val1))
        c.setFillColor(MUTED)
        c.drawString(margem + 95 * mm, y, f"{label2}:")
        c.setFillColor(TEXT)
        c.drawString(margem + 123 * mm, y, str(val2))
        y -= 6 * mm

    # ── Dados do exame ──
    y -= 4 * mm
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margem, y, "DADOS DO EXAME")
    y -= 2 * mm
    c.setStrokeColor(BORDER)
    c.line(margem, y, W - margem, y)
    try:
        d_exame = date.fromisoformat(data_exame)
        d_validade = d_exame + relativedelta(months=validade_meses or 12)
        validade_str = d_validade.strftime("%d/%m/%Y")
    except ValueError:
        d_exame = None
        validade_str = "-"
    exame_linhas = [
        ("Numero do ASO", aso_number, "Data do Exame", _br(data_exame)),
        ("Validade", f"{validade_meses or 12} meses (ate {validade_str})", "", ""),
    ]
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    for label1, val1, label2, val2 in exame_linhas:
        c.setFillColor(MUTED)
        c.drawString(margem, y, f"{label1}:")
        c.setFillColor(TEXT)
        c.drawString(margem + 28 * mm, y, str(val1))
        if label2:
            c.setFillColor(MUTED)
            c.drawString(margem + 95 * mm, y, f"{label2}:")
            c.setFillColor(TEXT)
            c.drawString(margem + 123 * mm, y, str(val2))
        y -= 6 * mm

    # ── Quadro reservado ──
    y -= 4 * mm
    box_top = y
    box_h = 100 * mm
    box_w = W - 2 * margem
    c.setStrokeColor(BORDER)
    c.setDash(4, 4)
    c.roundRect(margem, box_top - box_h, box_w, box_h, 4 * mm)
    c.setDash()
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 13)
    if has_doc:
        c.drawCentredString(W / 2, box_top - box_h / 2 + 8 * mm, "DOCUMENTO DO ASO ANEXADO")
        c.setFont("Helvetica", 9)
        c.drawCentredString(W / 2, box_top - box_h / 2 - 1 * mm, "Documento do medico anexado ao template nas paginas seguintes")
    else:
        c.drawCentredString(W / 2, box_top - box_h / 2 + 8 * mm, "ESPACO RESERVADO PARA O ASO")
        c.setFont("Helvetica", 9)
        c.drawCentredString(W / 2, box_top - box_h / 2 - 1 * mm, "Cole aqui o documento original ou anexe o ASO digitalizado")
        c.drawCentredString(W / 2, box_top - box_h / 2 - 6 * mm, "(botao 'Anexar' ou 'Digitalizar' na tela de ASOs)")

    # ── Assinaturas ──
    y = box_top - box_h - 22 * mm
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.6)
    ass_w = 70 * mm
    c.line(margem, y, margem + ass_w, y)
    c.line(W - margem - ass_w, y, W - margem, y)
    c.setFont("Helvetica", 9)
    c.setFillColor(TEXT)
    c.drawCentredString(margem + ass_w / 2, y - 5 * mm, "Assinatura do Funcionario")
    c.drawCentredString(W - margem - ass_w / 2, y - 5 * mm, "Medico Responsavel / CRM")

    # ── Rodape ──
    c.setFont("Helvetica", 7)
    c.setFillColor("#CCCCCC")
    c.drawRightString(W - margem, margem / 2, aso_number)
    c.drawString(margem, margem / 2, date.today().strftime("Emitido em %d/%m/%Y"))

    c.showPage()
    c.save()
    return output_path


def _moldura_aso(page, aso_number: str, tipo_aso: str, empresa: str,
                 logo_path, idx: int, total: int, W: float, H: float):
    """Desenha a moldura Altec (cabecalho + rodape) numa pagina do doc (v1.21.0)."""
    import fitz

    margem = 15.0
    primary = (0.106, 0.227, 0.361)  # #1B3A5C
    muted = (0.55, 0.58, 0.62)

    if logo_path:
        try:
            page.insert_image(
                fitz.Rect(margem, 12, margem + 74, 12 + 46),
                filename=logo_path, keep_proportion=True,
            )
        except Exception:
            pass

    sub = f"ASO {aso_number} - {tipo_aso} - Documento do medico"
    w_sub = fitz.get_text_length(sub, fontname="helv", fontsize=8)
    page.insert_text(fitz.Point(W - margem - w_sub, 24), sub,
                     fontname="helv", fontsize=8, color=muted)

    if empresa:
        w_emp = fitz.get_text_length(empresa, fontname="hebo", fontsize=11)
        page.insert_text(fitz.Point(W - margem - w_emp, 42), empresa,
                         fontname="hebo", fontsize=11, color=primary)

    page.draw_line(fitz.Point(margem, 70), fitz.Point(W - margem, 70),
                   color=primary, width=0.8)
    page.draw_line(fitz.Point(margem, H - 48), fitz.Point(W - margem, H - 48),
                   color=primary, width=0.6)

    rodape = f"Pagina {idx} de {total}"
    page.insert_text(fitz.Point(margem, H - 36), rodape,
                     fontname="helv", fontsize=7.5, color=muted)
    w_num = fitz.get_text_length(aso_number, fontname="helv", fontsize=7.5)
    page.insert_text(fitz.Point(W - margem - w_num, H - 36), aso_number,
                     fontname="helv", fontsize=7.5, color=muted)


def rebuild_aso_pdf(aso: dict, employee, doc_bytes: bytes, doc_tipo: str) -> str:
    """Regenera o PDF do ASO com o documento em moldura Altec (v1.21.0).

    Pagina 1 = capa (dados, has_doc=True); cada pagina do documento do
    medico (PDF ou imagem) vira uma pagina A4 com cabecalho/rodape Altec
    (logo + empresa + numero do ASO) e o conteudo encaixado na area
    central. Grava no proprio aso['pdf_path'] e retorna o caminho.
    """
    import tempfile
    import fitz

    pdf_path = aso["pdf_path"]

    try:
        from src.core.config import load_company_config
        empresa = (load_company_config().empresa or "").upper()
    except Exception:
        empresa = ""
    logo_path = None
    try:
        from src.utils.paths import get_logo_path
        p = get_logo_path()
        if p and Path(p).exists():
            logo_path = str(p)
    except Exception:
        logo_path = None

    W, H = fitz.paper_size("a4")
    margem = 15.0
    rect = fitz.Rect(margem, 88, W - margem, H - 58)

    with tempfile.TemporaryDirectory(prefix="normatech_aso_") as td:
        capa = str(Path(td) / "capa.pdf")
        generate_aso_pdf(
            capa, aso["aso_number"], employee, aso["tipo_aso"],
            aso["data_exame"], aso.get("validade_meses", 12), has_doc=True,
        )
        out = fitz.open(capa)
        try:
            if (doc_tipo or "pdf").lower() == "pdf":
                src = fitz.open(stream=doc_bytes, filetype="pdf")
                total = src.page_count
                for i in range(total):
                    page = out.new_page(width=W, height=H)
                    _moldura_aso(page, aso["aso_number"], aso["tipo_aso"],
                                 empresa, logo_path, i + 1, total, W, H)
                    page.show_pdf_page(rect, src, i)
                src.close()
            else:
                total = 1
                page = out.new_page(width=W, height=H)
                _moldura_aso(page, aso["aso_number"], aso["tipo_aso"],
                             empresa, logo_path, 1, total, W, H)
                page.insert_image(rect, stream=doc_bytes, keep_proportion=True)
            out.save(pdf_path, deflate=True)
        finally:
            out.close()
    return pdf_path


def rebuild_aso_pdf_sem_doc(aso: dict, employee) -> str:
    """Regenera apenas a capa (documento removido) e grava no pdf_path."""
    generate_aso_pdf(
        aso["pdf_path"], aso["aso_number"], employee, aso["tipo_aso"],
        aso["data_exame"], aso.get("validade_meses", 12), has_doc=False,
    )
    return aso["pdf_path"]
