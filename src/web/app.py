"""Portal Web NormaTech — fabrica do app FastAPI (Fase 1).

Rotas: login/logout, dashboard (leitura), usuarios (admin), troca de senha
obrigatoria. Reaproveita src/core/ e o MESMO certificados.db.

Execucao: python run_web.py [--host 0.0.0.0] [--port 8000]
"""

import secrets
from pathlib import Path

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, Response
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

    @app.middleware("http")
    async def _log_acesso(request: Request, call_next):
        """Log no console: usuario_X acessou /caminho (v1.63.1)."""
        response = await call_next(request)
        try:
            _u = auth.current_user(request)
            if _u:
                print(f"[portal] {_u.get('username', '?')} acessou {request.url.path}")
        except Exception:
            pass
        return response

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
        ("__botao__", [("Gest\u00e3o de Frota", "/frota", "frota"), ("Vencimentos da Frota", "/frota/vencimentos", "frota")]),
        ("Seguran\u00e7a", [
            ("Certificados", "/certificados", "certificados"),
            ("Emiss\u00e3o em Lote", "/emissao-lote", "certificados"),
            ("Hist\u00f3rico", "/historico", "historico"),
            ("Listas de Presen\u00e7a", "/presencas", "presencas"),
            ("Ficha de EPIs", "/epi", "epi"),
            ("Crach\u00e1s", "/crachas", "crachas"),
            ("Cintos e Talabartes", "/cintos", "cintos"),  # v1.83.0
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
            ("Romaneios", "/romaneios", "romaneios"),
        ]),
        ("Administração", [("Templates NR", "/admin/templates", "config")]),
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
                                   ("Feedbacks", "/feedbacks", "feedbacks"),
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

    def _databr(v):
        if not v:
            return v
        s = str(v)
        if "/" in s:
            return s
        try:
            from datetime import date as _d
            return _d.fromisoformat(s[:10]).strftime("%d/%m/%Y")
        except Exception:
            return s

    templates.env.filters["databr"] = _databr
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

    @app.get("/favicon.ico")
    def favicon_ico():
        from fastapi.responses import FileResponse, Response
        from src.utils.paths import get_assets_dir
        try:
            p = get_assets_dir() / "favicon.ico"
        except Exception:
            p = None
        if p and p.exists():
            # cache longo: favicon muda raramente
            return FileResponse(str(p), media_type="image/x-icon",
                                headers={"Cache-Control": "public, max-age=604800"})
        return Response(status_code=404, headers={"Cache-Control": "no-cache"})

    @app.get("/logo.png")
    def logo_png(user: dict = auth.require_permission("dashboard")):
        from fastapi.responses import FileResponse, Response
        from src.utils.paths import get_logo_path
        try:
            p = get_logo_path()
        except Exception:
            p = None
        if p and Path(p).exists():
            # v1.82.0: cache no navegador (evita revalidar o logo a cada request)
            return FileResponse(str(p), media_type="image/png",
                                headers={"Cache-Control": "public, max-age=86400"})
        return Response(status_code=404, headers={"Cache-Control": "no-cache"})

    @app.get("/")
    def dashboard(request: Request, user: dict = auth.require_permission("dashboard")):
        from datetime import datetime
        from src.core.employee_repo import EmployeeRepository
        from src.core.history_repo import HistoryRepository
        er = EmployeeRepository()
        hr = HistoryRepository()
        try:  # v1.87.0: feedbacks abertos no dashboard
            from src.core.feedback_repo import FeedbackRepository as fb
            fb = fb()
        except Exception:
            fb = None
        # v1.81.2: carrega a pilha de vencimentos UMA vez e reutiliza nos
        # cards (evita varrer certificados+ASOs+integracoes 3x por request)
        _pilha_itens = None
        try:
            from src.web.routers.vencimentos import _carregar_items as _ci
            _pilha_itens = _ci()
        except Exception:
            _pilha_itens = None
        stats = hr.get_dashboard_stats(itens=_pilha_itens)
        agora = datetime.now()
        anivers_hoje = er.get_aniversariantes(agora.month, agora.day)
        anivers_mes = er.get_aniversariantes(agora.month)
        venc_resumo = None
        try:
            from src.web.routers.vencimentos import resumo_vencimentos
            venc_resumo = resumo_vencimentos(itens=_pilha_itens)
        except Exception:
            venc_resumo = None
        try:
            _u_db = users.get_by_id(user["id"])
            setor_usuario = (dict(_u_db).get("setor") if _u_db else "") or ""
        except Exception:
            setor_usuario = ""
        frota_stats = None
        if pode_usuario(user, "frota"):
            try:
                from src.core.frota_repo import FrotaRepository
                fr = FrotaRepository()
                _, n_veic = fr.list_veiculos(limit=1)
                frota_stats = {"veiculos": n_veic,
                               "movs_abertas": fr.count_movs_abertas(),
                               "custo_mes": fr.custo_mes(),
            "sem_nf": fr.count_abast_sem_nf(),
            "sem_valor": fr.count_abast_sem_valor(),
        }
            except Exception:
                frota_stats = None
        # cards modulares (v1.63.1): usuario escolhe quais cards ver
        try:
            _prefs = users.get_cards_prefs(user["id"])
        except Exception:
            _prefs = None
        cert30 = 0
        try:
            # v1.80.1: mesma fonte da pagina /vencimentos (certs + ASOs + integracoes)
            # v1.81.2: reusa a pilha ja carregada acima (sem nova varredura)
            if _pilha_itens is not None:
                cert30 = sum(1 for _c in _pilha_itens if 0 <= _c["dias_para_vencer"] <= 30)
            else:
                from src.web.routers.vencimentos import _carregar_items as _ci2
                cert30 = sum(1 for _c in _ci2() if 0 <= _c["dias_para_vencer"] <= 30)
        except Exception:
            pass
        try:
            sem_assin = hr.count_sem_assinatura()
        except Exception:
            pass
        frotavenc = 0
        _pode_frota = False
        try:
            from src.web.routers.vencimentos import _carregar_frota as _cf
            frotavenc = sum(1 for _c in _cf() if 0 <= _c["dias_para_vencer"] <= 30)
        except Exception:
            pass
        try:
            from src.web.permissions import pode_usuario as _pu
            try:
                _pode_frota = _pu(user, "frota")
            except TypeError:
                _pode_frota = _pu(user.get("papel"), "frota")
        except Exception:
            pass
        # v1.72.0: cards respeitam permissoes do usuario (_pu ja importado acima)
        def _pm(mod):
            try:
                return bool(_pu(user, mod))
            except TypeError:
                return bool(_pu(user.get("papel"), mod))
        cards = {
            "historico": _pm("certificados"),
            "funcionarios": _pm("funcionarios"),
            "nrs": _pm("certificados"),
            "cert30": _pm("certificados"),
        "frotavenc": _pode_frota,
            "venc30": bool(setor_usuario == "seguranca" and venc_resumo
                           and _pm("vencimentos")),
            "veiculos": bool(frota_stats), "saidas": bool(frota_stats),
            "custo": bool(frota_stats),
         "sem_nf": bool(frota_stats),
            "sem_valor": bool(frota_stats),
            "sem_assinatura": _pm("certificados"),
            "cert_vencidos": _pm("certificados"),  # v1.79.0
            # v1.76.0: novos cards
            "aso_vencidos": _pm("aso"),
            "aso_30": _pm("aso"),
            "veic_bloq": _pode_frota,
            "pres_pend": _pm("presencas"),
            "func_incomp": _pm("funcionarios"),
        "cintos_venc": _pm("cintos"), "cintos_prox": _pm("cintos"),  # v1.85.0
        }
        # v1.72.0: prefs padrao por setor quando o usuario nao personalizou
        if not _prefs and setor_usuario:
            try:
                _prefs = users.get_setor_cards(setor_usuario)
            except Exception:
                _prefs = None
        if _prefs:
            for _k in cards:
                cards[_k] = cards[_k] and bool(_prefs.get(_k, True))
        cards_opcoes = [
            ("historico", "Certificados emitidos"),
            ("funcionarios", "Funcion\u00e1rios cadastrados"),
            ("nrs", "NRs dispon\u00edveis"),
            ("cert30", "Vencimentos em 30 dias"),
        ("frotavenc", "Vencimentos da frota"),
            ("sem_assinatura", "Certificados sem documento assinado"),
            ("cert_vencidos", "Certificados vencidos"),  # v1.79.0
        ]
        if setor_usuario == "seguranca":
            cards_opcoes.append(("venc30", "Vencem em 30 dias (vencimentos)"))
        cards_opcoes += [
            ("veiculos", "Ve\u00edculos na frota"),
            ("saidas", "Sa\u00eddas (ve\u00edculos) em aberto"),  # v1.79.0: renomeado
            ("custo", "Custo de abastecimento (m\u00eas)"),
            ("sem_nf", "Abastecimentos sem nota fiscal"),
            ("sem_valor", "Abastecimentos sem valor"),
            # v1.76.0
            ("aso_vencidos", "ASOs vencidos"),
            ("aso_30", "ASOs vencem em 30 dias"),
            ("veic_bloq", "Ve\u00edculos bloqueados"),
            ("pres_pend", "Listas de presen\u00e7a n\u00e3o assinadas"),
            ("func_incomp", "Funcion\u00e1rios com cadastro incompleto"),
            ("cintos_venc", "Inspe\u00e7\u00f5es atrasadas (cintos)"),
            ("cintos_prox", "Inspe\u00e7\u00f5es pr\u00f3ximas 30 dias (cintos)"),  # v1.85.0
        ]
        # v1.76.0: novos cards (ASOs, veiculos bloqueados, presencas, cadastro)
        _aso_venc = _aso_30 = _veic_bloq = _pres_pend = _func_incomp = 0
        try:
            # v1.82.0: reusa a pilha ja carregada (ASOs vem de
            # get_asos_with_expiration, only_latest=True por padrao) — sem nova
            # varredura da tabela de ASOs
            if _pilha_itens is not None:
                _asos = [a for a in _pilha_itens if a.get("nr_code") == "ASO"]
            else:
                from src.core.aso_repo import AsoRepository as _AsoR
                _asos = _AsoR().get_asos_with_expiration(only_latest=True)
            _aso_venc = sum(1 for a in _asos if a["dias_para_vencer"] < 0)
            _aso_30 = sum(1 for a in _asos if 0 <= a["dias_para_vencer"] <= 30)
            _aso_ok = {a["employee_id"] for a in _asos
                       if a["dias_para_vencer"] >= 0}
            _func_incomp = 0
            # v1.82.0: consulta enxuta (id/arquivado/foto/cpf/funcao/telefone),
            # sem carregar objetos Employee com blobs de foto
            for (_eid, _arq, _tem_foto, _cpf, _funcao, _tel) in \
                    er.iter_cadastro_check():
                if _arq:
                    continue
                if (not _tem_foto or not (_cpf or "").strip()
                        or not (_funcao or "").strip()
                        or not (_tel or "").strip()
                        or _eid not in _aso_ok):
                    _func_incomp += 1
        except Exception:
            _aso_venc = _aso_30 = _func_incomp = 0
        try:
            from src.core.frota_repo import FrotaRepository as _FrotaR
            _veic_bloq = _FrotaR().count_veiculos_bloqueados()
        except Exception:
            _veic_bloq = 0
        try:
            from src.core.presenca_repo import PresencaRepository as _PresR
            _c = _PresR().count_por_status()
            _pres_pend = _c.get("pendente", 0) + _c.get("parcial", 0)
        except Exception:
            _pres_pend = 0
        # v1.79.0: card de certificados vencidos (apenas certificados, sem ASOs)
        _cert_venc = 0
        try:
            # v1.82.0: reusa a pilha ja carregada (sem nova varredura completa)
            if _pilha_itens is not None:
                _cert_venc = sum(
                    1 for _c in _pilha_itens
                    if str(_c.get("nr_code", "")) != "ASO"
                    and not str(_c.get("nr_code", "")).startswith("INTEGRA")
                    and _c["dias_para_vencer"] < 0)
            else:
                _cert_venc = sum(1 for _c in hr.get_certificates_with_expiration()
                                 if _c["dias_para_vencer"] < 0)
        except Exception:
            _cert_venc = 0

        # v1.85.0: cards de inspeções de cintos/talabartes (atrasadas / próximas 30 dias)
        _cintos_venc = _cintos_prox = 0
        if _pm("cintos"):
            try:
                from src.core.cinto_repo import CintoRepository as _CintoR
                _cc = _CintoR().counts_situacao()
                _cintos_venc = _cc.get("insp_vencidas", 0)
                _cintos_prox = _cc.get("insp_proximas", 0)
            except Exception:
                _cintos_venc = _cintos_prox = 0

        # v1.73.1: area de Atalhos — personalizavel, respeita permissoes
        _pode_lote = pode_escrever(user["papel"], "certificados")
        _atalhos = {
            "cert": _pm("certificados"),
            "funcionarios": _pm("funcionarios"),
            "historico": _pm("certificados"),
            "vencimentos": _pm("vencimentos"),
            "lote": _pode_lote,
            "frota": _pode_frota,
            # v1.74.0: novos atalhos
            "presencas": _pm("presencas"),
            "epi": _pm("epi"),
            "crachas": _pm("crachas"),
            "cartoes": _pm("cartoes"),
            "aso": _pm("aso"),
            "feedbacks": _pm("feedbacks"),
        }
        _atalhos_prefs = None
        try:
            _atalhos_prefs = users.get_atalhos_prefs(user["id"])
        except Exception:
            _atalhos_prefs = None
        if not _atalhos_prefs and setor_usuario:
            # v1.77.0: fallback para o padrao de atalhos definido pelo admin para o setor
            try:
                _atalhos_prefs = users.get_setor_atalhos(setor_usuario)
            except Exception:
                _atalhos_prefs = None
        # v1.82.0: snapshot das permissoes puras (antes dos prefs do usuario),
        # para que o modal de atalhos nunca ofereca modulos sem permissao
        _atalhos_perm = dict(_atalhos)
        if _atalhos_prefs:
            for _k in _atalhos:
                _atalhos[_k] = _atalhos[_k] and bool(_atalhos_prefs.get(_k, True))
        atalhos_opcoes = [
            ("cert", "Emitir Certificado"),
            ("funcionarios", "Funcion\u00e1rios"),
            ("historico", "Hist\u00f3rico"),
            ("vencimentos", "Vencimentos"),
            ("lote", "Emiss\u00e3o em Lote"),
            ("frota", "Gest\u00e3o de Frota"),
            ("presencas", "Listas de Presen\u00e7a"),
            ("epi", "Ficha de EPIs"),
            ("crachas", "Crach\u00e1s"),
            ("cartoes", "Cart\u00f5es de Bloqueio"),
            ("aso", "ASO"),
            ("feedbacks", "Feedbacks"),
        ]
        # v1.82.0: modal so oferece atalhos de modulos com permissao (corrige
        # vazamento de rotulo p.ex. "Cartoes de Bloqueio" para role consulta)
        atalhos_opcoes = [(k, r) for (k, r) in atalhos_opcoes if _atalhos_perm.get(k)]
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
                pode_lote=_pode_lote,
                venc_resumo=venc_resumo,
                setor_usuario=setor_usuario,
                cards=cards,
                cards_opcoes=cards_opcoes, cert30=cert30, frotavenc=frotavenc,
                sem_assinatura=sem_assin,
                aso_vencidos=_aso_venc, aso_30=_aso_30,
                veic_bloq=_veic_bloq, pres_pend=_pres_pend,
                func_incomp=_func_incomp, cert_vencidos=_cert_venc,
                cintos_venc=_cintos_venc, cintos_prox=_cintos_prox,
                pode_setor_cards=bool(user.get("papel") == "admin"
                                      and setor_usuario),
                             sem_nf=(frota_stats.get("sem_nf", 0) if frota_stats else 0),
                             sem_valor=(frota_stats.get("sem_valor", 0) if frota_stats else 0),
                             abertos=(fb.contagem_abertos() if fb else 0),
                             atalhos=_atalhos, atalhos_opcoes=atalhos_opcoes))

    @app.post("/perfil/cards")
    def perfil_cards(request: Request, card: list = Form([]),
                     salvar_setor: str = Form(""),
                     user: dict = auth.require_permission("dashboard")):
        """Salva quais cards do dashboard o usuario quer ver (v1.63.1)."""
        import json as _json
        chaves = ("historico", "funcionarios", "nrs", "cert30", "frotavenc", "venc30",
                  "veiculos", "saidas", "custo",
                  "sem_nf", "sem_valor", "sem_assinatura",
                  "aso_vencidos", "aso_30", "veic_bloq", "pres_pend",
                  "func_incomp", "cert_vencidos",
                  "cintos_venc", "cintos_prox")
        prefs = {k: (k in card) for k in chaves}
        users.set_cards_prefs(user["id"], _json.dumps(prefs))
        # v1.72.0: admin pode gravar a escolha como padrao do seu setor
        if salvar_setor and user.get("papel") == "admin":
            try:
                users.set_setor_cards(setor_usuario, _json.dumps(prefs))
                _flash(request, msg="Cards do painel atualizados e gravados "
                                    "como padrão do setor.")
            except Exception:
                _flash(request, msg="Cards do painel atualizados.")
        else:
            _flash(request, msg="Cards do painel atualizados.")
        try:
            users.audit("cards-dashboard", user["username"], "dashboard")
        except Exception:
            pass
        _flash(request, msg="Cards do painel atualizados.")
        return RedirectResponse("/", 303)

    @app.post("/perfil/atalhos")
    def perfil_atalhos(request: Request, atalho: list = Form([]),
                       user: dict = auth.require_permission("dashboard")):
        """Salva quais atalhos o usuario quer ver no dashboard (v1.73.1)."""
        import json as _json
        chaves = ("cert", "funcionarios", "historico", "vencimentos", "lote", "frota",
                  "presencas", "epi", "crachas", "cartoes", "aso")
        prefs = {k: (k in atalho) for k in chaves}
        try:
            users.set_atalhos_prefs(user["id"], _json.dumps(prefs))
        except Exception:
            pass
        try:
            users.audit("atalhos-dashboard", user["username"], "dashboard")
        except Exception:
            pass
        _flash(request, msg="Atalhos atualizados.")
        return RedirectResponse("/", 303)

    # ---------------- jobs de fundo (progresso, 2.32.1) ----------------
    @app.get("/jobs/{jid}")
    def job_status(jid: str, user: dict = auth.require_permission("dashboard")):
        from fastapi.responses import JSONResponse
        snap = jobs.snapshot(jid)
        if snap is None:
            return JSONResponse({"ok": False, "erro": "job não encontrado"},
                                status_code=404)
        return JSONResponse({"ok": True, **snap})


    # ---------------- perfil do usuario (v1.59.0) ----------------
    @app.get("/perfil")
    def perfil_ver(request: Request, user: dict = auth.require_permission("dashboard")):
        u = users.get_by_id(user["id"])
        return templates.TemplateResponse(
            request=request, name="perfil.html",
            context=_ctx(request, me=u))

    @app.post("/perfil/nome")
    async def perfil_nome(request: Request, user: dict = auth.require_permission("dashboard")):
        form = await request.form()
        nome = (form.get("nome") or "").strip()
        users.set_nome(user["id"], nome)
        auth.set_user(request, users.get_by_id(user["id"]))
        users.audit("perfil-nome", user["username"])
        _flash(request, msg="Nome atualizado.")
        return RedirectResponse("/perfil", status_code=303)

    @app.post("/perfil/senha")
    async def perfil_senha(request: Request, user: dict = auth.require_permission("dashboard")):
        form = await request.form()
        atual = form.get("atual") or ""
        nova = form.get("nova") or ""
        confirma = form.get("confirma") or ""
        if users.verify_login(user["username"], atual) is None:
            _flash(request, erro="Senha atual incorreta.")
        elif len(nova) < 6:
            _flash(request, erro="A nova senha deve ter pelo menos 6 caracteres.")
        elif nova != confirma:
            _flash(request, erro="A confirmação não confere com a nova senha.")
        else:
            users.change_password(user["id"], nova)
            users.audit("perfil-senha", user["username"])
            _flash(request, msg="Senha alterada com sucesso.")
        return RedirectResponse("/perfil", status_code=303)

    @app.get("/perfil/foto/img")
    def perfil_foto_img(request: Request, user: dict = auth.require_permission("dashboard")):
        dados = users.get_foto(user["id"])
        if not dados:
            raise HTTPException(status_code=404)
        blob, tipo = dados
        media = "image/jpeg" if tipo in ("jpg", "jpeg") else f"image/{tipo}"
        return Response(content=blob, media_type=media)

    @app.post("/perfil/foto")
    async def perfil_foto(request: Request, user: dict = auth.require_permission("dashboard"),
                          foto: UploadFile = File(None)):
        dados = await foto.read() if foto is not None else b""
        nome = (foto.filename or "") if foto is not None else ""
        ext = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
        if not dados:
            _flash(request, erro="Selecione um arquivo de imagem.")
            return RedirectResponse("/perfil", status_code=303)
        if ext not in ("png", "jpg", "jpeg"):
            _flash(request, erro="Formato nao suportado (use PNG ou JPG).")
            return RedirectResponse("/perfil", status_code=303)
        if len(dados) > 3 * 1024 * 1024:
            _flash(request, erro="Imagem muito grande (maximo 3 MB).")
            return RedirectResponse("/perfil", status_code=303)
        users.set_foto(user["id"], dados, ext)
        users.audit("perfil-foto", user["username"])
        _flash(request, msg="Foto atualizada.")
        return RedirectResponse("/perfil", status_code=303)

    @app.post("/perfil/foto/remover")
    def perfil_foto_remover(request: Request, user: dict = auth.require_permission("dashboard")):
        users.remover_foto(user["id"])
        users.audit("perfil-foto-remover", user["username"])
        _flash(request, msg="Foto removida.")
        return RedirectResponse("/perfil", status_code=303)

    @app.post("/perfil/notificacoes")
    async def perfil_notificacoes(request: Request, user: dict = auth.require_permission("dashboard")):
        form = await request.form()
        users.set_pref_notif(user["id"], form.get("notif") == "1")
        auth.set_user(request, users.get_by_id(user["id"]))
        _flash(request, msg="Preferências de notificação salvas.")
        return RedirectResponse("/perfil", status_code=303)

    # ---------------- usuarios (admin) ----------------
    from src.web.permissions import SETORES as _SETORES_LIST
    _SETORES_FLAT = [(s, lbl) for s, lbl in _SETORES_LIST]

    def _perm_setores_ctx():
        """Estado das regras setor -> modulo para a tela Usuários."""
        from src.web.permissions import SETORES
        regras, _user_setor = users.setores_overrides()
        return [{"setor": s, "label": lbl,
                 "regras": regras.get(s) or {}}
                for s, lbl in SETORES]

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
                         perm_excecoes=excecoes,
                         perm_setores=_perm_setores_ctx(),
                         perm_setores_flat=_SETORES_FLAT))

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
                       papel: str = Form("consulta"), setor: str = Form(""),
                       user: dict = auth.require_permission("usuarios")):
        try:
            novo_id, provisoria = users.create_user(username, nome, papel)
            if setor.strip():
                users.set_setor(novo_id, setor)
            users.audit("criar-usuario", user["username"], username, f"papel={papel}")
            _flash(request, msg=f"Usuário '{username.strip().lower()}' criado."
                                f" Senha provisória: {provisoria} (exibida uma única vez).")
        except ValueError as e:
            _flash(request, erro=str(e))
        return RedirectResponse("/usuarios", status_code=303)


    @app.post("/usuarios/permissoes-setor")
    async def permissoes_setor_salvar(request: Request,
                                      user: dict = auth.require_permission("usuarios")):
        """Regras setor -> modulo (checkbox marcado = setor acessa o modulo)."""
        from src.web.permissions import SETORES as _SETORES
        form = await request.form()
        setor = (form.get("setor") or "").strip().lower()
        if setor not in {s for s, _l in _SETORES}:
            _flash(request, erro="Setor inválido.")
            return RedirectResponse("/usuarios", status_code=303)
        n = 0
        for modulo, _label in _MODULOS_PERM_UI:
            marcado = form.get(f"setor_{modulo}") == "1"
            users.set_regra_setor(setor, modulo, True if marcado else None)
            n += 1
        from src.web.permissions import invalidar_cache_permissoes
        invalidar_cache_permissoes()
        users.audit("permissoes-setor", user["username"], setor,
                    f"{n} modulos avaliados")
        _flash(request, msg=f"Permissões do setor '{setor}' atualizadas.")
        return RedirectResponse("/usuarios", status_code=303)

    @app.post("/usuarios/{user_id}/setor")
    async def usuario_setor(request: Request, user_id: int,
                            user: dict = auth.require_permission("usuarios")):
        form = await request.form()
        alvo = users.get_by_id(user_id)
        if alvo is None:
            _flash(request, erro="Usuário não encontrado.")
        else:
            users.set_setor(user_id, form.get("setor") or "")
            from src.web.permissions import invalidar_cache_permissoes
            invalidar_cache_permissoes()
            users.audit("setor-usuario", user["username"], alvo["username"],
                        f"setor={form.get('setor') or ''}")
            _flash(request, msg=f"Setor de '{alvo['username']}' atualizado.")
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
    from src.web.routers import romaneios as rotas_romaneios
    from src.web.routers import admin_templates as rotas_admin_templates
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
    rotas_romaneios.register(app, deps)
    rotas_admin_templates.register(app, deps)
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

    # v1.83.0: controle de cintos e talabartes
    from src.web.routers import cintos as rotas_cintos
    rotas_cintos.register(app, deps)

    # v1.87.0: modulo de feedback
    from src.web.routers import feedback as rotas_feedback
    rotas_feedback.register(app, deps)

    # ---------------- tarefas agendadas (v1.67.1) ----------------
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from src.utils import email_report

        def _normatech_diarias() -> None:
            try:
                email_report.tarefas_diarias()
            except Exception:
                from src.utils.error_log import log_error
                log_error("portal-tarefas-diarias")

        try:
            email_report.limpar_previews()
        except Exception:
            pass
        _sched = BackgroundScheduler(daemon=True)
        _sched.add_job(_normatech_diarias, "cron", hour=7, minute=30,
                       id="normatech-diarias", replace_existing=True)
        _sched.start()
        app.state.normatech_scheduler = _sched
    except Exception:
        pass

    return app
