"""Relatório de custos de frota em PDF (2.37.2) — para diretoria.

Modo 'todos': página de resumo (gráfico geral dos últimos 12 meses empilhado
por veículo + tabela por veículo com desglose combustível/extras) e uma
página POR VEÍCULO (dados essenciais com foto pequena, gráfico individual e
tabela por tipo de combustível). Modo 'individual' (veiculo_id informado)
gera somente a página do veículo.

Desenhado em ReportLab canvas puro (offline, sem dependências novas), no
padrão visual ALTEC dos demais PDFs. Nenhuma faixa sobrepõe textos (lição
2.34.3): gap dedicado entre faixa azul e conteúdo.
"""

from datetime import date, datetime
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

from src.core.frota_repo import (
    FrotaRepository, label_combustivel, label_subtipo, label_tipo,
    veiculo_rotulo,
)

PAGE_W, PAGE_H = landscape(A4)
MARGEM = 14 * mm

PRIMARY = HexColor("#1B3A5C")
AZUL2 = HexColor("#2E6DA4")
BORDA = HexColor("#D6DEE8")
FUNDO = HexColor("#F2F5F9")
TEXTO = HexColor("#22303F")
MUTED = HexColor("#67737F")
VERDE = HexColor("#256B28")
AMARELO = HexColor("#E6A23C")

_PALETTE = ("#2E6DA4", "#E6A23C", "#256B28", "#B03A5B", "#6A5ACD",
            "#00838F", "#8D6E63", "#546E7A", "#C0CA33", "#AD1457",
            "#00897B", "#7B1FA2")


def _cor(i: int) -> HexColor:
    return HexColor(_PALETTE[i % len(_PALETTE)])


def _num(v) -> str:
    try:
        return f"{float(v):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "0,00"


def _brl(v) -> str:
    return "R$ " + _num(v)


def _posse(v: dict) -> str:
    if v.get("proprio"):
        return "Próprio"
    return f"Alugado — {v.get('contratante') or '?'}"


def _cfg_empresa():
    try:
        from src.core.config import load_company_config
        return load_company_config()
    except Exception:
        return None


def _logo_path():
    try:
        from src.utils.paths import get_logo_path
        return get_logo_path()
    except Exception:
        return None


def _serie_totais(serie: list) -> dict:
    """Agrega {vid: {rotulo, comb, ext, litros}} de uma série por veículo."""
    tot = {}
    for s in serie:
        for vid, d in (s.get("por_veiculo") or {}).items():
            t = tot.setdefault(vid, {"rotulo": d["rotulo"], "comb": 0.0,
                                     "ext": 0.0, "litros": 0.0})
            t["comb"] += d["combustivel"]
            t["ext"] += d["extras"]
            t["litros"] += d["litros"]
    for t in tot.values():
        t["comb"] = round(t["comb"], 2)
        t["ext"] = round(t["ext"], 2)
        t["litros"] = round(t["litros"], 2)
    return tot


def _cabecalho(c: rl_canvas.Canvas, cfg) -> float:
    """Logo + empresa no topo; devolve o Y onde o conteúdo pode começar."""
    y_topo = PAGE_H - MARGEM
    logo = _logo_path()
    x_texto = MARGEM
    if logo:
        try:
            c.drawImage(str(logo), MARGEM, y_topo - 16 * mm,
                        width=30 * mm, height=16 * mm,
                        preserveAspectRatio=True, anchor="sw", mask="auto")
            x_texto = MARGEM + 34 * mm
        except Exception:
            pass
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 11)
    if cfg:
        c.drawString(x_texto, y_topo - 5 * mm, getattr(cfg, "empresa_nome", ""))
        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        cnc = getattr(cfg, "empresa_cnpj", "")
        local = getattr(cfg, "local_treinamento", "")
        linha = " · ".join(p for p in (f"CNPJ {cnc}" if cnc else "", local) if p)
        c.drawString(x_texto, y_topo - 9.5 * mm, linha)
    c.setStrokeColor(BORDA)
    c.setLineWidth(1)
    c.line(MARGEM, y_topo - 13 * mm, PAGE_W - MARGEM, y_topo - 13 * mm)
    return y_topo - 13 * mm


def _rodape(c: rl_canvas.Canvas):
    c.setFont("Helvetica", 7)
    c.setFillColor(MUTED)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.drawString(MARGEM, 8 * mm, f"NormaTech — gerado em {agora}")
    c.drawRightString(PAGE_W - MARGEM, 8 * mm,
                      f"Página {c.getPageNumber()}")


