"""Gera o PDF da Ficha de EPI (Entrega e Devolucao de Equipamentos).

Formato A4 com tabela dupla: entrega (CA/Descricao/Qtde/Data/Visto) e
devolucao (Qtde/Data/Visto). Celulas de visto ficam em branco para assinatura
de punho. Regeneravel a cada edicao dos itens.

v1.17.0: linha de item com 11mm (dado + estado da devolucao + separador sem
sobreposicao), cabecalho de colunas em faixa propria, estado por item
(Total/Parcial) destacado, linhas em branco dinamicas e quebra de pagina com
repeticao do cabecalho da tabela.
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
SUCCESS = "#2E7D32"
WARNING = "#BF5300"

# larguras das colunas de entrega (mm) — total ~180
COL_CA = 24 * mm
COL_DESC = 74 * mm
COL_QTDE = 16 * mm
COL_DATA = 26 * mm
COL_VISTO = 40 * mm
LINHAS_MINIMAS = 6          # total de linhas (itens + brancas) no minimo
PASSO_ITEM = 11 * mm        # dado + linha de devolucao + separador
PASSO_BRANCO = 7 * mm


def _br(iso: str) -> str:
    if iso and len(iso) == 10 and iso[4] == "-":
        return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
    return iso or ""


def _estado(item) -> str:
    """Pendente / Total / Parcial conforme dev_quantidade vs quantidade."""
    qtd = str(item.get("quantidade", "")).strip()
    dev = str(item.get("dev_quantidade", "")).strip()
    if not dev:
        return ""
    if qtd and dev == qtd:
        return "Total"
    return "Parcial"


def _cabecalho_pagina(c, W, H, margem, empresa):
    logo = None
    try:
        from src.utils.paths import get_logo_path
        logo = get_logo_path()
    except Exception:
        logo = None
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


def _rodape(c, W, margem, numero: str):
    c.setFont("Helvetica", 7)
    c.setFillColor("#CCCCCC")
    c.drawRightString(W - margem, margem / 2, numero)
    c.drawString(margem, margem / 2, date.today().strftime("Emitido em %d/%m/%Y"))


def generate_epi_pdf(output_path: str, epi_number: str, employee, data_emissao: str,
                     items: list) -> str:
    """Gera/regenera o PDF da ficha. items: [{ca, descricao, quantidade,
    data_entrega, dev_quantidade, dev_data}]. Retorna o caminho."""
    try:
        from src.core.config import load_company_config
        cfg = load_company_config()
    except Exception:
        cfg = None
    if cfg:
        empresa = cfg.empresa_nome or "Configurar empresa em Configuracoes"
    else:
        empresa = "Configurar empresa em Configuracoes"

    c = pdfcanvas.Canvas(output_path, pagesize=A4)
    W, H = A4
    margem = 15 * mm
    total_w = COL_CA + COL_DESC + COL_QTDE + COL_DATA + COL_VISTO
    limite = margem + 12 * mm          # zona do rodape reservada

    # ── Cabecalho da pagina 1 ──
    _cabecalho_pagina(c, W, H, margem, empresa)

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

    # ── TERMO DE COMPROMISSO (1a folha, v1.47.0) ──
    local_txt = (getattr(cfg, "local_treinamento", "") or "").strip() if cfg else ""
    cnpj_txt = (getattr(cfg, "empresa_cnpj", "") or "").strip() if cfg else ""

    def _wrap_termo(texto, largura, fonte="Helvetica", tamanho=7):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        palavras = texto.split()
        linhas, atual = [], ""
        for p in palavras:
            tent = (atual + " " + p).strip()
            if stringWidth(tent, fonte, tamanho) <= largura:
                atual = tent
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas

    y -= 9 * mm
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W / 2, y, "TERMO DE COMPROMISSO")
    paragrafos = [
        "Declaro que recebi orientação sobre o uso do EPI – Equipamento de Proteção "
        "Individual fornecida pela Empresa e que estou ciente da legislação "
        "discriminada, comprometendo-me a cumpri-la.",
        "Portaria Nº 3.214, 08/06/78 – Norma Regulamentadora Nº 01 – Disposições "
        "Gerais, Item 1.8 – CABE AO EMPREGADO:",
        "a) Cumprir as disposições legais e regulamentares sobre segurança e "
        "medicina do trabalho, inclusive as ordens de serviço expedidas pelo empregador;",
        "b) Usar o EPI fornecida pelo empregador;",
        "c) Submeter-se aos exames médicos previstos nas Normas Regulamentadoras – NR 07",
        "1.8.1 – Constitui ato faltoso a recusa injustificada do empregado (a) ao "
        "cumprimento do disposto no item anterior.",
        "CLT – Artigo 462, § 1º - Em caso de dano causado pelo empregado, o desconto "
        "será licito, desde que esta possibilidade tenha sido acordada, ou na "
        "ocorrência de dolo do empregado.",
    ]
    c.setFont("Helvetica", 7)
    c.setFillColor(TEXT)
    for par in paragrafos:
        for ln in _wrap_termo(par, total_w):
            c.drawString(margem, y, ln)
            y -= 3.1 * mm
    y -= 1 * mm
    rotulo_local = f"Local: {local_txt}" if local_txt else ""
    if cnpj_txt:
        rotulo_local += (f"   —   CNPJ: {cnpj_txt}" if rotulo_local
                         else f"CNPJ: {cnpj_txt}")
    if rotulo_local:
        c.setFont("Helvetica-Bold", 7)
        c.drawString(margem, y, rotulo_local)
    y -= 6 * mm
    ass_w_t = 80 * mm
    ass_x = W / 2 - ass_w_t / 2
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.5)
    c.line(ass_x, y, ass_x + ass_w_t, y)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, y - 3.5 * mm,
                        "Assinatura do Empregado — li e estou ciente do termo acima")
    y -= 9 * mm

    # ── Tabela ──
    y -= 2 * mm

    def cabecalho_grupo(yy, titulo):
        c.setFillColor(PRIMARY)
        c.rect(margem, yy - 7 * mm, total_w, 7 * mm, fill=1, stroke=0)
        c.setFillColor("#FFFFFF")
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margem + 2 * mm, yy - 5 * mm, titulo)

    def linha_colunas(yy):
        """Cabecalho das colunas em faixa propria, com folga sob a faixa azul
        (v1.47.0: faixa de 5mm e titulos centrados — sem invadir a faixa)."""
        cols = [("C.A.", COL_CA), ("Descricao do Material", COL_DESC),
                ("Qtde", COL_QTDE), ("Data", COL_DATA), ("Visto Empregado", COL_VISTO)]
        c.setFillColor(ZEBRA)
        c.rect(margem, yy - 4 * mm, total_w, 5 * mm, fill=1, stroke=0)
        x = margem
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.line(margem, yy - 4 * mm, margem + total_w, yy - 4 * mm)
        c.line(margem, yy + 1 * mm, margem + total_w, yy + 1 * mm)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(TEXT)
        for nome, w in cols:
            c.drawCentredString(x + w / 2, yy - 2.5 * mm, nome)
            x += w

    def abre_tabela(yy):
        """Faixa do grupo + cabecalho de colunas; retorna y da primeira linha."""
        cabecalho_grupo(yy, "ENTREGA DE EQUIPAMENTO")
        yy -= 9 * mm          # 2mm de folga entre a faixa azul e a de colunas
        linha_colunas(yy)
        return yy - 5 * mm

    def linha_dados(yy, item, zebra: bool):
        """Linha de 11mm: dado + estado da devolucao + separador."""
        if zebra:
            c.setFillColor(ZEBRA)
            c.rect(margem, yy - 3 * mm, total_w, 7 * mm, fill=1, stroke=0)
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
        # linha secundaria: fabricante / lote / descartavel (v1.47.0)
        extras = []
        if (item.get("fabricante") or "").strip():
            extras.append(f"Fabricante: {str(item['fabricante']).strip()}")
        if (item.get("lote") or "").strip():
            extras.append(f"Lote: {str(item['lote']).strip()}")
        if item.get("descartavel"):
            extras.append("Descartável")
        if extras:
            c.setFont("Helvetica-Oblique", 6.5)
            c.setFillColor(MUTED)
            c.drawString(margem + COL_CA + 2 * mm, yy - 4 * mm,
                         "  ·  ".join(extras)[:75])
            c.setFont("Helvetica", 8)
            c.setFillColor(TEXT)
        # estado da devolucao destacado abaixo do dado
        est = _estado(item)
        if est:
            cor = SUCCESS if est == "Total" else WARNING
            txt = f"Devolvido: {item.get('dev_quantidade', '')}/{item.get('quantidade', '')} ({est})"
            if item.get("dev_data"):
                txt += f"  em {_br(item['dev_data'])}"
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(cor)
            c.drawCentredString(margem + total_w - (COL_VISTO + COL_DATA + COL_QTDE) / 2,
                                yy - 7 * mm, txt)
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.4)
        c.line(margem, yy - 10 * mm, margem + total_w, yy - 10 * mm)

    def linha_branca(yy, zebra: bool):
        if zebra:
            c.setFillColor(ZEBRA)
            c.rect(margem, yy - 3 * mm, total_w, 7 * mm, fill=1, stroke=0)
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.4)
        c.line(margem, yy - 3 * mm, margem + total_w, yy - 3 * mm)

    def nova_pagina_tabela():
        _rodape(c, W, margem, epi_number)
        c.showPage()
        _cabecalho_pagina(c, W, H, margem, empresa)
        return abre_tabela(H - margem - 18 * mm)

    y = abre_tabela(y)

    itens = list(items or [])
    for idx, item in enumerate(itens):
        if y - PASSO_ITEM < limite:
            y = nova_pagina_tabela()
        y -= PASSO_ITEM
        linha_dados(y, item, idx % 2 == 1)

    # linhas em branco dinamicas (minimo LINHAS_MINIMAS no total)
    for idx in range(max(0, LINHAS_MINIMAS - len(itens))):
        if y - PASSO_BRANCO < limite:
            y = nova_pagina_tabela()
        y -= PASSO_BRANCO
        linha_branca(y, (len(itens) + idx) % 2 == 1)
    y -= 4 * mm

    # grupo DEVOLUCAO (manual) — quebra se nao couber grupo + assinaturas
    precisa = 7 * mm + 9 * mm + 5 * mm + 6 * 8 * mm + 24 * mm + 8 * mm
    if y - precisa < limite:
        _rodape(c, W, margem, epi_number)
        c.showPage()
        _cabecalho_pagina(c, W, H, margem, empresa)
        y = H - margem - 18 * mm

    cabecalho_grupo(y, "DEVOLUCAO DE EQUIPAMENTO")
    y -= 9 * mm          # mesma folga do grupo ENTREGA (v1.47.0)
    cols_dev = [("Qtde", COL_QTDE + COL_CA), ("Data", COL_DATA),
                ("Visto Empregado", COL_VISTO + COL_DESC)]
    c.setFillColor(ZEBRA)
    c.rect(margem, y - 4 * mm, total_w, 5 * mm, fill=1, stroke=0)
    x = margem
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.line(margem, y - 4 * mm, margem + total_w, y - 4 * mm)
    c.line(margem, y + 1 * mm, margem + total_w, y + 1 * mm)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(TEXT)
    for nome, w in cols_dev:
        c.drawCentredString(x + w / 2, y - 2.5 * mm, nome)
        x += w
    y -= 5 * mm
    for idx in range(6):
        y -= 8 * mm
        if idx % 2 == 1:
            c.setFillColor(ZEBRA)
            c.rect(margem, y - 4 * mm, total_w, 7 * mm, fill=1, stroke=0)
        c.setStrokeColor(BORDER)
        c.line(margem, y - 4 * mm, margem + total_w, y - 4 * mm)

    # ── Assinaturas ──
    if y - 24 * mm < limite:
        _rodape(c, W, margem, epi_number)
        c.showPage()
        _cabecalho_pagina(c, W, H, margem, empresa)
        y = H - margem - 24 * mm
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

    _rodape(c, W, margem, epi_number)
    c.showPage()
    c.save()
    return output_path


def generate_devolucao_pdf(output_path: str, epi_number: str, employee,
                           data_devolucao: str, items: list) -> str:
    """Gera o Termo de Devolucao de EPI para assinatura (v1.16.0).

    items: mesma lista da ficha; usa dev_quantidade/dev_data de cada item.
    Retorna o caminho.
    """
    try:
        from src.core.config import load_company_config
        cfg = load_company_config()
        empresa = cfg.empresa_nome if cfg else "Configurar empresa em Configuracoes"
    except Exception:
        empresa = "Configurar empresa em Configuracoes"

    c = pdfcanvas.Canvas(output_path, pagesize=A4)
    W, H = A4
    margem = 15 * mm
    limite = margem + 12 * mm

    d_ca = 24 * mm
    d_desc = 74 * mm
    d_qe = 20 * mm
    d_qd = 24 * mm
    d_est = 38 * mm
    total_w = d_ca + d_desc + d_qe + d_qd + d_est

    # ── Cabecalho da pagina 1 ──
    _cabecalho_pagina(c, W, H, margem, empresa)

    # ── Titulo ──
    y = H - margem - 30 * mm
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(W / 2, y, "TERMO DE DEVOLUCAO DE EPI")
    c.setFont("Helvetica", 9)
    c.setFillColor(TEXT)
    c.drawCentredString(W / 2, y - 6 * mm,
                        f"Ficha: {epi_number}   |   Data da devolucao: {_br(data_devolucao)}")

    # ── Dados do funcionario ──
    y -= 16 * mm
    c.setFont("Helvetica", 9)
    cpf = employee.cpf or "-"
    linha1 = f"Nome: {employee.nome}          CPF: {cpf}"
    linha2 = f"Funcao: {employee.funcao or '-'}"
    c.setFillColor(TEXT)
    c.drawString(margem, y, linha1)
    c.drawString(margem, y - 5 * mm, linha2)

    # ── Tabela de itens ──
    y -= 14 * mm

    def abre_tabela(yy):
        c.setFillColor(PRIMARY)
        c.rect(margem, yy - 7 * mm, total_w, 7 * mm, fill=1, stroke=0)
        c.setFillColor("#FFFFFF")
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margem + 2 * mm, yy - 5 * mm, "ITENS DEVOLVIDOS")
        yy -= 7 * mm
        cols = [("C.A.", d_ca), ("Descricao do Material", d_desc),
                ("Qtde Entregue", d_qe), ("Qtde Devolvida", d_qd), ("Estado", d_est)]
        x = margem
        c.setFillColor(ZEBRA)
        c.rect(margem, yy - 4 * mm, total_w, 6 * mm, fill=1, stroke=0)
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.line(margem, yy - 4 * mm, margem + total_w, yy - 4 * mm)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(TEXT)
        for nome, w in cols:
            c.drawCentredString(x + w / 2, yy - 1 * mm, nome)
            x += w
        return yy - 4 * mm

    def nova_pagina_tabela():
        _rodape(c, W, margem, epi_number)
        c.showPage()
        _cabecalho_pagina(c, W, H, margem, empresa)
        return abre_tabela(H - margem - 18 * mm)

    y = abre_tabela(y)

    itens = list(items or [])
    for idx, item in enumerate(itens):
        if y - 8 * mm < limite:
            y = nova_pagina_tabela()
        y -= 8 * mm
        if idx % 2 == 1:
            c.setFillColor(ZEBRA)
            c.rect(margem, y - 4 * mm, total_w, 7 * mm, fill=1, stroke=0)
        c.setFont("Helvetica", 8)
        c.setFillColor(TEXT)
        x = margem
        est = _estado(item) or "Pendente"
        vals = [item.get("ca", ""), str(item.get("descricao", ""))[:48],
                item.get("quantidade", ""), item.get("dev_quantidade", "") or "-",
                est]
        widths = [d_ca, d_desc, d_qe, d_qd, d_est]
        for i, (val, w) in enumerate(zip(vals, widths)):
            if w == d_desc:
                c.drawString(x + 2 * mm, y, str(val))
            else:
                if i == 4:
                    c.setFont("Helvetica-Bold", 8)
                    c.setFillColor(SUCCESS if est == "Total"
                                   else WARNING if est == "Parcial" else MUTED)
                c.drawCentredString(x + w / 2, y, str(val))
                if i == 4:
                    c.setFont("Helvetica", 8)
                    c.setFillColor(TEXT)
            x += w
        c.setStrokeColor(BORDER)
        c.line(margem, y - 4 * mm, margem + total_w, y - 4 * mm)

    # ── Assinaturas ──
    if y - 26 * mm < limite:
        _rodape(c, W, margem, epi_number)
        c.showPage()
        _cabecalho_pagina(c, W, H, margem, empresa)
        y = H - margem - 24 * mm
    y -= 26 * mm
    c.setStrokeColor(TEXT)
    c.setLineWidth(0.6)
    ass_w = 70 * mm
    c.line(margem, y, margem + ass_w, y)
    c.line(W - margem - ass_w, y, W - margem, y)
    c.setFont("Helvetica", 9)
    c.setFillColor(TEXT)
    c.drawCentredString(margem + ass_w / 2, y - 5 * mm, "Assinatura do Empregado")
    c.drawCentredString(W - margem - ass_w / 2, y - 5 * mm, "Responsavel pelo Recebimento")

    _rodape(c, W, margem, epi_number)
    c.showPage()
    c.save()
    return output_path
