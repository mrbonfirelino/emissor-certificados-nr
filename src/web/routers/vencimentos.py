"""Vencimentos no portal (Fase 3) — leitura, mesmos filtros do desktop.

Certs + ASOs + Integrações com a mesma lógica de filtro do desktop
(src/core/filtros_vencimentos). Consulta e emissor veem; é read-only.
"""

from urllib.parse import urlencode

from fastapi import APIRouter, Request

from src.core.filtros_vencimentos import PERIOD_RANGES, filter_certs
from src.web.auth import require_permission

PER_PAGE = 20

STATUS_CLASSE = {
    "vencido": "b-vermelho",
    "urgente": "b-vermelho",
    "critico": "b-vermelho",
    "atencao": "b-amarelo",
    "proximo": "b-verde",
    "ok": "b-verde",
}

PERIODOS = [
    ("", "Todos"),
    ("vencidos", "Vencidos"),
    ("dias_7", "Próximos 7 dias"),
    ("dias_15", "Próximos 15 dias"),
    ("mes_1", "Próximos 30 dias"),
    ("meses_3", "Próximos 90 dias"),
]


def _carregar_items() -> list:
    """Mesma fonte do desktop: certificados + ASOs + integrações."""
    from src.core.history_repo import HistoryRepository

    itens = list(HistoryRepository().get_certificates_with_expiration())
    try:
        from src.core.aso_repo import AsoRepository
        itens += AsoRepository().get_asos_with_expiration()
    except Exception:
        pass
    try:
        from src.core.integracao_repo import IntegracaoRepository
        itens += IntegracaoRepository().get_integracoes_with_expiration()
    except Exception:
        pass
    return itens


def _br(iso: str) -> str:
    s = str(iso or "")
    if len(s) >= 10:
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def register(app, deps: dict):
    ctx, flash = deps["ctx"], deps["flash"]
    templates = deps["templates"]

    @app.get("/vencimentos")
    def vencimentos(request: Request, user: dict = require_permission("vencimentos"),
                    nr: str = "TODAS", periodo: str = "", busca: str = ""):
        itens = _carregar_items()
        nrs = sorted({c.get("nr_code", "") for c in itens if c.get("nr_code")})
        termo = (busca or "").strip().lower()
        filtrados = filter_certs(itens, nr or "TODAS", termo, periodo or "")

        filtrados.sort(key=lambda c: (c["dias_para_vencer"],
                                      str(c.get("funcionario_nome", "")).lower()))
        total = len(filtrados)
        try:
            page = max(1, int(request.query_params.get("page", "1")))
        except ValueError:
            page = 1
        total_paginas = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        page = min(page, total_paginas)
        fatia = filtrados[(page - 1) * PER_PAGE:page * PER_PAGE]

        linhas = [{
            "numero": c.get("cert_number", ""),
            "nr": c.get("nr_code", ""),
            "item": c.get("descricao_treinamento", ""),
            "funcionario": c.get("funcionario_nome", ""),
            "cpf": c.get("funcionario_cpf", ""),
            "validade": _br(c.get("data_validade")),
            "dias": c.get("dias_para_vencer"),
            "status": c.get("status", ""),
            "classe": STATUS_CLASSE.get(c.get("status", ""), "b-verde"),
        } for c in fatia]

        vencidos = sum(1 for c in filtrados if c["dias_para_vencer"] < 0)
        sete = sum(1 for c in filtrados if 0 <= c["dias_para_vencer"] <= 7)
        trinta = sum(1 for c in filtrados if 0 <= c["dias_para_vencer"] <= 30)

        filtros = {"nr": nr or "TODAS", "periodo": periodo or "",
                   "busca": (busca or "").strip()}
        qs = urlencode({k: v for k, v in filtros.items() if v and v != "TODAS"})

        return templates.TemplateResponse(
            request=request, name="vencimentos.html",
            context=ctx(request,
                        periodo_opcoes=PERIODOS, periodo_sel=periodo or "",
                        nrs=nrs, nr_sel=nr or "TODAS", busca=filtros["busca"],
                        linhas=linhas, page=page, total_paginas=total_paginas,
                        total=total, vencidos=vencidos, sete=sete, trinta=trinta,
                        qs=qs, qs_prefix=("&" + qs) if qs else ""))