def _titulo(c: rl_canvas.Canvas, y: float, titulo: str, sub: str = "") -> float:
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(MARGEM, y - 8 * mm, titulo)
    yy = y - 8 * mm
    if sub:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8.5)
        c.drawString(MARGEM, yy - 5 * mm, sub)
        yy -= 5 * mm
    return yy - 4 * mm


def _desenha_grafico(c: rl_canvas.Canvas, x0: float, y_base: float, larg: float,
                     alt: float, rotulos: list, pilhas: list, maxv: float,
                     litros=None):
    """Barras empilhadas por mês (`pilhas[i]` = [(valor, cor), ...]) com eixo,
    rótulos e linha opcional de litros (escala própria)."""
    c.setStrokeColor(BORDA)
    c.setLineWidth(0.8)
    c.line(x0, y_base, x0 + larg, y_base)
    n = max(len(rotulos), 1)
    passo = larg / n
    bw = min(30.0, passo * 0.62)
    for i, (rot, pilha) in enumerate(zip(rotulos, pilhas)):
        acum = 0.0
        for val, cor in pilha:
            if val > 0:
                hh = val / maxv * alt
                c.setFillColor(cor)
                c.rect(x0 + i * passo + (passo - bw) / 2, y_base + acum,
                       bw, hh, stroke=0, fill=1)
                acum += hh
        c.setFillColor(HexColor("#5A6B7C"))
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(x0 + i * passo + passo / 2, y_base - 9, rot)
    c.setFillColor(HexColor("#5A6B7C"))
    c.setFont("Helvetica", 6.5)
    c.drawRightString(x0 - 4, y_base + alt - 2, _brl(maxv))
    c.drawRightString(x0 - 4, y_base - 2, "R$ 0")
    if litros:
        maxl = max(max(litros), 0.01)
        prev = None
        c.setStrokeColor(VERDE)
        c.setLineWidth(1.4)
        for i in range(n):
            xc = x0 + i * passo + passo / 2
            yv = y_base + (litros[i] / maxl) * alt
            if prev:
                c.line(prev[0], prev[1], xc, yv)
            prev = (xc, yv)
        c.setFillColor(VERDE)
        for i in range(n):
            xc = x0 + i * passo + passo / 2
            c.circle(xc, y_base + (litros[i] / maxl) * alt, 1.8, stroke=0, fill=1)


def _legenda(c: rl_canvas.Canvas, y: float, itens: list):
    """itens = [(cor, rótulo), ...] em linha única."""
    x = MARGEM
    c.setFont("Helvetica", 7.5)
    for cor, rot in itens:
        c.setFillColor(cor)
        c.rect(x, y - 2.2, 8, 8, stroke=0, fill=1)
        c.setFillColor(TEXTO)
        c.drawString(x + 11, y, rot)
        x += 11 + c.stringWidth(rot, "Helvetica", 7.5) + 14


def _tabela(c: rl_canvas.Canvas, y: float, larguras: list, headers: list,
            linhas: list, alinh=None) -> float:
    """Tabela com cabeçalho azul e zebra; devolve o Y final.
    `alinh` = lista 'E'/'D' por coluna (padrão E)."""
    if alinh is None:
        alinh = ["E"] * len(larguras)
    x0 = MARGEM
    total_w = sum(larguras)
    # cabeçalho
    c.setFillColor(PRIMARY)
    c.rect(x0, y - 7 * mm, total_w, 7 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 8)
    x = x0
    for w, h, a in zip(larguras, headers, alinh):
        if a == "D":
            c.drawRightString(x + w - 3 * mm, y - 4.8 * mm, h)
        else:
            c.drawString(x + 3 * mm, y - 4.8 * mm, h)
        x += w
    y -= 7 * mm
    # linhas
    c.setFont("Helvetica", 8)
    for i, linha in enumerate(linhas):
        if i % 2 == 1:
            c.setFillColor(FUNDO)
            c.rect(x0, y - 6 * mm, total_w, 6 * mm, stroke=0, fill=1)
        c.setFillColor(TEXTO)
        x = x0
        for w, val, a in zip(larguras, linha, alinh):
            if a == "D":
                c.drawRightString(x + w - 3 * mm, y - 4.2 * mm, str(val))
            else:
                c.drawString(x + 3 * mm, y - 4.2 * mm, str(val))
            x += w
        y -= 6 * mm
    c.setStrokeColor(BORDA)
    c.setLineWidth(0.8)
    c.rect(x0, y, total_w, (len(linhas) + 1) * 6 * mm + 1 * mm, stroke=1, fill=0)
    return y


