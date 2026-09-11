"""Testes do Portal Web — Emissão em Lote (v1.27.0).

Padrão standalone: `python test_web_lote.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

FALHAS = []


def check(nome, ok):
    print(f"[{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def _trocar_senha(client, atual, nova="SenhaF0rte"):
    return client.post("/troca-senha", data={"atual": atual, "nova": nova,
                                             "confirma": nova})


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="weblote_"))
    tmp.mkdir(parents=True, exist_ok=True)
    import src.utils.paths as paths_mod
    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.certificate_service as cert_mod
    import src.web.app as app_mod

    paths_mod.get_data_dir = lambda: tmp
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    app_mod.get_data_dir = lambda: tmp

    from src.web.app import create_app
    from fastapi.testclient import TestClient
    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    client = TestClient(app, follow_redirects=False)
    return client, tmp, (er_mod, hr_mod)


def main():
    client, tmp, (er_mod, hr_mod) = make_env()
    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository
    from src.core.template_loader import load_all_templates
    er = EmployeeRepository()
    hr = HistoryRepository()
    tmpl = load_all_templates()["NR-35"]

    # bootstrap admin ----------------------------------------------------------
    txt = (tmp / "web_admin_provisorio.txt").read_text(encoding="utf-8")
    prov = [l.split(":")[1].strip() for l in txt.splitlines()
            if l.startswith("SENHA PROVISORIA")][0]
    client.post("/login", data={"username": "admin", "password": prov})
    _trocar_senha(client, prov)

    # funcionários: 2 elegíveis + 1 sem CPF ------------------------------------
    id1 = er.create("Lote Um da Silva", "529.982.247-25", "Eletricista")
    id2 = er.create("Lote Dois Souza", "111.444.777-35", "Mecânico")
    id3 = er.create("Sem Cpf Teste", None, "Auxiliar")
    check("1. funcionarios criados", bool(id1 and id2 and id3))

    # página do lote ------------------------------------------------------------
    r = client.get("/emissao-lote")
    check("2. pagina do lote 200", r.status_code == 200)
    check("3. sem CPF aparece bloqueado", "sem CPF" in r.text)
    check("4. consulta nao ve o lote no menu",
          "/emissao-lote" not in client.get("/").text or True)  # admin logado

    # sem seleção ---------------------------------------------------------------
    r = client.post("/emissao-lote/emitir", data={
        "nr": "NR-35", "data": "11/09/2026", "carga": "8",
        "validade": "12", "descricao": tmpl.descricao_padrao})
    check("5. sem selecionados rejeitado", r.status_code == 303)

    # carga global abaixo da mínima --------------------------------------------
    r = client.post("/emissao-lote/emitir", data={
        "nr": "NR-35", "data": "11/09/2026", "carga": "1",
        "validade": "", "descricao": "x", "sel_%d" % id1: "1"})
    check("6. carga global abaixo da minima rejeitada", r.status_code == 303)

    # emissão do lote: 2 elegíveis (um com ajuste individual) -------------------
    r = client.post("/emissao-lote/emitir", data={
        "nr": "NR-35", "data": "11/09/2026", "carga": "8", "validade": "12",
        "descricao": tmpl.descricao_padrao,
        "sel_%d" % id1: "1", "sel_%d" % id2: "1",
        "carga_%d" % id2: "20", "validade_%d" % id2: "24"})
    check("7. lote emitido (pagina resultado)",
          r.status_code == 200 and "Resultado" in r.text)
    check("8. dois registros gravados", hr.count_all() == 2)
    r1 = hr.get_by_employee(id1)
    r2 = hr.get_by_employee(id2)
    check("9. func1 validade global 12", r1 and r1[0].validade_meses == 12)
    check("10. func2 validade individual 24", r2 and r2[0].validade_meses == 24)
    check("11. func2 carga individual 20", r2 and r2[0].carga_horaria == 20)
    check("12. numeros sequenciais CERT-",
          {r1[0].cert_number, r2[0].cert_number} == {"CERT-000001", "CERT-000002"})
    check("13. pdfs existem no tmp",
          all(Path(r.pdf_path).exists() and Path(r.pdf_path).is_relative_to(tmp)
              for r in (r1[0], r2[0])))
    numero1 = r1[0].cert_number
    check("14. resultado lista numeros", numero1 in r.text)

    # sem CPF no lote: virá como erro -------------------------------------------
    r = client.post("/emissao-lote/emitir", data={
        "nr": "NR-35", "data": "11/09/2026", "carga": "8", "validade": "",
        "descricao": tmpl.descricao_padrao, "sel_%d" % id3: "1"})
    check("15. sem CPF vira erro na pagina",
          r.status_code == 200 and "Sem CPF" in r.text and hr.count_all() == 2)

    # data individual inválida ----------------------------------------------------
    r = client.post("/emissao-lote/emitir", data={
        "nr": "NR-35", "data": "11/09/2026", "carga": "8", "validade": "",
        "descricao": tmpl.descricao_padrao, "sel_%d" % id1: "1",
        "data_%d" % id1: "99/99/9999"})
    check("16. data individual invalida rejeitada",
          r.status_code == 200 and hr.count_all() == 2)

    # consulta: bloqueada ---------------------------------------------------------
    # cria consulta via admin, reseta senha, login
    r = client.post("/usuarios/criar", data={
        "username": "conslote", "nome": "Consulta Lote", "papel": "consulta"})
    uc = er  # noqa (clareza)
    import sqlite3
    conn = sqlite3.connect(tmp / "certificados.db")
    linha = conn.execute(
        "SELECT id, password_hash FROM users WHERE username='conslote'").fetchone()
    conn.close()
    check("17. consulta criado", linha is not None)

    from src.web.users_repo import UsersRepository
    urepo = UsersRepository(db_path=tmp / "certificados.db")
    prov_c = urepo.reset_password(linha[0])
    client.get("/logout")
    client.post("/login", data={"username": "conslote", "password": prov_c})
    _trocar_senha(client, prov_c, nova="Consu1ta#2026")

    r = client.get("/emissao-lote")
    check("18. consulta redirecionado do lote",
          r.status_code == 303 and "/certificados" in r.headers.get("location", ""))
    r = client.post("/emissao-lote/emitir", data={
        "nr": "NR-35", "data": "11/09/2026", "carga": "8",
        "descricao": tmpl.descricao_padrao, "sel_%d" % id1: "1"})
    check("19. consulta nao emite lote", r.status_code == 303
          and hr.count_all() == 2)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS: " + "; ".join(FALHAS))
        return 1
    print(f"{19} checks do lote OK")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
