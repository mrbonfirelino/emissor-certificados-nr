"""Portal Web — Integrações com fábricas de clientes (marcador de validade).

CRUD de integrações e empresas reaproveitando IntegracaoRepository; status
"Em dia/Vencida" pela mesma lógica de get_integracoes_with_expiration.
Módulo só para admin/emissor (matriz docs/PORTAL/01 §6).
"""

import re
from datetime import date
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse

from src.web import auth

PER_PAGE = 20

STATUS_CLASSE = {
    "vencido": "b-vermelho", "urgente": "b-vermelho", "critico": "b-vermelho",
    "atencao": "b-amarelo", "proximo": "b-verde", "ok": "b-verde",
}
STATUS_LABEL = {
    "vencido": "Vencida", "urgente": "Vence em 7 dias",
    "critico": "Vence em 15 dias", "atencao": "Vence em 30 dias",
    "proximo": "Em dia", "ok": "Em dia",
}


def _br(iso: str) -> str:
    s = str(iso or "")
    if len(s) >= 10:
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def register(app, deps: dict):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    def _repo():
        from src.core.integracao_repo import IntegracaoRepository
        return IntegracaoRepository()

    # ---------------- lista ----------------
    @app.get("/integracoes")
    def integracoes_lista(request: Request, q: str = "", page: int = 1,
                          user: dict = auth.require_permission("integracoes")):
        repo = _repo()
        itens = repo.get_integracoes_with_expiration(only_latest=False)
        termo = (q or "").strip().lower()
        if termo:
            itens = [i for i in itens if termo in (i.get("funcionario_nome") or "").lower()
                     or termo in (i.get("empresa_nome") or "").lower()
                     or termo in (i.get("tipo") or "").lower()]
        itens.sort(key=lambda i: (i.get("data_validade") or "", i.get("id") or 0))
        total = len(itens)
        paginas = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        page = min(max(1, page), paginas)
        fatia = itens[(page - 1) * PER_PAGE: page * PER_PAGE]
        linhas = [{"id": i["id"], "funcionario": i.get("funcionario_nome") or "—",
                   "empresa": i.get("empresa_nome") or "—",
                   "tipo": i.get("tipo") or "—",
                   "inicio": _br(i.get("data_inicio")),
                   "validade": _br(i.get("data_validade")),
                   "status": i.get("status") or "ok"} for i in fatia]
        base_url = f"/integracoes?q={quote(q)}&" if q else "/integracoes?"
        return templates.TemplateResponse(
            request=request, name="integracoes.html",
            context=ctx(request, linhas=linhas, total=total, q=q,
                        page=page, paginas=paginas, base_url=base_url,
                        status_classe=STATUS_CLASSE, status_label=STATUS_LABEL,
                        pode_escrever=auth.pode_escrever(user["papel"], "integracoes")))

    # ---------------- nova / editar integração ----------------
    def _dados_form(request: Request):
        from src.core.employee_repo import EmployeeRepository
        er = EmployeeRepository()
        funcionarios = sorted(er.get_all(limit=1000000), key=lambda e: e.nome.lower())
        empresas = sorted(_repo().list_empresas(), key=lambda x: x["nome"].lower())
        return funcionarios, empresas

    @app.get("/integracoes/novo")
    def integracao_nova(request: Request,
                        user: dict = auth.require_permission("integracoes")):
        if not auth.pode_escrever(user["papel"], "integracoes"):
            return templates.TemplateResponse(
                request=request, name="integracao_form.html",
                context=ctx(request, erro="Somente administrador ou emissor "
                                          "podem editar integrações."))
        funcionarios, empresas = _dados_form(request)
        padrao = date.today().replace(year=date.today().year + 1).isoformat()
        return templates.TemplateResponse(
            request=request, name="integracao_form.html",
            context=ctx(request, integ=None, funcionarios=funcionarios,
                        empresas=empresas, validade_padrao=padrao))

    @app.post("/integracoes/novo")
    async def integracao_criar(request: Request,
                               user: dict = auth.require_permission("integracoes")):
        if not auth.pode_escrever(user["papel"], "integracoes"):
            flash(request, erro="Somente administrador ou emissor podem editar integrações.")
            return RedirectResponse("/integracoes", status_code=303)
        form = await request.form()
        try:
            employee_id = int(form.get("employee_id") or 0)
            empresa_id = int(form.get("empresa_id") or 0)
            if employee_id <= 0:
                raise ValueError("Selecione o funcionário.")
            if empresa_id <= 0:
                raise ValueError("Selecione a empresa.")
            novo_id = _repo().add_integracao(
                employee_id, empresa_id, str(form.get("tipo") or ""),
                str(form.get("data_inicio") or ""),
                str(form.get("data_validade") or ""),
                str(form.get("obs") or ""))
            flash(request, msg=f"Integração #{novo_id} criada.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/integracoes", status_code=303)

    @app.get("/integracoes/{integracao_id}/editar")
    def integracao_editar(request: Request, integracao_id: int,
                          user: dict = auth.require_permission("integracoes")):
        if not auth.pode_escrever(user["papel"], "integracoes"):
            return templates.TemplateResponse(
                request=request, name="integracao_form.html",
                context=ctx(request, erro="Somente administrador ou emissor "
                                          "podem editar integrações."))
        integ = _repo().get_by_id(integracao_id)
        if integ is None:
            flash(request, erro="Integração não encontrada.")
            return RedirectResponse("/integracoes", status_code=303)
        funcionarios, empresas = _dados_form(request)
        return templates.TemplateResponse(
            request=request, name="integracao_form.html",
            context=ctx(request, integ=integ, funcionarios=funcionarios,
                        empresas=empresas, validade_padrao=""))

    @app.post("/integracoes/{integracao_id}/editar")
    async def integracao_salvar(request: Request, integracao_id: int,
                                user: dict = auth.require_permission("integracoes")):
        if not auth.pode_escrever(user["papel"], "integracoes"):
            flash(request, erro="Somente administrador ou emissor podem editar integrações.")
            return RedirectResponse("/integracoes", status_code=303)
        form = await request.form()
        try:
            employee_id = int(form.get("employee_id") or 0)
            empresa_id = int(form.get("empresa_id") or 0)
            if employee_id <= 0 or empresa_id <= 0:
                raise ValueError("Selecione funcionário e empresa.")
            _repo().update_integracao(
                integracao_id, employee_id=employee_id, empresa_id=empresa_id,
                tipo=str(form.get("tipo") or ""),
                data_inicio=str(form.get("data_inicio") or ""),
                data_validade=str(form.get("data_validade") or ""),
                obs=str(form.get("obs") or ""))
            flash(request, msg="Integração atualizada.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/integracoes", status_code=303)

    @app.post("/integracoes/{integracao_id}/excluir")
    async def integracao_excluir(request: Request, integracao_id: int,
                                 user: dict = auth.require_permission("integracoes")):
        if not auth.pode_escrever(user["papel"], "integracoes"):
            flash(request, erro="Somente administrador ou emissor podem excluir integrações.")
            return RedirectResponse("/integracoes", status_code=303)
        _repo().delete_integracao(integracao_id)
        flash(request, msg="Integração excluída.")
        return RedirectResponse("/integracoes", status_code=303)

    # ---------------- empresas clientes ----------------
    @app.get("/empresas")
    def empresas_lista(request: Request,
                       user: dict = auth.require_permission("integracoes")):
        repo = _repo()
        linhas = []
        for e in sorted(repo.list_empresas(), key=lambda x: x["nome"].lower()):
            qtd = repo.count_integracoes_empresa(e["id"])
            linhas.append({**e, "integracoes": qtd})
        return templates.TemplateResponse(
            request=request, name="empresas.html",
            context=ctx(request, linhas=linhas,
                        pode_escrever=auth.pode_escrever(user["papel"], "integracoes")))

    @app.post("/empresas/criar")
    async def empresa_criar(request: Request,
                            user: dict = auth.require_permission("integracoes")):
        if not auth.pode_escrever(user["papel"], "integracoes"):
            flash(request, erro="Somente administrador ou emissor podem gerenciar empresas.")
            return RedirectResponse("/empresas", status_code=303)
        form = await request.form()
        nome = str(form.get("nome") or "").strip()
        cnpj = str(form.get("cnpj") or "").strip()
        if not nome:
            flash(request, erro="Informe o nome da empresa.")
            return RedirectResponse("/empresas", status_code=303)
        digitos = re.sub(r"\D", "", cnpj)
        if digitos and (len(digitos) != 14 or digitos == digitos[0] * 14):
            flash(request, erro="CNPJ inválido: informe os 14 dígitos (ou deixe vazio).")
            return RedirectResponse("/empresas", status_code=303)
        try:
            if _repo().get_empresa_por_nome(nome):
                raise ValueError(f"Empresa '{nome}' já existe.")
            _repo().add_empresa(nome, cnpj)
            flash(request, msg=f"Empresa '{nome}' criada.")
        except ValueError as e:
            flash(request, erro=str(e))
        return RedirectResponse("/empresas", status_code=303)

    @app.post("/empresas/{empresa_id}/renomear")
    async def empresa_renomear(request: Request, empresa_id: int,
                               user: dict = auth.require_permission("integracoes")):
        if not auth.pode_escrever(user["papel"], "integracoes"):
            flash(request, erro="Somente administrador ou emissor podem gerenciar empresas.")
            return RedirectResponse("/empresas", status_code=303)
        form = await request.form()
        nome = str(form.get("nome") or "").strip()
        cnpj = str(form.get("cnpj") or "").strip()
        if not nome:
            flash(request, erro="Informe o nome da empresa.")
            return RedirectResponse("/empresas", status_code=303)
        digitos = re.sub(r"\D", "", cnpj)
        if digitos and (len(digitos) != 14 or digitos == digitos[0] * 14):
            flash(request, erro="CNPJ inválido: informe os 14 dígitos (ou deixe vazio).")
            return RedirectResponse("/empresas", status_code=303)
        atual = _repo().get_empresa(empresa_id)
        if atual is None:
            flash(request, erro="Empresa não encontrada.")
            return RedirectResponse("/empresas", status_code=303)
        existente = _repo().get_empresa_por_nome(nome)
        if existente and existente["id"] != empresa_id:
            flash(request, erro=f"Já existe uma empresa chamada '{nome}'.")
            return RedirectResponse("/empresas", status_code=303)
        _repo().update_empresa(empresa_id, nome, cnpj)
        flash(request, msg="Empresa atualizada.")
        return RedirectResponse("/empresas", status_code=303)

    @app.post("/empresas/{empresa_id}/excluir")
    async def empresa_excluir(request: Request, empresa_id: int,
                              user: dict = auth.require_permission("integracoes")):
        if not auth.pode_escrever(user["papel"], "integracoes"):
            flash(request, erro="Somente administrador ou emissor podem gerenciar empresas.")
            return RedirectResponse("/empresas", status_code=303)
        repo = _repo()
        empresa = repo.get_empresa(empresa_id)
        if empresa is None:
            flash(request, erro="Empresa não encontrada.")
            return RedirectResponse("/empresas", status_code=303)
        if repo.count_integracoes_empresa(empresa_id) > 0:
            flash(request, erro=f"'{empresa['nome']}' tem integrações vinculadas — "
                                "exclua-as antes de remover a empresa.")
            return RedirectResponse("/empresas", status_code=303)
        repo.delete_empresa(empresa_id)
        flash(request, msg="Empresa excluída.")
        return RedirectResponse("/empresas", status_code=303)
