# -*- coding: utf-8 -*-
"""Testes do Portal Web - v1.63.1 (itens medios do roadmap novo).

Cobre:
- 925: botao toggle-senha do login com cor/contraste (#333, 18px)
- 879/931: opcionais da emissao em lote dentro de <details> recolhido
- 929: rota /certificados/exemplo gera PDF inline sem gravar historico
- 907: funcionario_form com foto no topo direito (header flex)
- 924: middleware de log 'usuario acessou /path' no create_app
- 927: stat-cards modulares (cards_prefs em users, editor no dashboard)
"""
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHA'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="webv1631_"))
    tmp.mkdir(parents=True, exist_ok=True)
    import src.utils.paths as paths_mod
    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.frota_repo as fr_mod
    import src.core.config as config_mod
    import src.web.app as app_mod
    import src.core.certificate_service as cs_mod

    paths_mod.get_data_dir = lambda: tmp
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    fr_mod.get_db_path = lambda: tmp / "certificados.db"
    config_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    app_mod.get_data_dir = lambda: tmp
    import src.web.users_repo as users_mod
    users_mod.get_db_path = lambda: tmp / "certificados.db"

    # evita PDF real no teste da rota exemplo: preview retorna None -> flash/redirect
    class _SvcFalso:
        def __init__(self, *a, **k):
            pass

        def generate_preview_pdf(self, *a, **k):
            return None

    cs_mod.CertificateService = _SvcFalso

    from src.web.app import create_app
    from fastapi.testclient import TestClient
    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    client = TestClient(app, follow_redirects=False)
    return client, tmp


def _login_admin(client, tmp):
    from src.core.employee_repo import EmployeeRepository
    from src.core.frota_repo import FrotaRepository
    EmployeeRepository()
    FrotaRepository()
    txt = (tmp / "web_admin_provisorio.txt").read_text(encoding="utf-8")
    prov = [l.split(":")[1].strip() for l in txt.splitlines()
            if l.startswith("SENHA PROVISORIA")][0]
    client.post("/login", data={"username": "admin", "password": prov})
    client.post("/troca-senha", data={"atual": prov, "nova": "nova1631",
                                      "confirma": "nova1631"})
    return prov


def main():
    print("=== v1.63.1: itens medios (925/879-931/929/907/924/927) ===")
    raiz = Path(__file__).resolve().parent.parent
    tpl = raiz / "src" / "web" / "templates"

    client, tmp = make_env()
    _login_admin(client, tmp)

    # --- 925: toggle-senha com contraste ---
    login = (tpl / "login.html").read_text(encoding="utf-8")
    check("V631-1 login: toggle com color #333",
          "toggle-senha" in login and "color:#333" in login)
    check("V631-2 login: fonte 18px",
          "font-size:18px" in login)

    # --- 879/931: opcionais do lote em <details> ---
    lote = (tpl / "emissao_lote.html").read_text(encoding="utf-8")
    check("V631-3 lote: <details> envolvendo opcionais",
          "<details" in lote and "form-grid lote-grid" in lote
          and lote.count("</details>") >= 1
          and lote.index("<details") < lote.index('name="carga"'))

    # --- 929: rota /certificados/exemplo ---
    certs_py = (raiz / "src" / "web" / "routers" / "certificates.py").read_text(encoding="utf-8")
    check("V631-4 rota /certificados/exemplo existe",
          '@app.get("/certificados/exemplo")' in certs_py
          and "generate_preview_pdf" in certs_py)
    certs_html = (tpl / "certificados.html").read_text(encoding="utf-8")
    check("V631-5 botao Gerar exemplo no form",
          "/certificados/exemplo?nr=" in certs_html)
    r = client.get("/certificados/exemplo?nr=NR-35")
    # com service falso (preview None) deve redirecionar com flash, nao 500
    check("V631-6 exemplo sem PDF -> redirect 303 (sem 500)",
          r.status_code == 303)

    # --- 907: foto no topo direito ---
    fform = (tpl / "funcionario_form.html").read_text(encoding="utf-8")
    check("V631-7 funcionario_form: header flex com foto",
          "justify-content:space-between" in fform
          and "Foto atual" in fform
          and fform.index("justify-content:space-between") < fform.index("form-grid"))

    # --- 924: middleware de log ---
    app_py = (raiz / "src" / "web" / "app.py").read_text(encoding="utf-8")
    check("V631-8 middleware _log_acesso no create_app",
          '_log_acesso' in app_py and "acessou" in app_py)

    # --- 927: cards modulares ---
    users_py = (raiz / "src" / "web" / "users_repo.py").read_text(encoding="utf-8")
    check("V631-9 users_repo: cards_prefs (migracao + metodos)",
          "cards_prefs" in users_py and "set_cards_prefs" in users_py
          and "get_cards_prefs" in users_py)
    r = client.get("/")
    check("V631-10 dashboard 200", r.status_code == 200)
    check("V631-11 dashboard: editor 'Escolher cards do painel'",
          "Escolher cards do painel" in r.text and "/perfil/cards" in r.text)
    # admin sem setor: card venc30 NAO aparece; frota aparece (frota vazia -> sem frota_stats)
    check("V631-12 dashboard: cards padrao visiveis",
          '<a class="stat-card" href="/historico">' in r.text
          and '<a class="stat-card" href="/certificados">' in r.text)
    check("V631-13 dashboard: venc30 oculto para admin sem setor seguranca",
          "Vencem em 30 dias (vencimentos)" not in r.text)
    # salvar prefs desmarcando tudo (exceto nada marcado)
    r = client.post("/perfil/cards", data={})
    check("V631-14 POST /perfil/cards -> 303", r.status_code == 303)
    r = client.get("/")
    check("V631-15 dashboard: cards ocultos apos salvar vazio",
          '<a class="stat-card" href="/historico">' not in r.text)
    # restaurar marcando tudo
    client.post("/perfil/cards", data={"card": ["historico", "funcionarios", "nrs"]})
    r = client.get("/")
    check("V631-16 dashboard: cards restaurados",
          '<a class="stat-card" href="/historico">' in r.text
          and '<a class="stat-card" href="/funcionarios">' in r.text)
    # prefs persistidas no DB
    from src.web.users_repo import UsersRepository
    ur = UsersRepository()
    prefs = ur.get_cards_prefs(1)
    check("V631-17 prefs persistidas no users",
          isinstance(prefs, dict) and prefs.get("historico") is True)

    # --- migracao cards_prefs em DB existente (idempotente) ---
    ur2 = UsersRepository()  # mesma base tmp do app
    check("V631-18 get_cards_prefs retorna dict/None sem erro",
          ur2.get_cards_prefs(1) is None or isinstance(ur2.get_cards_prefs(1), dict))

    print()
    if FALHAS:
        print(f"RESULTADO: {len(FALHAS)} FALHA(S): {FALHAS}")
        return 1
    print("RESULTADO: TUDO OK")
    return 0


from types import SimpleNamespace  # noqa: E402 (usado em make_env)

if __name__ == "__main__":
    sys.exit(main())
