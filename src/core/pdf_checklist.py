"""Gerador do 'Relatorio de Verificacao - Veiculos Leves' (ROADMAP 2.29.5).

Replica o formulario em papel da ALTEC (CHECK LIST - SEMANAL): grade de
itens com colunas 2a a sab, marcações S/N vindas do portal, quadro do
veiculo com legenda de avarias, observacoes por dia e assinaturas.
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from src.utils.paths import get_data_dir, get_logo_path
from src.core.frota_repo import CHECKLIST_GRUPOS, CHECKLIST_DIAS

AZUL = HexColor("#1F4E79")
CINZA = HexColor("#595959")
VERMELHO = HexColor("#B71C1C")

MEIA = 93 * mm   # meia largura util (A4 - margens 12mm)
LARG_TOTAL = 186 * mm


def get_checklists_dir() -> Path:
    pasta = get_data_dir() / "frota" / "checklists"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _fonte(nome: str, tamanho: int, **kwargs) -> ParagraphStyle:
    base = "Helvetica"
    if nome.endswith("-bold"):
        base = "Helvetica-Bold"
        nome = nome[:-5]
    return ParagraphStyle(nome, fontName=base, fontSize=tamanho, **kwargs)


def _marca(valor: str) -> Paragraph:
    """Celula da grade: 'S' preto, 'N' vermelho, vazio se nao marcado."""
    if valor == "S":
        return Paragraph("<b>S</b>", _fonte("s", 8, alignment=TA_CENTER))
    if valor == "N":
        return Paragraph("<b>N</b>", _fonte("n", 8, alignment=TA_CENTER,
                                            textColor=VERMELHO))
    return Paragraph("", _fonte("v", 8, alignment=TA_CENTER))


def _estilo_grade(linhas: int, colunas: int) -> TableStyle:
    return TableStyle([
        ("GRID", (1, 0), (-1, -1), 0.5, HexColor("#444444")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ])


def _meia_grade(titulo: str, itens, itens_marcados: dict,
                largura_label: float) -> Table:
    """Bloco [titulo preto + linhas de item x 6 dias] de meia pagina."""
    style_tit = _fonte("gt-bold", 8, alignment=TA_LEFT, textColor=white,
                       leading=10)
    style_it = _fonte("it", 7.5, leading=9)
    larg_dia = (MEIA - largura_label) / len(CHECKLIST_DIAS)
    dados = [[Paragraph(titulo, style_tit)] + [""] * len(CHECKLIST_DIAS)]
    rotulos = {}
    for _, _, itens_g in CHECKLIST_GRUPOS:
        for num, lab in itens_g:
            rotulos[num] = lab
    for num, _lab in itens:
        linha = [Paragraph(f"<b>{num}</b> {rotulos.get(num, '')}", style_it)]
        for dia in CHECKLIST_DIAS:
            linha.append(_marca((itens_marcados.get(num) or {}).get(dia)))
        dados.append(linha)
    t = Table(dados, colWidths=[largura_label] + [larg_dia] * len(CHECKLIST_DIAS),
              rowHeights=[6 * mm] + [5.1 * mm] * (len(dados) - 1))
    t.setStyle(_estilo_grade(len(dados), len(CHECKLIST_DIAS) + 1))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1A1A1A")),
        ("SPAN", (0, 0), (-1, 0)),
    ]))
    # cabecalho dos dias na segunda linha
    dados.insert(1, [""] + [Paragraph(f"<b>{d}</b>",
                _fonte("d", 7, alignment=TA_CENTER)) for d in CHECKLIST_DIAS])
    return t


def gerar_pdf_checklist(dados: dict) -> Path:
    """Gera o PDF preenchido e devolve o caminho.

    dados: serial, veiculo (dict), data_inicial_br, data_final_br, km_rodado,
    placa, motorista, lider, pode_operar ('S'|'N'), itens, observacoes,
    config (load_company_config()).
    """
    serial = dados["serial"]
    itens_marcados = dados.get("itens") or {}
    obs = dados.get("observacoes") or {}

    style_titulo = _fonte("t-bold", 12, alignment=TA_CENTER, leading=15)
    style_sub = _fonte("s-bold", 10, alignment=TA_CENTER, leading=13)
    style_campo = _fonte("c", 8, leading=10)
    style_campo_b = _fonte("cb-bold", 8, leading=10)
    style_instr = _fonte("i", 8, leading=10)
    style_obs_t = _fonte("o", 8, leading=11)
    style_sig = _fonte("sig", 9, alignment=TA_CENTER, leading=11)
    style_leg = _fonte("lg", 6.5, leading=8, textColor=CINZA)

    story = []

    # ---- cabecalho: logo + bloco de titulos/campos ----
    bloco = Table([
        [Paragraph("RELATÓRIO DE VERIFICAÇÃO - VEÍCULOS LEVES",
                   style_titulo), ""],
        [Paragraph("CHECK LIST - SEMANAL", style_sub), ""],
        [Paragraph(f"Data Inicial: <b>{dados.get('data_inicial_br') or '—'}</b>",
                   style_campo),
         Paragraph(f"Data Final: <b>{dados.get('data_final_br') or '—'}</b>",
                   style_campo)],
        [Paragraph(f"KM Rodado: <b>{dados.get('km_rodado') or '—'}</b>",
                   style_campo),
         Paragraph(f"Placa do Veículo: <b>{dados.get('placa') or '—'}</b>",
                   style_campo)],
    ], colWidths=[MEIA / 2, MEIA / 2])
    bloco.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, HexColor("#1A1A1A")),
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (0, 1), (1, 1)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    logo = get_logo_path()
    esq = []
    if logo and logo.exists():
        esq = [Image(str(logo), width=34 * mm, height=17 * mm)]
    topo = Table([[esq or "", bloco]], colWidths=[40 * mm, LARG_TOTAL - 40 * mm])
    topo.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
    ]))
    story.append(topo)
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph(
        "Assinale a alternativa <b>S (SIM ATENDE)</b> e <b>N (NÃO ATENDE)</b>"
        " para os itens de verificação abaixo.", style_instr))
    story.append(Spacer(1, 2 * mm))

    # ---- secao 1: duas colunas (1.1-1.14 | 1.15-1.19 + quadro veiculo) ----
    g1 = CHECKLIST_GRUPOS[0][2]
    esq_tbl = _meia_grade(CHECKLIST_GRUPOS[0][1], g1[:14], itens_marcados,
                          40 * mm)
    dir_itens = _meia_grade(CHECKLIST_GRUPOS[0][1], g1[14:], itens_marcados,
                            40 * mm)
    quadro = Table(
        [[Paragraph("<b>veículo</b>",
                    _fonte("vq", 8, alignment=TA_CENTER,
                           textColor=CINZA))]] +
        [[""] for _ in range(4)],
        colWidths=[MEIA - 40 * mm],
        rowHeights=[4 * mm] + [4.6 * mm] * 4)
    quadro.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#777777")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    legenda = Paragraph(
        "A amassado &nbsp; R riscado &nbsp; X quebrado &nbsp; F faltante"
        " &nbsp; T trincado &nbsp; M Machucado", style_leg)
    dir_tbl = Table(
        [[dir_itens], [quadro], [legenda]],
        colWidths=[MEIA],
        rowHeights=[None, None, 4 * mm])
    dir_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(Table([[esq_tbl, dir_tbl]], colWidths=[MEIA, MEIA],
                       style=TableStyle([
                           ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                       ])))
    story.append(Spacer(1, 2.5 * mm))

    # ---- secoes 2 e 3 lado a lado ----
    g2 = CHECKLIST_GRUPOS[1][2]
    g3 = CHECKLIST_GRUPOS[2][2]
    t2 = _meia_grade(CHECKLIST_GRUPOS[1][1], g2, itens_marcados, 40 * mm)
    t3 = _meia_grade(CHECKLIST_GRUPOS[2][1], g3, itens_marcados, 40 * mm)
    story.append(Table([[t2, t3]], colWidths=[MEIA, MEIA],
                       style=TableStyle([
                           ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                       ])))
    story.append(Spacer(1, 2.5 * mm))

    # ---- faixa "pode-se operar com seguranca" ----
    pode = dados.get("pode_operar")
    sim = "<b>[ X ]</b> SIM" if pode == "S" else "[&nbsp;&nbsp;] SIM"
    nao = "<b>[ X ]</b> NÃO" if pode == "N" else "[&nbsp;&nbsp;] NÃO"
    t_pode = Table([[Paragraph(
        f"<b>Pode-se operar com Segurança?</b> &nbsp; {sim} &nbsp;&nbsp;"
        f" {nao} ( Se não, comunique imediatamente ao Líder imediato )",
        _fonte("p", 8.5, textColor=white, leading=11))]],
        colWidths=[LARG_TOTAL])
    t_pode.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#1A1A1A")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_pode)
    story.append(Spacer(1, 2.5 * mm))

    # ---- observacoes por dia ----
    t_obs_tit = Table([[Paragraph(
        "<b>Observações:</b> ( Sempre que colocarmos N (NÃO ATENDE) -"
        " Informar o que foi encontrado. )", style_instr)]],
        colWidths=[LARG_TOTAL])
    t_obs_tit.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, HexColor("#1A1A1A")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_obs_tit)
    linhas_obs = []
    for dia in CHECKLIST_DIAS:
        texto = (obs.get(dia) or "").strip()
        linhas_obs.append([
            Paragraph(f"<b>{dia}</b>", _fonte("od", 8, alignment=TA_CENTER,
                                              leading=10)),
            Paragraph(texto or "", style_obs_t),
        ])
    t_obs = Table(linhas_obs, colWidths=[12 * mm, LARG_TOTAL - 12 * mm],
                  rowHeights=[6.5 * mm] * len(linhas_obs))
    t_obs.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, HexColor("#1A1A1A")),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, HexColor("#AAAAAA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_obs)
    story.append(Spacer(1, 8 * mm))

    # ---- assinaturas: motorista + lider ----
    t_ass = Table(
        [[
            [Spacer(1, 10 * mm),
             Paragraph("_" * 34, _fonte("l1", 8.5, alignment=TA_CENTER,
                                        leading=10)),
             Spacer(1, 1.5 * mm),
             Paragraph(dados.get("motorista") or "Motorista", style_sig),
             Paragraph("Assinatura do Motorista",
                       _fonte("l2", 8, alignment=TA_CENTER, leading=10))],
            "",
            [Spacer(1, 10 * mm),
             Paragraph("_" * 34, _fonte("l3", 8.5, alignment=TA_CENTER,
                                        leading=10)),
             Spacer(1, 1.5 * mm),
             Paragraph(dados.get("lider") or "Líder", style_sig),
             Paragraph("Assinatura do Líder",
                       _fonte("l4", 8, alignment=TA_CENTER, leading=10))],
        ]],
        colWidths=[75 * mm, 20 * mm, 75 * mm])
    t_ass.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(t_ass)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "OBS: Ao término de cada semana o formulário deve ser entregue para"
        " a Administração para arquivo.",
        _fonte("f", 7.5, alignment=TA_CENTER, textColor=CINZA, leading=9)))

    pasta = get_checklists_dir()
    destino = pasta / f"{serial}.pdf"
    doc = SimpleDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
        title=f"Checklist Semanal {serial}")
    doc.build(story)
    return destino
