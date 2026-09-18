"""Portal Web — Auditoria (admin).

Consulta do audit_log (login, emissões, exclusões, imports, config)
com busca, filtro por data, linhas por página e paginação (2.30.2).
"""

from urllib.parse import quote_plus

from fastapi import APIRouter, Request

from src.web import auth

_PER_OPCOES = (10, 20, 30, 50)


def register(app, deps):
    templates = deps["templates"]
    ctx = deps["ctx"]

    @app.get("/auditoria")
    def auditoria_lista(request: Request,
                        busca: str = "",
                        data_de: str = "",
                        data_ate: str = "",
                        per: int = 20,
                        page: int = 1,
                        user: dict = auth.require_permission("auditoria")):
        users = deps["users"]
        q = (busca or "").strip()
        de = (data_de or "").strip()
        ate = (data_ate or "").strip()
        per = per if per in _PER_OPCOES else 20
        rows, total = users.audit_page(q, limit=per,
                                       offset=(max(1, page) - 1) * per,
                                       data_de=de or None,
                                       data_ate=ate or None)
        itens = [{
            "id": r["id"],
            "quando": (r["created_at"] or "").replace("T", " ")[:16],
            "username": r["username"],
            "acao": r["acao"],
            "alvo": r["alvo"],
            "detalhe": r["detalhe"],
        } for r in rows]
        paginas = max(1, (total + per - 1) // per)
        page = max(1, min(page, paginas))
        from urllib.parse import parse_qsl
        params = [("busca", q)] if q else []
        params += [("data_de", de)] if de else []
        params += [("data_ate", ate)] if ate else []
        params += [("per", str(per))] if per != 20 else []
        pg_base = "/auditoria" + ("?" + "&".join(
            f"{k}={quote_plus(v)}" for k, v in params) if params else "")
        return templates.TemplateResponse(
            request, "auditoria.html",
            ctx(request, itens=itens, total=total, q=q, de=de, ate=ate,
                per=per, per_opcoes=_PER_OPCOES,
                page=page, paginas=paginas, pg_base=pg_base))
