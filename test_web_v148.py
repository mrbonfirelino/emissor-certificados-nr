# -*- coding: utf-8 -*-
"""Testes do Portal Web — v1.47.0 (roadmap 2.34).

Padrão standalone: `python test_web_v148.py`; app FastAPI em DB tmp
(patches ANTES de create_app) + TestClient.

Cobre:
- 2.34.1 select de exceção reflete Permitir/Negar após salvar (bug do badge)
- 2.34.1 backups mais recentes primeiro (independente do nome)
- 2.34.2 fabricante/lote/descartável por item (form, ficha, repo)
- 2.34.2 badge "Devolução parcial" (lista, filtro e ficha) + total intacto
- 2.34.3 PDF da ficha com TERMO DE COMPROMISSO, Local/CNPJ, extras e
  "Devolvido: x/y (Parcial)"; gap faixa/colunas presente no layout novo
"""

import os
import re
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
    tmp = Path(tempfile.mkdtemp(prefix="webv148_"))
    tmp.mkdir(parents=True, exist_ok=True)
    import src.utils.paths as paths_mod
    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.epi_repo as epi_repo_mod
    import src.core.config as config_mod
    import src.core.backup_manager as bm_mod
    import src.web.app as app_mod

    paths_mod.get_data_dir = lambda: tmp
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    epi_repo_mod.get_db_path = lambda: tmp / "certificados.db"
    bm_mod.get_backup_dir = lambda: tmp / "backups"
    config_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Rua das Acacias, 100 - Cordeiro/RJ",
        instrutor_nome="Instrutor Teste", instrutor_registro_mte="MTE 44633/RJ")
    app_mod.get_data_dir = lambda: tmp

    from src.web.app import create_app
    from fastapi.testclient import TestClient
    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    client = TestClient(app, follow_redirects=False)
    return client, tmp


def _login_admin(client, tmp):
    txt = (tmp / "web_admin_provisorio.txt").read_text(encoding="utf-8")
    prov = [l.split(":")[1].strip() for l in txt.splitlines()
            if l.startswith("SENHA PROVISORIA")][0]
    client.post("/login", data={"username": "admin", "password": prov})
    _trocar_senha(client, prov)


def _secao_usuario(pagina, user_id):
    """Trecho do form de exceções do usuário (do form até </form>)."""
    ini = pagina.find(f'action="/usuarios/{user_id}/permissoes"')
    if ini < 0:
        return ""
    fim = pagina.find("</form>", ini)
    return pagina[ini:fim if fim > 0 else len(pagina)]


def _select(pagina, nome):
    """Trecho do <select name=...> até </select>."""
    ini = pagina.find(f'name="{nome}"')
    if ini < 0:
        return ""
    fim = pagina.find("</select>", ini)
    return pagina[ini:fim if fim > 0 else len(pagina)]


