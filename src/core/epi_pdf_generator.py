"""Gera o PDF da Ficha de EPI (Entrega e Devolucao de Equipamentos).

Formato A4 com tabela dupla: entrega (CA/Descalcao/Qtde/Data/Visto) e
devolucao (Qtde/Data/Visto). Celas de visto ficam em branco para assinatura
de punho. Regeneravel a cada edicao dos itens.
"""
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

PRIMARY = "#1B3A5C"
TEXT = "#333333"
MUTED = "#999999"
BORDER = "#CCCCCC"
ZEBRA = "#F2F5F8"

# larguras das colunas de entrega (mm) — total ~180
COL_CA = 24 * mm
COL_DESC = 74 * mm
COL_QTDE = 16 * mm
COL_DATA = 26 * mm
COL_VISTO = 40 * mm
LINHAS_EXTRAS = 6


def _br(iso: str) -> str:
    if iso and len(iso) == 10 and iso[4] == "-":
        return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
    return iso or ""


def generate_epi_pdf(output_path: str, epi_number: str, employee, data_emissao: str,
                     items: list) -> str:
    """Gera/regenera o PDF da ficha. items: [{ca, descricao, quantidade,
    data_entrega, dev_quantidade, dev_data}]. Retorna o caminho."""
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
    if logo and logo.exists():
        try:
            from reportlab.lib.utils import ImageReader
            c.drawImage(ImageReader(str(logo)), margem, H - margem - 16 * mm,
                        width=26 * mm, height=16 * mm, mask='auto', preserveAspectRatio=True)
        except Exception:
            pass
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(W - margem, H - margem - 12 * mm, empresa)
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawRightString(W - margem, H - margem - 17 * mm, "Ficha de EPI — NR-6")

    # ── Titulo ──
    y = H - margem - 30 * mm
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(W / 2, y, "FICHA DE ENTREGA E DEVOLUCAO DE EPI")
    c.setFont("Helvetica", 9)
    c.setFillColor(TEXT)
    c.drawCentredString(W / 2, y - 6 * mm, f"Numero: {epi_number}   |   Emissao: {_br(data_emissao)}")

    # ── Dados do funcionario ──
    y -= 16 * mm
    c.setFont("Helvetica", 9)
    cpf = employee.cpf or "-"
    adm = getattr(employee, "data_admissao", None)
    linha1 = f"Nome: {employee.nome}          CPF: {cpf}"
    linha2 = f"Funcao: {employee.funcao or '-'}          Admissao: {_br(adm) if adm else '-'}"
    c.setFillColor(TEXT)
    c.drawString(margem, y, linha1)
    c.drawString(margem, y - 5 * mm, linha2)

    # ── Tabela ──
    y -= 14 * mm
    total_w = COL_CA + COL_DESC + COL_QTDE + COL_DATA + COL_VISTO

    def cabecalho_grupo(yy, titulo):
        c.setFillColor(PRIMARY)
        c.rect(margem, yy - 7 * mm, total_w, 7 * mm, fill=1, stroke=0)
        c.setFillColor("#FFFFFF")
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margem + 2 * mm, yy - 5 * mm, titulo)

    def linha_colunas(yy):
        cols = [("C.A.", COL_CA), ("Descricao do Material", COL_DESC),
                ("Qtde", COL_QTDE), ("Data", COL_DATA), ("Visto Empregado", COL_VISTO)]
        x = margem
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.line(margem, yy - 4 * mm, margem + total_w, yy - 4 * mm)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(TEXT)
        for nome, w in cols:
            c.drawCentredString(x + w / 2, yy, nome)
            x += w

    def linha_dados(yy, item, zebra: bool):
        if zebra:
            c.setFillColor(ZEBRA)
            c.rect(margem, yy - 4 * mm, total_w, 6.5 * mm, fill=1, stroke=0)
        c.setFont("Helvetica", 8)
        c.setFillColor(TEXT)
        x = margem
        vals = [item.get("ca", ""), item.get("descricao", ""),
                item.get("quantidade", ""), _br(item.get("data_entrega", "")), ""]
        widths = [COL_CA, COL_DESC, COL_QTDE, COL_DATA, COL_VISTO]
        for val, w in zip(vals, widths):
            if w == COL_DESC:
                c.drawString(x + 2 * mm, yy, str(val)[:48])
            else:
                c.drawCentredString(x + w / 2, yy, str(val))
            x += w
        # devolucao na mesma linha (meio tom, abaixo)
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(MUTED)
        dev = []
        if item.get("dev_quantidade"):
            dev.append(f"Devolveu: {item['dev_quantidade']}")
        if item.get("dev_data"):
            dev.append(f"em {_br(item['dev_data'])}")
        if dev:
            c.drawCentredString(margem + total_w - (COL_QTDE + COL_DATA + COL_VISTO) / 2 - COL_VISTO / 2,
                                yy - 8 * mm, "  |  ".join(dev))
        c.setStrokeColor(BORDER)
        c.line(margem, yy - 11 * mm, margem + total_w, yy - 11 * mm)

    # grupo ENTREGA
    cabecalho_grupo(y, "ENTREGA DE EQUIPAMENTO")
    y -= 7 * mm
    linha_colunas(y)
    y -= 4 * mm
    # altura base das linhas: 11mm (espaco p/ devolucao manuscrita)
    itens = list(items or [])
    for idx, item in enumerate(itens):
        y -= 7 * mm
        linha_dados(y, item, idx % 2 == 1)
    # linhas em branco para preenchimento manual
    for idx in range(LINHAS_EXTRAS):
        y -= 7 * mm
        linha_dados(y, {}, (len(itens) + idx) % 2 == 1)
    y -= 7 * mm

    # grupo DEVOLUCAO
    cabecalho_grupo(y, "DEVOLUCAO DE EQUIPAMENTO")
    y -= 7 * mm
    cols_dev = [("Qtde", COL_QTDE + COL_CA), ("Data", COL_DATA),
                ("Visto Empregado", COL_VISTO + COL_DESC)]
    x = margem
    c.setStrokeColor(BORDER)
    c.line(margem, y - 4 * mm, margem + total_w, y - 4 * mm)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(TEXT)
    for nome, w in cols_dev:
        c.drawCentredString(x + w / 2, y, nome)
        x += w
    for idx in range(6):
        y -= 8 * mm
        if idx % 2 == 1:
            c.setFillColor(ZEBRA)
            c.rect(margem, y - 4 * mm, total_w, 7 * mm, fill=1, stroke=0)
        c.setStrokeColor(BORDER)
        c.line(margem, y - 4 * mm, margem + total_w, y - 4 * mm)

    # ── Assinaturas ──
    y -= 24 * mm
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.6)
    ass_w = 70 * mm
    c.line(margem, y, margem + ass_w, y)
    c.line(W - margem - ass_w, y, W - margem, y)
    c.setFont("Helvetica", 9)
    c.setFillColor(TEXT)
    c.drawCentredString(margem + ass_w / 2, y - 5 * mm, "Assinatura do Empregado")
    c.drawCentredString(W - margem - ass_w / 2, y - 5 * mm, "Responsavel pela Entrega")

    # ── Rodape ──
    c.setFont("Helvetica", 7)
    c.setFillColor("#CCCCCC")
    c.drawRightString(W - margem, margem / 2, epi_number)
    c.drawString(margem, margem / 2, date.today().strftime("Emitido em %d/%m/%Y"))

    c.showPage()
    c.save()
    return output_path
