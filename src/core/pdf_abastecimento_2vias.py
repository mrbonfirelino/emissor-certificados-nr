"""PDF da Solicitacao de Abastecimento em 2 vias por folha A4 (v1.54.0).

Layout paisagem com 2 copias lado a lado na mesma folha (uma via para o
sistema e uma via fisica para quem emite). Reaproveita o visual do
prototipo aprovado (prototipo_abastecimento_2vias.py, roadmap 2.40.4).

Recebe o MESMO dict `dados` de gerar_pdf_abastecimento e salva em
data/abastecimentos/{serial}.pdf (mesmo caminho — pdf_path no repo
continua valido).
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from src.utils.paths import get_logo_path
from src.core.pdf_abastecimento import (
    get_abastecimentos_dir,
)
from src.core.frota_repo import (
    label_combustivel, veiculo_rotulo,
)

AZUL = HexColor("#1F4E79")
CINZA = HexColor("#595959")
BORDA = HexColor("#8FA8C8")
FUNDO = HexColor("#EEF3F9")
VERMELHO = HexColor("#C0392B")
TEXTO = HexColor("#22303F")


def _monta_pares(dados: dict) -> list:
    serial = dados["serial"]
    v = dados.get("veiculo") or {}
    rotulo_veic = veiculo_rotulo(v)
    if not v.get("placa"):
        rotulo_veic = f"{rotulo_veic} (sem placa)"
    if v.get("proprio"):
        rotulo_veic += " — Próprio"
    elif v.get("contratante"):
        rotulo_veic += f" — Alugado (contratante: {v['contratante']})"
    forn = dados.get("fornecedor") or {}
    forn_txt = forn.get("nome") or "—"
    if forn.get("cnpj"):
        forn_txt += f" · CNPJ {forn['cnpj']}"
    return [
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


def _copia(c, x0: float, y0: float, larg: float, alt: float, dados: dict,
           n_via: int):
    """Desenha UMA cópia dentro do retângulo (x0, y0, larg, alt)."""
    mg = 8 * mm
    w = larg - 2 * mg
    y = y0 + alt - mg

    c.setStrokeColor(BORDA)
    c.setLineWidth(0.8)
    c.rect(x0, y0, larg, alt)

    # cabeçalho: logo + empresa
    logo = get_logo_path()
    lh = 12 * mm
    try:
        if logo and Path(logo).exists():
            img = ImageReader(str(logo))
            iw, ih = img.getSize()
            tw = lh * iw / ih
            c.drawImage(img, x0 + mg, y - lh, width=tw, height=lh,
                        preserveAspectRatio=True, mask="auto")
    except Exception:
        pass
    cfg = dados.get("config")
    empresa = getattr(cfg, "empresa_nome", None) or ""
    cnpj = getattr(cfg, "empresa_cnpj", None) or ""
    c.setFillColor(AZUL)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(x0 + larg - mg, y - 5 * mm, empresa)
    c.setFillColor(CINZA)
    c.setFont("Helvetica", 6.5)
    if cnpj:
        c.drawRightString(x0 + larg - mg, y - 9 * mm, f"CNPJ: {cnpj}")
    y -= lh + 3 * mm

    c.setFillColor(AZUL)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawCentredString(x0 + larg / 2, y, "SOLICITAÇÃO DE ABASTECIMENTO")
    y -= 5 * mm
    c.setFillColor(CINZA)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(x0 + larg / 2, y,
                        "Documento interno de solicitação de combustível")
    y -= 6 * mm
    c.setFillColor(AZUL)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(x0 + larg / 2, y, dados["serial"])
    y -= 7 * mm

    def _linha(rotulo, valor):
        nonlocal y
        hh = 6.2 * mm
        c.setFillColor(FUNDO)
        c.rect(x0 + mg, y - hh, 34 * mm, hh, stroke=0, fill=1)
        c.setStrokeColor(BORDA)
        c.setLineWidth(0.5)
        c.rect(x0 + mg, y - hh, w, hh, stroke=1, fill=0)
        c.setFillColor(CINZA)
        c.setFont("Helvetica-Bold", 6)
        c.drawString(x0 + mg + 2 * mm, y - hh + 2.2 * mm, rotulo.upper())
        c.setFillColor(TEXTO)
        c.setFont("Helvetica", 7.5)
        c.drawString(x0 + mg + 36 * mm, y - hh + 2 * mm, str(valor or "—"))
        y -= hh

    for rot, val in _monta_pares(dados):
        _linha(rot, val)

    # itens extras (sem valores — igual ao documento de 1 via, 2.37.1)
    extras = [e for e in (dados.get("extras") or [])
              if isinstance(e, dict) and str(e.get("desc") or "").strip()]
    if extras:
        y -= 3 * mm
        c.setFillColor(CINZA)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(x0 + mg, y, "ITENS EXTRAS")
        y -= 4.5 * mm
        col1, col2 = w - 22 * mm, 22 * mm
        c.setFillColor(FUNDO)
        c.rect(x0 + mg, y - 5 * mm, col1, 5 * mm, stroke=0, fill=1)
        c.rect(x0 + mg + col1, y - 5 * mm, col2, 5 * mm, stroke=0, fill=1)
        c.setStrokeColor(BORDA)
        c.setLineWidth(0.5)
        c.rect(x0 + mg, y - 5 * mm, w, 5 * mm, stroke=1, fill=0)
        c.rect(x0 + mg + col1, y - 5 * mm, col2, 5 * mm, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(CINZA)
        c.drawString(x0 + mg + 2 * mm, y - 3.6 * mm, "DESCRIÇÃO")
        c.drawCentredString(x0 + mg + col1 + col2 / 2, y - 3.6 * mm, "QTDE")
        y -= 5 * mm
        c.setFont("Helvetica", 7)
        c.setFillColor(TEXTO)
        for e in extras:
            c.rect(x0 + mg, y - 6 * mm, w, 6 * mm, stroke=1, fill=0)
            c.rect(x0 + mg + col1, y - 6 * mm, col2, 6 * mm, stroke=1, fill=0)
            c.drawString(x0 + mg + 2 * mm, y - 4.2 * mm, str(e.get("desc")))
            c.drawCentredString(x0 + mg + col1 + col2 / 2, y - 4.2 * mm,
                                str(e.get("qtd") or "—"))
            y -= 6 * mm

    obs = (dados.get("obs") or "").strip()
    if obs:
        y -= 3 * mm
        c.setFillColor(CINZA)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(x0 + mg, y, "DESCRIÇÃO / OBSERVAÇÕES")
        y -= 4.5 * mm
        hh = 9 * mm
        c.setFillColor(FUNDO)
        c.rect(x0 + mg, y - hh, w, hh, stroke=0, fill=1)
        c.setStrokeColor(BORDA)
        c.rect(x0 + mg, y - hh, w, hh, stroke=1, fill=0)
        c.setFillColor(TEXTO)
        c.setFont("Helvetica", 6.5)
        c.drawString(x0 + mg + 2 * mm, y - 3.4 * mm, obs[:70])
        y -= hh

    # assinaturas
    y -= 11 * mm
    metade = w / 2
    condutor = dados.get("condutor") or ""
    for cx, rotulo, nome in (
            (x0 + mg + metade / 2, "Condutor", condutor or "Condutor"),
            (x0 + mg + metade * 1.5, "Aprovação do Superior", "Aprovado")):
        c.setStrokeColor(TEXTO)
        c.setLineWidth(0.6)
        c.line(cx - 24 * mm, y, cx + 24 * mm, y)
        c.setFillColor(TEXTO)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(cx, y - 4 * mm, nome)
        c.setFillColor(CINZA)
        c.setFont("Helvetica", 6)
        c.drawCentredString(cx, y - 7 * mm, rotulo)

    # identificação discreta da via
    c.setFillColor(CINZA)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x0 + mg, y0 + 3 * mm, f"VIA {n_via} DE 2")


def gerar_pdf_abastecimento_2vias(dados: dict, watermark: str = "") -> Path:
    """Gera o PDF paisagem com 2 cópias e devolve o caminho."""
    serial = dados["serial"]
    pasta = get_abastecimentos_dir()
    destino = pasta / f"{serial}.pdf"

    c = canvas.Canvas(str(destino), pagesize=landscape(A4))
    larg, alt = landscape(A4)
    meia = larg / 2
    for i in (1, 2):
        _copia(c, (i - 1) * meia, 0, meia, alt, dados, i)
        if i == 1:
            c.setStrokeColor(BORDA)
            c.setLineWidth(0.6)
            c.line(meia, 6 * mm, meia, alt - 6 * mm)

    if watermark:
        marca = str(watermark).upper()
        c.saveState()
        c.setFillColor(VERMELHO)
        try:
            c.setFillAlpha(0.16)
        except Exception:
            pass
        c.setFont("Helvetica-Bold", 64)
        c.translate(larg / 2, alt / 2)
        c.rotate(45)
        c.drawCentredString(0, -22, marca)
        c.restoreState()

    c.setTitle(f"Solicitação de Abastecimento {serial} (2 vias)")
    c.showPage()
    c.save()
    return destino
