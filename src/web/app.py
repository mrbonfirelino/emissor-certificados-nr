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

from src.utils.paths import get_data_dir
from src.web import auth
from src.web.permissions import ROLE_LABELS, pode
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

    # Módulos implementados no portal (Fase 1+2); a matriz de permissões
    # (permissions.pode) filtra o que cada papel vê.
    _MODULOS_NAV = [
        ("Dashboard", "/", "dashboard"),
        ("Certificados", "/certificados", "certificados"),
        ("Funcionários", "/funcionarios", "funcionarios"),
        ("Histórico", "/historico", "historico"),
    ]

    def _nav(user: dict, caminho: str = "") -> list:
        itens = []
        for label, url, modulo in _MODULOS_NAV:
            if not pode(user["papel"], modulo):
                continue
            ativo = (caminho == url) if url == "/" else caminho.startswith(url)
            itens.append({"label": label, "url": url, "ativo": ativo})
        if pode(user["papel"], "usuarios"):
            itens.append({"label": "Usuários", "url": "/usuarios",
                          "ativo": caminho.startswith("/usuarios")})
        return itens

    def _ctx(request: Request, **extra) -> dict:
        user = auth.current_user(request)
        sessao = request.session.pop("flash", None) or {}
        ctx = {"request": request, "user": user,
               "nav": _nav(user, request.url.path) if user else [],
               "papel_label": ROLE_LABELS.get(user["papel"], user["papel"]) if user else "",
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
    @app.get("/")
    def dashboard(request: Request, user: dict = auth.require_permission("dashboard")):
        from src.core.history_repo import HistoryRepository
        stats = HistoryRepository().get_dashboard_stats()
        return templates.TemplateResponse(request=request, name="dashboard.html",
                                          context=_ctx(request, stats=stats))

    # ---------------- usuarios (admin) ----------------
    @app.get("/usuarios")
    def usuarios(request: Request, user: dict = auth.require_permission("usuarios")):
        return templates.TemplateResponse(
            request=request, name="usuarios.html",
            context=_ctx(request, usuarios=users.list_users(), papeis=ROLE_LABELS))

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

    # ---------------- routers da Fase 2 ----------------
    deps = {"users": users, "templates": templates, "ctx": _ctx, "flash": _flash}
    from src.web.routers import employees as rotas_funcionarios
    from src.web.routers import certificates as rotas_certificados
    from src.web.routers import history as rotas_historico
    rotas_funcionarios.register(app, deps)
    rotas_certificados.register(app, deps)
    rotas_historico.register(app, deps)

    return app
