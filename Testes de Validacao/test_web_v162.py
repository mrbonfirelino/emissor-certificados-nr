# -*- coding: utf-8 -*-
"""Testes do Portal Web - v1.62.4.

Cobre:
- GET /api/vencimentos/resumo (notificacoes do navegador): 200, JSON valido
  com notif/setor_usuario, usando usuario sqlite3.Row (regressao do
  AttributeError 'sqlite3.Row' object has no attribute 'get')
- Smoke das rotas de API chamadas pelo dashboard logado
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHA'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="webv1624_"))
    tmp.mkdir(parents=True, exist_ok=True)
    import src.utils.paths as paths_mod
    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.frota_repo as fr_mod
    import src.core.config as config_mod
    import src.web.app as app_mod

    paths_mod.get_data_dir = lambda: tmp
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    fr_mod.get_db_path = lambda: tmp / "certificados.db"
    config_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    app_mod.get_data_dir = lambda: tmp

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
    client.post("/troca-senha", data={"atual": prov, "nova": "nova1624",
                                      "confirma": "nova1624"})


def main():
    print("=== v1.62.4: /api/vencimentos/resumo (Row .get) ===")
    client, tmp = make_env()
    _login_admin(client, tmp)

    r = client.get("/api/vencimentos/resumo")
    check("V62-1 resumo 200", r.status_code == 200)
    dados = {}
    try:
        dados = r.json()
    except Exception:
        pass
    check("V62-2 JSON com total/alertas/status",
          isinstance(dados, dict) and "total" in dados
          and "alertas" in dados and "status" in dados)
    check("V62-3 notif presente (bool)",
          isinstance(dados.get("notif"), bool))
    check("V62-4 setor_usuario presente (str)",
          isinstance(dados.get("setor_usuario"), str))
    check("V62-5 itens_urgentes lista",
          isinstance(dados.get("itens_urgentes"), list))
    check("V62-6 por_setor dict",
          isinstance(dados.get("por_setor"), dict))

    # repete: chamada com usuario sem pref_notif/setor nao pode 500
    r2 = client.get("/api/vencimentos/resumo")
    check("V62-7 segunda chamada 200", r2.status_code == 200)

    # smoke: paginas que o dashboard carrega logado
    for caminho in ("/", "/vencimentos", "/perfil"):
        rr = client.get(caminho)
        check(f"V62-8 GET {caminho} 200", rr.status_code == 200)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS:")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TODOS OS CHECKS DA v1.62.4 PASSARAM.")


if __name__ == "__main__":
    main()
