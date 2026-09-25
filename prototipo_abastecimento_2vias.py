"""PROTÓTIPO (roadmap 2.40.4) — NÃO integrado ao sistema.

Gera um PDF de Solicitação de Abastecimento com 2 CÓPIAS na mesma folha
A4 (cópias lado a lado, na horizontal), para avaliação do formato que
permitirá 1 via para o sistema e 1 via física para quem emite.

Uso:  python prototipo_abastecimento_2vias.py
Saída: prototipo_abastecimento_2vias.pdf na raiz do projeto
       (o caminho completo é impresso no console).
Dados de exemplo embutidos (valores e itens extras fictícios).
"""

import random
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

try:
    from src.utils.paths import get_logo_path
except Exception:
    def get_logo_path():
        return None

AZUL = HexColor("#1F4E79")
CINZA = HexColor("#595959")
BORDA = HexColor("#8FA8C8")
FUNDO = HexColor("#EEF3F9")
VERMELHO = HexColor("#C0392B")


def _copia(c: canvas.Canvas, x0: float, y0: float, larg: float, alt: float,
           dados: dict):
    """Desenha UMA cópia da solicitação dentro do retângulo (x0, y0)."""
    mg = 8 * mm
    w = larg - 2 * mg
    y = y0 + alt - mg

    # moldura da cópia
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
    c.setFillColor(AZUL)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(x0 + larg - mg, y - 5 * mm, dados["empresa"])
    c.setFillColor(CINZA)
    c.setFont("Helvetica", 6.5)
    c.drawRightString(x0 + larg - mg, y - 9 * mm, f"CNPJ: {dados['cnpj']}")
    y -= lh + 3 * mm

    # título
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

    # tabela de dados
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
        c.setFillColor(HexColor("#22303F"))
        c.setFont("Helvetica", 7.5)
        c.drawString(x0 + mg + 36 * mm, y - hh + 2 * mm, valor)
        y -= hh

    for rot, val in dados["pares"]:
        _linha(rot, val)

    # itens extras
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
    c.setFillColor(HexColor("#22303F"))
    for desc, qtde in dados["extras"]:
        c.rect(x0 + mg, y - 6 * mm, w, 6 * mm, stroke=1, fill=0)
        c.rect(x0 + mg + col1, y - 6 * mm, col2, 6 * mm, stroke=1, fill=0)
        c.drawString(x0 + mg + 2 * mm, y - 4.2 * mm, desc)
        c.drawCentredString(x0 + mg + col1 + col2 / 2, y - 4.2 * mm, qtde)
        y -= 6 * mm

    # observações
    if dados.get("obs"):
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
        c.setFillColor(HexColor("#22303F"))
        c.setFont("Helvetica", 6.5)
        c.drawString(x0 + mg + 2 * mm, y - 3.4 * mm, dados["obs"][:70])
        y -= hh

    # assinaturas
    y -= 11 * mm
    metade = w / 2
    for cx, rotulo, nome in (
            (x0 + mg + metade / 2, "Condutor", dados["condutor"]),
            (x0 + mg + metade * 1.5, "Aprovação do Superior", "Aprovado")):
        c.setStrokeColor(HexColor("#22303F"))
        c.setLineWidth(0.6)
        c.line(cx - 24 * mm, y, cx + 24 * mm, y)
        c.setFillColor(HexColor("#22303F"))
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(cx, y - 4 * mm, nome)
        c.setFillColor(CINZA)
        c.setFont("Helvetica", 6)
        c.drawCentredString(cx, y - 7 * mm, rotulo)

    # marca discreta de via (só no protótipo)
    c.setFillColor(VERMELHO)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x0 + mg, y0 + 3 * mm, dados["via"])


def main():
    random.seed(240)
    caminho = Path(__file__).resolve().parent / \
        "prototipo_abastecimento_2vias.pdf"

    dados_base = {
        "empresa": "ALTEC ENGENHARIA LTDA",
        "cnpj": "12.345.678/0001-99",
        "serial": "AB-2026-00042",
        "condutor": "JOÃO R. DA SILVA",
        "obs": "Abastecimento em viagem — obra Rodovia BR-101 km 220.",
        "extras": [
            ("Óleo 15W40 (litro)", f"{random.randint(2, 6)}"),
            ("Pedágio", f"{random.randint(1, 4)}"),
            ("Arla 32 (litro)", f"{random.randint(5, 15)}"),
        ],
        "pares": [
            ("Serial", "AB-2026-00042"),
            ("Data da solicitação", "24/09/2026"),
            ("Veículo", "Fiat Strada — ABC1D23 — Próprio"),
            ("Combustível", "Diesel"),
            ("KM do veículo", "210.884"),
            ("Viagem / Serviço", "Viagem — Obra BR-101"),
            ("Fornecedor (posto)", "Posto KM 220 · CNPJ 98.765.432/0001-55"),
            ("Condutor", "JOÃO R. DA SILVA"),
        ],
    }

    c = canvas.Canvas(str(caminho), pagesize=landscape(A4))
    larg, alt = landscape(A4)
    meia = larg / 2
    for i in (1, 2):
        d = dict(dados_base)
        d["via"] = f"PROTÓTIPO 2.40.4 — VIA {i} DE 2 (NÃO OFICIAL)"
        _copia(c, (i - 1) * meia, 0, meia, alt, d)
        if i == 1:
            c.setStrokeColor(BORDA)
            c.setLineWidth(0.6)
            c.line(meia, 6 * mm, meia, alt - 6 * mm)
    c.setTitle("Protótipo — Solicitação de Abastecimento 2 vias (2.40.4)")
    c.showPage()
    c.save()
    print(f"PROTOTIPO GERADO EM: {caminho}")


if __name__ == "__main__":
    main()