def main():
    client, tmp = make_env()
    _login_admin(client, tmp)

    from src.web.users_repo import UsersRepository
    from src.core.employee_repo import EmployeeRepository
    from src.core.epi_repo import EpiRepository
    users = UsersRepository()
    er = EmployeeRepository()
    repo = EpiRepository()

    # ---------- 2.34.1a: select de exceção reflete o estado salvo ----------
    r = client.post("/usuarios/criar", data={"username": "joao", "nome": "João",
                                             "papel": "emissor"})
    check("criar usuario joao (303)", r.status_code == 303)
    joao = users.get_by_username("joao")
    uid = joao["id"]

    pagina = client.get("/usuarios").text
    sec = _secao_usuario(pagina, uid)
    check("antes: sem selected em Permitir", 'value="1" selected' not in sec)
    check("antes: Padrão do papel aparece", ">Padrão do papel</option>" in sec)

    r = client.post(f"/usuarios/{uid}/permissoes", data={"exc_importacoes": "1"})
    check("salvar excecao permitir (303)", r.status_code == 303)
    sec = _select(_secao_usuario(client.get("/usuarios").text, uid),
                  "exc_importacoes")
    check("depois: Permitir selecionado", 'value="1" selected>Permitir' in sec)
    check("depois: Padrão não selecionado", 'value="" selected' not in sec)

    r = client.post(f"/usuarios/{uid}/permissoes", data={"exc_importacoes": "0"})
    sec = _select(_secao_usuario(client.get("/usuarios").text, uid),
                  "exc_importacoes")
    check("depois: Negar selecionado", 'value="0" selected>Negar' in sec)

    r = client.post(f"/usuarios/{uid}/permissoes", data={"exc_importacoes": ""})
    sec = _select(_secao_usuario(client.get("/usuarios").text, uid),
                  "exc_importacoes")
    check("voltar ao padrao selecionado", 'value="" selected>Padrão do papel' in sec)

    # ---------- 2.34.1b: backups mais recentes primeiro ----------
    bdir = tmp / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    nomes = [("certificados_manual_20250101_000000.db.gz", 1000),
             ("certificados_periodic_20250601_000000.db.gz", 2000),
             ("certificados_auto_20260101_000000.db.gz", 3000)]
    for nome, mtime in nomes:
        p = bdir / nome
        p.write_bytes(b"x" * 2048)
        os.utime(p, (mtime, mtime))
    pagina = client.get("/backup").text
    ordem = re.findall(r"certificados_[a-z]+_(\d{8}_\d{6})", pagina)
    check("backup mais recente primeiro (auto 2026)",
          ordem[:1] == ["20260101_000000"])
    check("backup mais antigo por ultimo (manual 2025)",
          ordem[-1:] == ["20250101_000000"])

    # ---------- 2.34.2: fabricante/lote/descartável por item ----------
    emp_id = er.create("Ana EPI", "52998224725")

    form_nova = client.get("/epi/nova").text
    check("form tem item_fab_0", 'name="item_fab_0"' in form_nova)
    check("form tem item_lote_0", 'name="item_lote_0"' in form_nova)
    check("form tem checkbox descartavel", 'name="item_desc_chk_0"' in form_nova)
    check("addLinha gera campos novos", "item_fab_'" in form_nova
          or "item_fab_' +" in form_nova.replace(" ", ""))

    r = client.post("/epi/nova", data={
        "funcionario_id": str(emp_id), "data_emissao": "23/09/2026",
        "item_ca_0": "11111", "item_desc_0": "Luva nitrílica",
        "item_qtd_0": "2", "item_fab_0": "Danny", "item_lote_0": "LT-09",
        "item_desc_chk_0": "1", "item_data_0": "23/09/2026",
        "item_ca_1": "22222", "item_desc_1": "Capacete", "item_qtd_1": "2",
        "item_data_1": "23/09/2026"})
    check("abrir ficha com extras (303)", r.status_code == 303
          and r.headers["location"].startswith("/epi/"))
    epi_id = int(r.headers["location"].rsplit("/", 1)[-1])

    ficha = repo.get_by_id(epi_id)
    it0, it1 = ficha["items"][0], ficha["items"][1]
    check("repo: fabricante gravado", it0.get("fabricante") == "Danny")
    check("repo: lote gravado", it0.get("lote") == "LT-09")
    check("repo: descartavel gravado", it0.get("descartavel") is True)
    check("repo: item sem extras fica vazio",
          it1.get("fabricante") == "" and it1.get("descartavel") is False)

    pagina = client.get(f"/epi/{epi_id}").text
    check("ficha mostra fabricante", "Fabricante: Danny" in pagina)
    check("ficha mostra lote", "Lote: LT-09" in pagina)
    check("ficha mostra badge descartavel", "Descartável" in pagina)

    # ---------- 2.34.2: badge "Devolução parcial" ----------
    r = client.post(f"/epi/{epi_id}/devolucao", data={
        "dev_modo_0": "pendente",
        "dev_modo_1": "parcial", "dev_qtd_1": "1",
        "data_devolucao": "23/09/2026"})
    check("devolucao parcial (303)", r.status_code == 303)

    pagina = client.get("/epi").text
    check("lista: badge Devolução parcial", "Devolução parcial" in pagina
          and "b-amarelo" in pagina)
    pagina_f = client.get(f"/epi/{epi_id}").text
    check("ficha: badge Devolução parcial", "Devolução parcial" in pagina_f)
    filtro = client.get("/epi", params={"status": "parcial"}).text
    check("filtro parcial acha a ficha", f"/epi/{epi_id}" in filtro)
    filtro_nao = client.get("/epi", params={"status": "devolvidos"}).text
    check("filtro devolvidos NAO acha parcial",
          f"/epi/{epi_id}" not in filtro_nao)

    # ---------- 2.34.3: PDF com TERMO + extras + parcial ----------
    ficha = repo.get_by_id(epi_id)
    pdf_path = Path(ficha["pdf_path"])
    check("pdf existe no disco", pdf_path.exists())
    import fitz
    doc = fitz.open(str(pdf_path))
    p1 = doc[0].get_text()
    check("PDF: TERMO DE COMPROMISSO", "TERMO DE COMPROMISSO" in p1)
    check("PDF: Local da empresa", "Rua das Acacias, 100 - Cordeiro/RJ" in p1)
    check("PDF: CNPJ", "11.222.333/0001-81" in p1)
    check("PDF: assinatura do termo", "li e estou ciente" in p1)
    check("PDF: fabricante no item", "Fabricante: Danny" in p1)
    check("PDF: devolvido parcial", "Devolvido: 1/2 (Parcial)" in
          "".join(doc[i].get_text() for i in range(doc.page_count)))
    check("PDF: faixa devolucao", "DEVOLUCAO DE EQUIPAMENTO" in
          "".join(doc[i].get_text() for i in range(doc.page_count)))
    doc.close()

    # devolução total continua -> badge azul "Itens devolvidos"
    r = client.post(f"/epi/{epi_id}/devolucao", data={
        "dev_modo_0": "total",
        "dev_modo_1": "total",
        "data_devolucao": "23/09/2026"})
    check("devolucao total (303)", r.status_code == 303)
    pagina = client.get("/epi").text
    check("total: badge Itens devolvidos (b-azul)", "Itens devolvidos" in pagina)
    check("parcial nao aparece mais", ">Devolução parcial</span>" not in pagina)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}):")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TESTES WEB v1.47.0 OK")


if __name__ == "__main__":
    main()
