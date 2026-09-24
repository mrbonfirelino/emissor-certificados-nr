"""Portal Web NormaTech — fabrica do app FastAPI (Fase 1).

Rotas: login/logout, dashboard (leitura), usuarios (admin), troca de senha
obrigatoria. Reaproveita src/core/ e o MESMO certificados.db.

Execucao: python run_web.py [--host 0.0.0.0] [--port 8000]
"""

import secrets
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from src.core.version import APP_VERSION
from src.utils.paths import get_data_dir
from src.web import auth, jobs
from src.web.permissions import ROLE_LABELS, pode, pode_escrever, pode_usuario
from src.web.permissions import MODULOS_UI as _MODULOS_PERM_UI
from src.web.users_repo import ROLES, UsersRepository

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _carregar_ou_criar_secret(arquivo: Path) -> str:
    try:
        if arquivo.exists():
            segredo = arquivo.read_text(encoding="utf-8").strip()
            if segredo:
                return segredo
        segredo = secrets.token_hex(32)
        arquivo.write_text(segredo, encoding="utf-8")
        return segredo
    except Exception:
        return secrets.token_hex(32)


def _anunciar_senha_provisoria(senha: str) -> None:
    """Senha provisoria do 1o boot: console + arquivo (NSSM nao tem console)."""
    print("=" * 56)
    print("USUARIO ADMIN CRIADO (1o boot do portal)")
    print(f"  login: admin    senha provisoria: {senha}")
    print("Troque a senha no primeiro acesso.")
    print("=" * 56)
    try:
        alvo = get_data_dir() / "web_admin_provisorio.txt"
        alvo.write_text(
            "LOGIN: admin\n"
            f"SENHA PROVISORIA: {senha}\n\n"
            "Troque a senha no primeiro acesso ao portal.\n"
            "APAGUE ESTE ARQUIVO depois de anotar a senha.\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def create_app(db_path=None, secret_file: Path = None) -> FastAPI:
    app = FastAPI(title="NormaTech Portal", docs_url=None, redoc_url=None, openapi_url=None)
    segredo = _carregar_ou_criar_secret(secret_file or (get_data_dir() / "web_secret.key"))
    app.add_middleware(SessionMiddleware, secret_key=segredo, max_age=12 * 3600, same_site="lax")

    users = UsersRepository(db_path=db_path)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    senha_bootstrap = users.bootstrap_admin()
    if senha_bootstrap:
        _anunciar_senha_provisoria(senha_bootstrap)

    # Módulos implementados no portal; a matriz de permissões
    # (permissions.pode) filtra o que cada papel vê. Nav organizada em
    # grupos (2.30.1): titulo=None vira link direto no topo da barra.
    _GRUPOS_NAV = [
        (None, [("Dashboard", "/", "dashboard")]),
        ("__botao__", [("Gest\u00e3o de Frota", "/frota", "frota")]),
        ("Seguran\u00e7a", [
            ("Certificados", "/certificados", "certificados"),
            ("Emiss\u00e3o em Lote", "/emissao-lote", "certificados"),
            ("Hist\u00f3rico", "/historico", "historico"),
            ("Listas de Presen\u00e7a", "/presencas", "presencas"),
            ("Ficha de EPIs", "/epi", "epi"),
            ("Crach\u00e1s", "/crachas", "crachas"),
            ("Cart\u00f5es", "/cartoes", "cartoes"),
            ("Vencimentos", "/vencimentos", "vencimentos"),
        ]),
        ("Funcion\u00e1rios", [
            ("Cadastros", "/funcionarios", "funcionarios"),
            ("ASO", "/aso", "aso"),
            ("Integra\u00e7\u00f5es", "/integracoes", "integracoes"),
        ]),
        ("Controle", [
            ("Importa\u00e7\u00f5es", "/importacoes", "importacoes"),
        ]),
    ]

    def _nav(user: dict, caminho: str = "") -> list:
        def item(label, url, ativo):
            return {"label": label, "url": url, "ativo": ativo}

        grupos = []
        for titulo, modulos in _GRUPOS_NAV:
            itens = []
            for label, url, modulo in modulos:
                if url == "/emissao-lote":
                    # lote é operação: exceção de acesso não basta, exige papel
                    # com escrita (admin/emissor)
                    if not (pode_usuario(user, modulo)
                            and pode_escrever(user["papel"], "certificados")):
                        continue
                elif not pode_usuario(user, modulo):
                    continue  # 2.33.4: papel + exceção por usuário
                ativo = (caminho == url) if url == "/" else caminho.startswith(url)
                itens.append(item(label, url, ativo))
            if itens:
                grupos.append({"titulo": titulo, "itens": itens})
        sistema = []
        for label, url, modulo in (("Usuários", "/usuarios", "usuarios"),
                                   ("Backup", "/backup", "backup"),
                                   ("Auditoria", "/auditoria", "auditoria"),
                                   ("Configurações", "/configuracoes", "config")):
            if pode_usuario(user, modulo):
                sistema.append(item(label, url, caminho.startswith(url)))
        if sistema:
            grupos.append({"titulo": "Sistema", "itens": sistema})
        return grupos

    def _milhar(v):
        """Ponto de milhar para KMs (100000 -> 100.000)."""
        try:
            return "{:,.0f}".format(float(v)).replace(",", ".")
        except (TypeError, ValueError):
            return v

    templates.env.filters["milhar"] = _milhar
    templates.env.globals["milhar"] = _milhar

    def _dec(v, casas: int = 2):
        """Número com vírgula decimal e milhar (2.37.3/2.38.1):
        1720.52 -> '1.720,52'; vazio -> '—'."""
        if v in (None, ""):
            return "—"
        try:
            txt = f"{float(v):.{casas}f}"
            inteiro, _, frac = txt.partition(".")
            return _milhar(inteiro) + ("," + frac if frac else "")
        except (TypeError, ValueError):
            return v

    templates.env.filters["dec"] = _dec

    def _brl(v):
        """Moeda com vírgula e milhar (2.37.3/2.38.1): 409.5 -> 'R$ 409,50';
        1720.52 -> 'R$ 1.720,52'; vazio -> '—'."""
        if v in (None, ""):
            return "—"
        try:
            return "R$ " + _dec(v)
        except (TypeError, ValueError):
            return v

    templates.env.filters["brl"] = _brl
    templates.env.globals["dec"] = _dec
    templates.env.globals["brl"] = _brl

    def _ctx(request: Request, **extra) -> dict:
        user = auth.current_user(request)
        sessao = request.session.pop("flash", None) or {}
        ctx = {"request": request, "user": user,
               "nav": _nav(user, request.url.path) if user else [],
               "papel_label": ROLE_LABELS.get(user["papel"], user["papel"]) if user else "",
               "versao": APP_VERSION,
               "msg": sessao.get("msg") or extra.pop("msg", None),
               "erro": sessao.get("erro") or extra.pop("erro", None)}
        ctx.update(extra)
        return ctx

    def _flash(request: Request, msg: str = "", erro: str = ""):
        request.session["flash"] = {"msg": msg, "erro": erro}

    # ---------------- auth ----------------
    @app.get("/login")
    def login_form(request: Request):
        if auth.current_user(request):
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(request=request, name="login.html",
                                          context=_ctx(request))

    @app.post("/login")
    def login(request: Request, username: str = Form(""), password: str = Form("")):
        ip = request.client.host if request.client else "local"
        if auth.login_excedido(ip):
            users.audit("login-bloqueado", username, ip, "rate limit")
            return templates.TemplateResponse(
                request=request, name="login.html",
                context=_ctx(request, erro="Muitas tentativas. Aguarde alguns minutos."))
        user = users.verify_login(username, password)
        if user is None:
            auth.registrar_falha(ip)
            users.audit("login-falha", username, ip)
            return templates.TemplateResponse(
                request=request, name="login.html",
                context=_ctx(request, erro="Usuário ou senha inválidos."), status_code=200)
        auth.limpar_falhas(ip)
        auth.set_user(request, user)
        users.audit("login-ok", user["username"], ip)
        return RedirectResponse("/troca-senha" if user["must_change"] else "/", status_code=303)

    @app.get("/logout")
    def logout(request: Request):
        user = auth.current_user(request)
        if user:
            users.audit("logout", user["username"])
        auth.logout_user(request)
        return RedirectResponse("/login", status_code=303)

    # ---------------- troca de senha ----------------
    @app.get("/troca-senha")
    def troca_form(request: Request):
        user = auth.current_user(request)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(
            request=request, name="troca_senha.html",
            context=_ctx(request, obrigatoria=user["must_change"]))

    @app.post("/troca-senha")
    def troca(request: Request, atual: str = Form(""), nova: str = Form(""),
              confirma: str = Form("")):
        user = auth.current_user(request)
        if user is None:
            return RedirectResponse("/login", status_code=303)
        db_user = users.get_by_id(user["id"])
        if db_user is None or not users.verify_login(db_user["username"], atual):
            return templates.TemplateResponse(
                request=request, name="troca_senha.html",
                context=_ctx(request, erro="Senha atual incorreta.", obrigatoria=True),
                status_code=200)
        if len(nova or "") < 6:
            return templates.TemplateResponse(
                request=request, name="troca_senha.html",
                context=_ctx(request, erro="A nova senha precisa ter ao menos 6 caracteres.",
                             obrigatoria=user["must_change"]), status_code=200)
        if nova != confirma:
            return templates.TemplateResponse(
                request=request, name="troca_senha.html",
                context=_ctx(request, erro="A confirmação não confere com a nova senha.",
                             obrigatoria=user["must_change"]), status_code=200)
        users.change_password(user["id"], nova)
        users.audit("troca-senha", user["username"])
        auth.set_user(request, users.get_by_id(user["id"]))
        _flash(request, msg="Senha alterada com sucesso.")
        return RedirectResponse("/", status_code=303)

    # ---------------- dashboard ----------------
    _DIAS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                "sexta-feira", "sábado", "domingo"]
    _MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

    @app.get("/logo.png")
    def logo_png(user: dict = auth.require_permission("dashboard")):
        from fastapi.responses import FileResponse, Response
        from src.utils.paths import get_logo_path
        try:
            p = get_logo_path()
        except Exception:
            p = None
        if p and Path(p).exists():
            return FileResponse(str(p), media_type="image/png")
        return Response(status_code=404)

    @app.get("/")
    def dashboard(request: Request, user: dict = auth.require_permission("dashboard")):
        from datetime import datetime
        from src.core.employee_repo import EmployeeRepository
        from src.core.history_repo import HistoryRepository
        er = EmployeeRepository()
        hr = HistoryRepository()
        stats = hr.get_dashboard_stats()
        agora = datetime.now()
        anivers_hoje = er.get_aniversariantes(agora.month, agora.day)
        anivers_mes = er.get_aniversariantes(agora.month)
        frota_stats = None
        if pode_usuario(user, "frota"):
            try:
                from src.core.frota_repo import FrotaRepository
                fr = FrotaRepository()
                _, n_veic = fr.list_veiculos(limit=1)
                frota_stats = {"veiculos": n_veic,
                               "movs_abertas": fr.count_movs_abertas(),
                               "custo_mes": fr.custo_mes()}
            except Exception:
                frota_stats = None
        return templates.TemplateResponse(
            request=request, name="dashboard.html",
            context=_ctx(
                request, stats=stats,
                total_funcionarios=er.count_total(),
                total_nrs=len(hr.distinct_nrs()),
                data_extensa=f"{_DIAS_PT[agora.weekday()]}, "
                             f"{agora.day} de {_MESES_PT[agora.month - 1]} de {agora.year}",
                hora_init=agora.strftime("%H:%M:%S"),
                mes_nome=_MESES_PT[agora.month - 1].capitalize(),
                anivers_hoje=anivers_hoje,
                anivers_mes=anivers_mes,
                frota_stats=frota_stats,
                pode_lote=pode_escrever(user["papel"], "certificados")))

    # ---------------- jobs de fundo (progresso, 2.32.1) ----------------
    @app.get("/jobs/{jid}")
    def job_status(jid: str, user: dict = auth.require_permission("dashboard")):
        from fastapi.responses import JSONResponse
        snap = jobs.snapshot(jid)
        if snap is None:
            return JSONResponse({"ok": False, "erro": "job não encontrado"},
                                status_code=404)
        return JSONResponse({"ok": True, **snap})

    # ---------------- usuarios (admin) ----------------
    @app.get("/usuarios")
    def usuarios(request: Request, user: dict = auth.require_permission("usuarios")):
        papel_ov, usuario_ov = users.permissoes_overrides()
        from src.web.permissions import PERMISSIONS
        estado, override = {}, {}
        for modulo, _label in _MODULOS_PERM_UI:
            for papel in ROLES:
                if modulo in (papel_ov.get(papel) or {}):
                    estado[(modulo, papel)] = bool(papel_ov[papel][modulo])
                    override[(modulo, papel)] = True
                else:
                    estado[(modulo, papel)] = papel in PERMISSIONS.get(modulo, set())
                    override[(modulo, papel)] = False
        excecoes = {u["id"]: {m: ("1" if v else "0")
                              for m, v in (usuario_ov.get(u["id"]) or {}).items()}
                    for u in users.list_users()}
        return templates.TemplateResponse(
            request=request, name="usuarios.html",
            context=_ctx(request, usuarios=users.list_users(), papeis=ROLE_LABELS,
                         perm_modulos=_MODULOS_PERM_UI, perm_papeis=ROLES,
                         perm_estado=estado, perm_override=override,
                         perm_excecoes=excecoes))

    @app.post("/usuarios/permissoes")
    async def permissoes_salvar(request: Request,
                                user: dict = auth.require_permission("usuarios")):
        """Salva a matriz módulo × papel (checkbox marcado = permitir)."""
        form = await request.form()
        from src.web.permissions import _MODULOS_ADMIN_FIXOS
        n = 0
        for modulo, _label in _MODULOS_PERM_UI:
            for papel in ROLES:
                if papel == "admin" and modulo in _MODULOS_ADMIN_FIXOS:
                    continue  # fixo: admin não perde Usuários/Configurações
                marcado = form.get(f"perm_{modulo}__{papel}") == "1"
                users.set_permissao_papel(papel, modulo, marcado)
                n += 1
        users.audit("permissoes-papel", user["username"], "matriz",
                    f"{n} celulas gravadas")
        _flash(request, msg="Permissões por papel atualizadas (aplicadas na hora).")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/permissoes/padrao")
    def permissoes_padrao(request: Request,
                          user: dict = auth.require_permission("usuarios")):
        """Restaura a matriz base (apaga os ajustes de papel)."""
        n = users.limpar_permissoes_papel()
        users.audit("permissoes-papel-padrao", user["username"], "matriz",
                    f"{n} ajustes removidos")
        _flash(request, msg="Matriz restaurada ao padrão.")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/{user_id}/permissoes")
    async def permissoes_usuario_salvar(request: Request, user_id: int,
                                        user: dict = auth.require_permission("usuarios")):
        """Exceções de acesso por usuário: permitir/negar/padrão por módulo."""
        alvo = users.get_by_id(user_id)
        if alvo is None:
            _flash(request, erro="Usuário não encontrado.")
            return RedirectResponse("/usuarios", status_code=303)
        form = await request.form()
        n = 0
        for modulo, _label in _MODULOS_PERM_UI:
            valor = form.get(f"exc_{modulo}") or ""
            if valor == "1":
                users.set_excecao_usuario(user_id, modulo, True)
                n += 1
            elif valor == "0":
                users.set_excecao_usuario(user_id, modulo, False)
                n += 1
            else:
                users.set_excecao_usuario(user_id, modulo, None)
        users.audit("permissoes-usuario", user["username"], alvo["username"],
                    f"{n} excecoes gravadas")
        _flash(request, msg=f"Exceções de '{alvo['username']}' atualizadas "
                            f"(aplicadas na hora).")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/criar")
    def usuarios_criar(request: Request, username: str = Form(""), nome: str = Form(""),
                       papel: str = Form("consulta"),
                       user: dict = auth.require_permission("usuarios")):
        try:
            novo_id, provisoria = users.create_user(username, nome, papel)
            users.audit("criar-usuario", user["username"], username, f"papel={papel}")
            _flash(request, msg=f"Usuário '{username.strip().lower()}' criado."
                                f" Senha provisória: {provisoria} (exibida uma única vez).")
        except ValueError as e:
            _flash(request, erro=str(e))
        return RedirectResponse("/usuarios", status_code=303)

    def _guarda_admin_alvo(user: dict, alvo_id: int) -> str:
        alvo = users.get_by_id(alvo_id)
        if alvo is None:
            return "Usuário não encontrado."
        if alvo["papel"] == "admin" and users.count_admins_ativos() <= 1:
            return "Não é possível remover o último administrador ativo."
        return ""

    @app.post("/usuarios/{user_id}/bloquear")
    def usuarios_bloquear(request: Request, user_id: int,
                          user: dict = auth.require_permission("usuarios")):
        if user_id == user["id"]:
            _flash(request, erro="Você não pode bloquear o seu próprio acesso.")
            return RedirectResponse("/usuarios", status_code=303)
        erro = _guarda_admin_alvo(user, user_id)
        if erro:
            _flash(request, erro=erro)
            return RedirectResponse("/usuarios", status_code=303)
        alvo = users.get_by_id(user_id)
        users.set_active(user_id, False)
        users.audit("bloquear-usuario", user["username"], alvo["username"] if alvo else str(user_id))
        _flash(request, msg="Acesso bloqueado.")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/{user_id}/ativar")
    def usuarios_ativar(request: Request, user_id: int,
                        user: dict = auth.require_permission("usuarios")):
        alvo = users.get_by_id(user_id)
        users.set_active(user_id, True)
        users.audit("ativar-usuario", user["username"], alvo["username"] if alvo else str(user_id))
        _flash(request, msg="Acesso reativado.")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/{user_id}/reset")
    def usuarios_reset(request: Request, user_id: int,
                       user: dict = auth.require_permission("usuarios")):
        alvo = users.get_by_id(user_id)
        provisoria = users.reset_password(user_id)
        if provisoria is None:
            _flash(request, erro="Usuário não encontrado.")
        else:
            users.audit("reset-senha", user["username"], alvo["username"] if alvo else str(user_id))
            _flash(request, msg=f"Nova senha provisória de"
                                f" '{alvo['username'] if alvo else '?'}': {provisoria}"
                                f" (exibida uma única vez).")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/{user_id}/senha")
    def usuarios_definir_senha(request: Request, user_id: int,
                               nova: str = Form(""), confirma: str = Form(""),
                               user: dict = auth.require_permission("usuarios")):
        """Admin define a senha do usuário diretamente (sem senha aleatória)."""
        alvo = users.get_by_id(user_id)
        if alvo is None:
            _flash(request, erro="Usuário não encontrado.")
            return RedirectResponse("/usuarios", status_code=303)
        if len(nova.strip()) < 6:
            _flash(request, erro="A nova senha precisa ter ao menos 6 caracteres.")
            return RedirectResponse("/usuarios", status_code=303)
        if nova != confirma:
            _flash(request, erro="A confirmação não confere com a nova senha.")
            return RedirectResponse("/usuarios", status_code=303)
        if not users.change_password(user_id, nova.strip()):
            _flash(request, erro="Não foi possível alterar a senha.")
            return RedirectResponse("/usuarios", status_code=303)
        users.audit("definir-senha", user["username"], alvo["username"])
        _flash(request, msg=f"Senha de '{alvo['username']}' definida.")
        return RedirectResponse("/usuarios", status_code=303)

    # ---------------- routers da Fase 2+3 ----------------
    deps = {"users": users, "templates": templates, "ctx": _ctx, "flash": _flash}
    from src.web.routers import employees as rotas_funcionarios
    from src.web.routers import certificates as rotas_certificados
    from src.web.routers import history as rotas_historico
    from src.web.routers import lote as rotas_lote
    from src.web.routers import vencimentos as rotas_vencimentos
    from src.web.routers import aso as rotas_aso
    from src.web.routers import epi as rotas_epi
    from src.web.routers import crachas as rotas_crachas
    from src.web.routers import cartoes as rotas_cartoes
    from src.web.routers import integracoes as rotas_integracoes
    from src.web.routers import importacoes as rotas_importacoes
    from src.web.routers import configuracoes as rotas_configuracoes
    from src.web.routers import frota as rotas_frota
    from src.web.routers import backup as rotas_backup
    from src.web.routers import auditoria as rotas_auditoria
    from src.web.routers import presencas as rotas_presencas
    rotas_funcionarios.register(app, deps)
    rotas_certificados.register(app, deps)
    rotas_historico.register(app, deps)
    rotas_lote.register(app, deps)
    rotas_vencimentos.register(app, deps)
    rotas_aso.register(app, deps)
    rotas_epi.register(app, deps)
    rotas_crachas.register(app, deps)
    rotas_cartoes.register(app, deps)
    rotas_integracoes.register(app, deps)
    rotas_importacoes.register(app, deps)
    rotas_configuracoes.register(app, deps)
    rotas_frota.register(app, deps)
    rotas_backup.register(app, deps)
    rotas_auditoria.register(app, deps)
    rotas_presencas.register(app, deps)

    return app
