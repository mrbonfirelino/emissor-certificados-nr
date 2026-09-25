"""Gerador do documento 'Solicitacao de Abastecimento' (ROADMAP 2.29.2).

PDF A4 com logotipo da empresa (config), dados da solicitacao e campos
de assinatura do condutor e do campo "Aprovado" (sem nome — 2.32.2).
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from src.utils.paths import get_data_dir, get_logo_path
from src.core.frota_repo import (
    label_combustivel, veiculo_rotulo, SEM_PLACA,
)

AZUL = HexColor("#1F4E79")
CINZA = HexColor("#595959")
BORDA = HexColor("#8FA8C8")
FUNDO = HexColor("#EEF3F9")


def _fonte(nome_padrao: str, tamanho: int, **kwargs) -> ParagraphStyle:
    """Helvetica builtin do reportlab cobre acentuacao latin-1; o projeto
    nao embute TTFs (assets/fonts vazio, mesmo padrao do pdf_generator)."""
    base = "Helvetica"
    if nome_padrao.endswith("-bold"):
        base = "Helvetica-Bold"
        nome_padrao = nome_padrao[:-5]
    return ParagraphStyle(
        nome_padrao, fontName=base, fontSize=tamanho, **kwargs)


def get_abastecimentos_dir() -> Path:
    pasta = get_data_dir() / "abastecimentos"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def gerar_pdf_abastecimento(dados: dict, watermark: str = "") -> Path:
    """Gera o PDF e devolve o caminho.

    dados: serial, data_br, veiculo (dict do repo), fornecedor (dict|None),
    condutor (str), viagem_servico, km, obs,
    config (load_company_config()).
    watermark: texto grande atravessando a página (ex.: 'CANCELADO') para
    solicitações bloqueadas/canceladas (roadmap 2.40.2).
    """
    serial = dados["serial"]

    style_titulo = _fonte("titulo-bold", 17, alignment=TA_CENTER,
                          textColor=AZUL, leading=21)
    style_sub = _fonte("sub", 10.5, alignment=TA_CENTER, textColor=CINZA,
                       leading=13)
    style_ser = _fonte("ser-bold", 14, alignment=TA_CENTER, textColor=AZUL,
                       leading=17)
    style_label = _fonte("lb-bold", 9, textColor=CINZA, leading=11)
    style_valor = _fonte("val", 10.5, leading=13)
    style_obs = _fonte("obs", 9.5, textColor=CINZA, leading=12)
    style_sig_name = _fonte("sign-bold", 10, alignment=TA_CENTER, leading=13)
    style_sig_det = _fonte("sigdet", 8.5, alignment=TA_CENTER,
                           textColor=CINZA, leading=11)

    story = []

    # Cabecalho: logo + empresa
    cfg = dados.get("config")
    logo = get_logo_path()
    cabeçalho: list = []
    if logo and logo.exists():
        img = Image(str(logo), width=42 * mm, height=22 * mm)
        cabeçalho.append(img)
    empresa = getattr(cfg, "empresa_nome", None) or ""
    cnpj = getattr(cfg, "empresa_cnpj", None) or ""
    local = getattr(cfg, "local_treinamento", None) or ""
    linhas_emp = [f"<b>{empresa}</b>" if empresa else ""]
    if cnpj:
        linhas_emp.append(f"CNPJ: {cnpj}")
    if local:
        linhas_emp.append(local)
    cabeçalho.append(Paragraph("<br/>".join(l for l in linhas_emp if l),
                               _fonte("emp", 10, alignment=TA_LEFT,
                                      leading=13)))
    t_topo = Table([[cabeçalho]], colWidths=[170 * mm])
    t_topo.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_topo)
    story.append(Spacer(1, 10 * mm))

    story.append(Paragraph("SOLICITAÇÃO DE ABASTECIMENTO", style_titulo))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Documento interno de solicitação de combustível",
                           style_sub))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"<b>{serial}</b>", style_ser))
    story.append(Spacer(1, 8 * mm))

    def _celula(rotulo, valor):
        return [Paragraph(rotulo.upper(), style_label),
                Paragraph(str(valor or "—"), style_valor)]

    v = dados.get("veiculo") or {}
    rotulo_veic = veiculo_rotulo(v)
    if not v.get("placa"):
        rotulo_veic = f"{rotulo_veic} (sem placa)"
    # propriedade do veiculo (próprio ou alugado + contratante)
    if v.get("proprio"):
        rotulo_veic += " — Próprio"
    elif v.get("contratante"):
        rotulo_veic += f" — Alugado (contratante: {v['contratante']})"
    forn = dados.get("fornecedor") or {}
    forn_txt = forn.get("nome") or "—"
    if forn.get("cnpj"):
        forn_txt += f" · CNPJ {forn['cnpj']}"

    pares = [
        ("Serial", serial),
        ("Data da solicitação", dados.get("data_br") or "—"),
        ("Veículo", rotulo_veic),
        ("Combustível", label_combustivel(dados.get("combustivel", ""))),
        ("KM do veículo", str(dados.get("km")) if dados.get("km")
         not in (None, "") else "—"),
        ("Viagem / Serviço", dados.get("viagem_servico") or "—"),
        ("Fornecedor (posto)", forn_txt),
        ("Condutor", dados.get("condutor") or "—"),
    ]
    linhas = []
    for rot, val in pares:
        linhas.append([Paragraph(rot.upper(), style_label),
                       Paragraph(str(val), style_valor)])
    t_dados = Table(linhas, colWidths=[48 * mm, 122 * mm])
    t_dados.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BORDA),
        ("BACKGROUND", (0, 0), (0, -1), FUNDO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_dados)

    # ---- Itens extras (2.35.2 / 2.37.1): SEM valores no documento —
    # apenas Descrição | Qtde (custo fica só no sistema) ----
    extras = [e for e in (dados.get("extras") or [])
              if isinstance(e, dict) and str(e.get("desc") or "").strip()]
    if extras:
        style_extra_hd = _fonte("extrahd-bold", 8.5, textColor=CINZA,
                                leading=11)
        style_extra_val = _fonte("extraval", 9.5, leading=12)

        linhas_ex = [[Paragraph("DESCRIÇÃO", style_extra_hd),
                      Paragraph("QTDE", style_extra_hd)]]
        for e in extras:
            linhas_ex.append([
                Paragraph(str(e.get("desc") or "—"), style_extra_val),
                Paragraph(str(e.get("qtd") or "—"), style_extra_val),
            ])
        t_ex = Table(linhas_ex, colWidths=[130 * mm, 40 * mm])
        t_ex.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, BORDA),
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("ITENS EXTRAS", style_label))
        story.append(Spacer(1, 1.5 * mm))
        story.append(t_ex)

    obs = (dados.get("obs") or "").strip()
    if obs:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("DESCRIÇÃO / OBSERVAÇÕES", style_label))
        story.append(Spacer(1, 1.5 * mm))
        t_obs = Table([[Paragraph(obs, style_obs)]], colWidths=[170 * mm])
        t_obs.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, BORDA),
            ("BACKGROUND", (0, 0), (-1, -1), FUNDO),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t_obs)

    story.append(Spacer(1, 22 * mm))

    # Assinaturas: condutor + aprovação (sem nome — roadmap 2.32.2)
    condutor = dados.get("condutor") or ""
    t_ass = Table(
        [[
            [Spacer(1, 12 * mm),
             Paragraph("_" * 34, style_sig_det),
             Spacer(1, 2 * mm),
             Paragraph(condutor or "Condutor", style_sig_name),
             Paragraph("Condutor", style_sig_det)],
            "",
            [Spacer(1, 12 * mm),
             Paragraph("_" * 34, style_sig_det),
             Spacer(1, 2 * mm),
             Paragraph("Aprovado", style_sig_name),
             Paragraph("Aprovação do Superior", style_sig_det)],
        ]],
        colWidths=[75 * mm, 20 * mm, 75 * mm])
    t_ass.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(t_ass)

    pasta = get_abastecimentos_dir()
    destino = pasta / f"{serial}.pdf"
    doc = SimpleDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Solicitação de Abastecimento {serial}")

    # 2.37.1: revisão fica só no sistema — documento sem marcação de REV
    if watermark:
        marca = str(watermark).upper()

        def _desenha_marca(canvas, _doc):
            canvas.saveState()
            try:
                canvas.setFillColor(HexColor("#C0392B"))
                canvas.setFillAlpha(0.16)
                canvas.setFont("Helvetica-Bold", 96)
                canvas.translate(A4[0] / 2, A4[1] / 2)
                canvas.rotate(45)
                canvas.drawCentredString(0, -34, marca)
                canvas.setFont("Helvetica-Bold", 20)
                canvas.drawCentredString(0, -140, marca)
            finally:
                canvas.restoreState()

        doc.build(story, onFirstPage=_desenha_marca, onLaterPages=_desenha_marca)
    else:
        doc.build(story)
    return destino
