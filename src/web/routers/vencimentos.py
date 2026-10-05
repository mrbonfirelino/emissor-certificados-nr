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
    try:
        from src.core.frota_repo import FrotaRepository
        itens += FrotaRepository().get_laudos_with_expiration()
    except Exception:
        pass
    try:
        from src.core.frota_repo import FrotaRepository
        itens += FrotaRepository().get_manutencoes_with_expiration()
    except Exception:
        pass
    return itens


def _br(iso: str) -> str:
    s = str(iso or "")
    if len(s) >= 10:
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def _setor_do_item(c: dict) -> str:
    """Mapa item -> setor (notificacoes estruturadas por setor)."""
    nr = str(c.get("nr_code", ""))
    if nr == "FROTA":
        return "frota"
    if nr.startswith("INTEGRA"):
        return "outros"
    # treinamentos de segurança (NR-XX, ASO, PTA, CIPAA, brigadista etc.)
    return "seguranca"


def resumo_vencimentos() -> dict:
    """Contagens de vencimentos por status/categoria + itens mais urgentes."""
    itens = _carregar_items()
    hoje_status = {"vencido": 0, "urgente": 0, "critico": 0, "atencao": 0,
                   "proximo": 0, "ok": 0}
    por_setor = {}
    urgentes = []
    for c in itens:
        st = str(c.get("status", "ok"))
        hoje_status[st] = hoje_status.get(st, 0) + 1
        setor = _setor_do_item(c)
        por_setor.setdefault(setor, {"total": 0, "vencido": 0, "alerta": 0})
        por_setor[setor]["total"] += 1
        if st in ("vencido", "urgente", "critico"):
            por_setor[setor]["vencido" if st == "vencido" else "alerta"] += 1
        if c.get("dias_para_vencer", 999) <= 30:
            urgentes.append(c)
    urgentes.sort(key=lambda c: c.get("dias_para_vencer", 0))
    top = [{"numero": c.get("cert_number", ""),
            "nr": c.get("nr_code", ""),
            "item": c.get("descricao_treinamento", ""),
            "funcionario": c.get("funcionario_nome", ""),
            "status": str(c.get("status", "")),
            "classe": STATUS_CLASSE.get(str(c.get("status", "")), "b-verde"),
            "dias": c.get("dias_para_vencer", 0)} for c in urgentes[:10]]
    total = len(itens)
    alertas = hoje_status["vencido"] + hoje_status["urgente"] + hoje_status["critico"]
    return {"total": total, "status": hoje_status, "alertas": alertas,
            "por_setor": por_setor, "itens_urgentes": top}


def register(app, deps: dict):

    ctx, flash = deps["ctx"], deps["flash"]

    users = deps["users"]

    @app.get("/api/vencimentos/resumo")
    def api_vencimentos_resumo(user: dict = require_permission("vencimentos")):
        from fastapi.responses import JSONResponse
        resumo = resumo_vencimentos()
        try:
            u = users.get_by_id(user["id"]) or {}
        except Exception:
            u = {}
        resumo["notif"] = bool(u.get("pref_notif", 1))
        resumo["setor_usuario"] = u.get("setor", "") or ""
        return JSONResponse(resumo)
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

        linhas = []
        for c in fatia:
            if c.get("por_km"):
                validade, dias = "— (por KM)", f"{c['dias_para_vencer']} km"
            else:
                validade, dias = _br(c.get("data_validade")), \
                    c.get("dias_para_vencer")
            linhas.append({
                "numero": c.get("cert_number", ""),
                "nr": c.get("nr_code", ""),
                "item": c.get("descricao_treinamento", ""),
                "funcionario": c.get("funcionario_nome", ""),
                "cpf": c.get("funcionario_cpf", ""),
                "validade": validade,
                "dias": dias,
                "status": c.get("status", ""),
                "classe": STATUS_CLASSE.get(c.get("status", ""), "b-verde"),
            })

        vencidos = sum(1 for c in filtrados if c["dias_para_vencer"] < 0)
        sete = sum(1 for c in filtrados if 0 <= c["dias_para_vencer"] <= 7)
        quinze = sum(1 for c in filtrados if 8 <= c["dias_para_vencer"] <= 15)
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
                        pg_base=("/vencimentos?" + qs) if qs else "/vencimentos",
                        total=total, vencidos=vencidos, sete=sete,
                        quinze=quinze, trinta=trinta,
                        qs=qs, qs_prefix=("&" + qs) if qs else ""))