def _pagina_resumo(c: rl_canvas.Canvas, repo: FrotaRepository, serie: list,
                   tot12: dict):
    cfg = _cfg_empresa()
    y = _cabecalho(c, cfg)
    mes_ini, mes_fim = serie[0]["rotulo"], serie[-1]["rotulo"]
    y = _titulo(c, y, "RELATÓRIO DE CUSTOS — FROTA",
                f"Período do gráfico: {mes_ini} a {mes_fim} (últimos 12 meses)"
                " · solicitações bloqueadas ficam fora dos totais")

    # gráfico geral empilhado por veículo
    vid_order, rotulos_v = [], {}
    for s in serie:
        for vid, d in (s.get("por_veiculo") or {}).items():
            if vid not in rotulos_v:
                vid_order.append(vid)
                rotulos_v[vid] = d["rotulo"]
    maxv = 0.01
    pilhas, rotulos, litros = [], [], []
    for s in serie:
        pilha, tot = [], 0.0
        for vid in vid_order:
            d = (s.get("por_veiculo") or {}).get(vid)
            if d:
                v = d["combustivel"] + d["extras"]
                if v > 0:
                    pilha.append((v, _cor(vid_order.index(vid))))
                    tot += v
        pilhas.append(pilha)
        rotulos.append(s["rotulo"])
        litros.append(sum(d["litros"] for d in
                          (s.get("por_veiculo") or {}).values()))
        maxv = max(maxv, tot)
    alt_g = 52 * mm
    _desenha_grafico(c, MARGEM + 14 * mm, y - alt_g,
                     PAGE_W - 2 * MARGEM - 14 * mm, alt_g,
                     rotulos, pilhas, maxv, litros=litros)
    y = y - alt_g - 12 * mm
    _legenda(c, y, [( _cor(i), rotulos_v[vid]) for i, vid in enumerate(vid_order)])
    y -= 12 * mm

    # tabela por veículo (12 meses)
    linhas = []
    tot_comb = tot_ext = tot_lit = 0.0
    for vid in vid_order:
        t = tot12.get(vid)
        if not t:
            continue
        tot_comb += t["comb"]
        tot_ext += t["ext"]
        tot_lit += t["litros"]
        linhas.append([t["rotulo"], f"{_num(t['litros'])} L",
                       _brl(t["comb"]), _brl(t["ext"]),
                       _brl(t["comb"] + t["ext"])])
    if linhas:
        linhas.append(["TOTAL", f"{_num(tot_lit)} L", _brl(tot_comb),
                       _brl(tot_ext), _brl(tot_comb + tot_ext)])
        _tabela(c, y, [92 * mm, 38 * mm, 44 * mm, 44 * mm, 46 * mm],
                ["Veículo", "Litros", "Combustível", "Itens extras", "Total"],
                linhas, alinh=["E", "D", "D", "D", "D"])


