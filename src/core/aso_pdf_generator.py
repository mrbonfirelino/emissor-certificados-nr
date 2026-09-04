"""Gera o PDF modelo do ASO (Atestado de Saude Ocupacional).

O documento tem um quadro reservado para colar/anexar o ASO real (digitalizado).
"""
from datetime import date
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
                     data_exame: str, validade_meses: int = 12) -> str:
    """Gera o PDF do ASO. employee = Employee (modelo). Retorna o caminho."""
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