def _pagina_veiculo(c: rl_canvas.Canvas, repo: FrotaRepository, v: dict,
                    serie_v: list, comb_linhas: list):
    cfg = _cfg_empresa()
    y = _cabecalho(c, cfg)

    # foto pequena no canto direito
    foto = None
    try:
        foto = repo.get_foto(v["id"])
    except Exception:
        foto = None
    if foto and foto.get("dados"):
        try:
            c.drawImage(ImageReader(BytesIO(foto["dados"])),
                        PAGE_W - MARGEM - 32 * mm, PAGE_H - MARGEM - 24 * mm,
                        width=32 * mm, height=24 * mm,
                        preserveAspectRatio=True, anchor="ne", mask="auto")
        except Exception:
            pass

    rotulo = veiculo_rotulo(v)
    detalhe = " · ".join(p for p in (
        f"Placa {v.get('placa')}" if v.get("placa") else "",
        label_tipo(v.get("tipo", "")),
        label_subtipo(v.get("subtipo", "")) if v.get("subtipo") else "",
        _posse(v),
        v.get("empresa_nome") or "") if p)
    y = _titulo(c, y, f"RELATÓRIO DE CUSTOS — {rotulo}", detalhe)

    mes_ini, mes_fim = serie_v[0]["rotulo"], serie_v[-1]["rotulo"]
    comb12 = sum(s["combustivel"] for s in serie_v)
    ext12 = sum(s["extras"] for s in serie_v)
    lit12 = sum(s["litros"] for s in serie_v)

    c.setFillColor(TEXTO)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(MARGEM, y - 4 * mm, f"Últimos 12 meses ({mes_ini} a {mes_fim}):")
    c.setFont("Helvetica", 9)
    c.drawString(MARGEM + 62 * mm, y - 4 * mm,
                 f"Combustível {_brl(comb12)}  ·  Itens extras {_brl(ext12)}"
                 f"  ·  Total {_brl(comb12 + ext12)}"
                 f"  ·  Litros {_num(lit12)}")
    y -= 10 * mm

    # mini gráfico individual
    maxv = max(max(s["combustivel"] + s["extras"] for s in serie_v), 0.01)
    pilhas = [[(s["combustivel"], AZUL2), (s["extras"], AMARELO)]
              for s in serie_v]
    rotulos = [s["rotulo"] for s in serie_v]
    litros = [s["litros"] for s in serie_v]
    alt_g = 46 * mm
    _desenha_grafico(c, MARGEM + 14 * mm, y - alt_g,
                     PAGE_W - 2 * MARGEM - 14 * mm, alt_g,
                     rotulos, pilhas, maxv, litros=litros)
    y = y - alt_g - 11 * mm
    _legenda(c, y, [(AZUL2, "Combustível"), (AMARELO, "Itens extras"),
                    (VERDE, "Litros (linha)")])
    y -= 12 * mm

    # tabela por tipo de combustível (histórico ativo)
    if comb_linhas:
        linhas = []
        t_comb = t_ext = t_lit = 0.0
        for it in comb_linhas:
            t_comb += it["combustivel"]
            t_ext += it["extras"]
            t_lit += it["litros"]
            linhas.append([label_combustivel(it["comb"]),
                           f"{_num(it['litros'])} L",
                           _brl(it["combustivel"]), _brl(it["extras"]),
                           _brl(it["combustivel"] + it["extras"])])
        linhas.append(["TOTAL", f"{_num(t_lit)} L", _brl(t_comb),
                       _brl(t_ext), _brl(t_comb + t_ext)])
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGEM, y - 4 * mm, "Por tipo de combustível (histórico ativo)")
        y -= 6 * mm
        _tabela(c, y, [74 * mm, 38 * mm, 48 * mm, 48 * mm, 48 * mm],
                ["Combustível", "Litros", "Valor", "Itens extras", "Total"],
                linhas, alinh=["E", "D", "D", "D", "D"])
        y -= (len(linhas) + 1) * 6 * mm + 2 * mm

    # indicadores (histórico ativo)
    try:
        resumo = repo.resumo_custo_veiculo(v["id"])
    except Exception:
        resumo = {}
    ind = []
    if resumo.get("media_km_l"):
        ind.append(f"Média: {_num(resumo['media_km_l'])} KM/L")
    if resumo.get("custo_km"):
        ind.append(f"Custo por km: {_brl(resumo['custo_km'])}")
    if resumo.get("km_l_esperado"):
        ind.append(f"KM/L esperado: {_num(resumo['km_l_esperado'])}")
    if ind:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(MARGEM, y - 4 * mm, " · ".join(ind) + " (histórico ativo)")


def gerar_pdf_custos_frota(veiculo_id=None, repo: FrotaRepository = None) -> bytes:
    """Gera o RELATÓRIO DE CUSTOS — FROTA e devolve os bytes do PDF.
    veiculo_id=None → resumo geral + 1 página por veículo (com dados).
    veiculo_id informado → somente a página desse veículo."""
    repo = repo or FrotaRepository()
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setTitle("Relatório de Custos — Frota")

    if veiculo_id is None:
        serie = repo.custo_serie_todos()
        tot12 = _serie_totais(serie)
        _pagina_resumo(c, repo, serie, tot12)
        _rodape(c)
        c.showPage()
        for vid in sorted(tot12.keys()):
            v = repo.get_veiculo(vid)
            if not v:
                continue
            comb_linhas = [it for it in repo.custo_por_combustivel()
                           if it["vid"] == vid]
            _pagina_veiculo(c, repo, v, repo.custo_serie_veiculo(vid),
                            comb_linhas)
            _rodape(c)
            c.showPage()
    else:
        v = repo.get_veiculo(veiculo_id)
        if not v:
            raise ValueError("Veículo não encontrado.")
        comb_linhas = [it for it in repo.custo_por_combustivel()
                       if it["vid"] == veiculo_id]
        _pagina_veiculo(c, repo, v, repo.custo_serie_veiculo(veiculo_id),
                        comb_linhas)
        _rodape(c)
        c.showPage()

    c.save()
    return buf.getvalue()
