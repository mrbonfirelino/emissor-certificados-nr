"""Testes do Portal Web — Fase 2 (funcionarios, certificados, historico).

Padrao standalone: roda com `python test_web_fase2.py`; cria app FastAPI em
DB tmp (patches ANTES de create_app) e exercita as rotas com TestClient.
"""

import io
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

FALHAS = []


def check(nome, ok):
    print(f"[{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def _png_bytes(w=120, h=160):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (40, 80, 140)).save(buf, format="PNG")
    return buf.getvalue()


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="webf2_"))
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


def _trocar_senha(client, atual, nova="SenhaF0rte"):
    r = client.post("/troca-senha", data={"atual": atual, "nova": nova,
                                          "confirma": nova})
    return r


def main():
    client, tmp, (er_mod, hr_mod) = make_env()
    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository
    from src.core.template_loader import load_all_templates
    from src.web.users_repo import UsersRepository
    er = EmployeeRepository()
    hr = HistoryRepository()
    users = UsersRepository()

    # login inicial do admin (bootstrap) -----------------------------------
    check("1. login form acessivel", client.get("/login").status_code == 200)
    admin = users.get_by_username("admin")
    check("2. admin bootstrapado com troca pendente",
          admin is not None and admin["must_change"] == 1)
    client.post("/login", data={"username": "admin",
                                "password": admin["password_hash"]})
    # senha provisoria real: usar reset para conhecida
    prov = users.reset_password(admin["id"])
    client.post("/login", data={"username": "admin", "password": prov})
    check("3. admin logado -> troca-senha",
          client.get("/", follow_redirects=False).status_code in (200, 303))
    _trocar_senha(client, prov)

    # nav da fase 2
    r = client.get("/")
    nav_ok = all(x in r.text for x in (">Certificados<", ">Funcionários<",
                                       ">Histórico<"))
    check("4. nav mostra modulos da fase 2", r.status_code == 200 and nav_ok)

    # criar funcionario -----------------------------------------------------
    r = client.post("/funcionarios/novo", data={
        "nome": "Maria da Silva", "cpf": "529.982.247-25", "funcao": "Operadora",
        "telefone": "21984209236", "nascimento": "01/01/1990",
        "admissao": "10/03/2020", "tipo": "O+", "ctps": "123456",
        "ear": "on"})
    check("5. criar funcionario (303 ficha)",
          r.status_code == 303 and "/funcionarios/" in r.headers["location"])
    emp_id = int(r.headers["location"].rsplit("/", 1)[-1])
    r = client.get(f"/funcionarios/{emp_id}")
    check("6. ficha mostra dados", r.status_code == 200
          and "Maria da Silva" in r.text and "Documentos" in r.text)

    # cpf invalido rejeitado
    r = client.post("/funcionarios/novo", data={"nome": "CPF Ruim",
                                                "cpf": "111.111.111-11"})
    check("7. cpf invalido rejeitado", r.status_code == 303
          and er.count_search("CPF Ruim") == 0)

    # editar ----------------------------------------------------------------
    r = client.post(f"/funcionarios/{emp_id}/editar", data={
        "nome": "Maria da Silva Sauro", "cpf": "529.982.247-25",
        "funcao": "Operadora Senior", "telefone": "21984209236",
        "nascimento": "01/01/1990", "admissao": "10/03/2020",
        "tipo": "O+", "ctps": "123456", "ear": "on"})
    r = client.get(f"/funcionarios/{emp_id}")
    check("8. edicao persiste", r.status_code == 200
          and "Maria da Silva Sauro" in r.text)

    # foto ------------------------------------------------------------------
    r = client.post(f"/funcionarios/{emp_id}/editar", data={
        "nome": "Maria da Silva Sauro", "cpf": "529.982.247-25",
        "funcao": "Operadora Senior"}, files={
        "foto": ("foto.png", _png_bytes(), "image/png")})
    r = client.get(f"/funcionarios/{emp_id}/foto")
    check("9. foto upload + serve imagem", r.status_code == 200
          and r.headers["content-type"].startswith("image/")
          and len(r.content) > 100)

    # documentos ------------------------------------------------------------
    r = client.post(f"/funcionarios/{emp_id}/docs", files={
        "arquivo": ("exame.txt", b"laudo fake", "text/plain")})
    docs = er.list_docs(emp_id)
    check("10. doc upload (txt aceito)", r.status_code == 303 and len(docs) == 1)
    r = client.get(f"/funcionarios/{emp_id}/docs/{docs[0]['id']}/download")
    check("11. doc download", r.status_code == 200 and r.content == b"laudo fake")
    antes = len(er.list_docs(emp_id))
    client.post(f"/funcionarios/{emp_id}/docs", files={
        "arquivo": ("mal.exe", b"MZfake", "application/x-msdownload")})
    check("12. exe bloqueado", len(er.list_docs(emp_id)) == antes)
    client.post(f"/funcionarios/{emp_id}/docs/{docs[0]['id']}/excluir")
    r = client.get(f"/funcionarios/{emp_id}/docs/{docs[0]['id']}/download")
    check("13. doc excluido (404)", r.status_code == 404)

    # emissor ---------------------------------------------------------------
    eid, prov_e = users.create_user("emissor1", "Emissor Um", "emissor")
    client.get("/logout")
    client.post("/login", data={"username": "emissor1", "password": prov_e})
    _trocar_senha(client, prov_e)
    check("14. emissor ve formulario de emissao",
          client.get("/certificados").status_code == 200)

    # emitir certificado pelo navegador -------------------------------------
    tmpl = load_all_templates()["NR-35"]
    r = client.post("/certificados/emitir", data={
        "funcionario_id": emp_id, "nr": "NR-35", "data": "11/09/2026",
        "carga": str(tmpl.carga_horaria_minima), "validade": "12",
        "descricao": tmpl.descricao_padrao})
    numero = "CERT-000001"
    check("15. emitir -> redirect detalhe",
          r.status_code == 303 and numero in r.headers.get("location", ""))
    check("16. registro gravado", hr.count_all() == 1)
    record = hr.get_by_number(numero)
    check("17. registro com validade override + pdf no tmp",
          record is not None and record.validade_meses == 12
          and record.pdf_path and Path(record.pdf_path).exists())
    r = client.get(f"/certificados/{numero}")
    check("18. pagina de detalhe", r.status_code == 200
          and "Baixar PDF" in r.text)
    r = client.get(f"/certificados/{numero}/pdf")
    check("19. download pdf", r.status_code == 200
          and r.content[:5] == b"%PDF-")

    # carga abaixo da minima rejeitada
    r = client.post("/certificados/emitir", data={
        "funcionario_id": emp_id, "nr": "NR-35", "data": "11/09/2026",
        "carga": "1", "validade": "", "descricao": "x"})
    check("20. carga abaixo da minima rejeitada",
          r.status_code == 303 and hr.count_all() == 1)

    # historico com filtros ---------------------------------------------------
    r = client.get("/historico")
    check("21. historico lista", r.status_code == 200 and numero in r.text)
    r = client.get("/historico", params={"nr": "NR-35"})
    check("22. filtro NR", r.status_code == 200 and numero in r.text)
    r = client.get("/historico", params={"nr": "NR-10"})
    check("23. filtro NR sem resultado", r.status_code == 200
          and numero not in r.text)
    r = client.get("/historico", params={"de": "01/01/2020",
                                         "ate": "31/12/2026"})
    check("24. filtro periodo", r.status_code == 200 and numero in r.text)

    # documento assinado -------------------------------------------------------
    r = client.post(f"/historico/{numero}/assinado", files={
        "arquivo": ("assinado.png", _png_bytes(), "image/png")})
    check("25. anexar assinado", r.status_code == 303
          and hr.get_signed_doc(record.id) is not None)
    r = client.get(f"/historico/{numero}/assinado")
    check("26. baixar assinado", r.status_code == 200
          and r.headers["content-type"].startswith("image/"))
    r = client.get("/historico", params={"assinado": "sim"})
    check("27. filtro assinado=sim", r.status_code == 200 and numero in r.text)
    client.post(f"/historico/{numero}/assinado/remover")
    r = client.get(f"/historico/{numero}/assinado")
    check("28. remover assinado (404)", r.status_code == 404)

    # consulta: somente leitura ------------------------------------------------
    cid, prov_c = users.create_user("consulta1", "Consulta Um", "consulta")
    hr.attach_signed_doc(record.id, _png_bytes(), "png")  # repõe para o teste 32
    client.get("/logout")
    client.post("/login", data={"username": "consulta1", "password": prov_c})
    _trocar_senha(client, prov_c)
    check("29. consulta ve listas",
          client.get("/funcionarios").status_code == 200
          and client.get("/historico").status_code == 200
          and client.get("/certificados").status_code == 200)
    r = client.post("/certificados/emitir", data={
        "funcionario_id": emp_id, "nr": "NR-35", "data": "11/09/2026",
        "carga": "16", "validade": "", "descricao": "x"})
    check("30. consulta nao emite", r.status_code == 303
          and hr.count_all() == 1)
    r = client.post(f"/funcionarios/{emp_id}/docs", files={
        "arquivo": ("x.txt", b"x", "text/plain")})
    check("31. consulta nao anexa doc", len(er.list_docs(emp_id)) == 0)
    r = client.post(f"/historico/{numero}/assinado/remover")
    check("32. consulta nao remove assinado", r.status_code == 303
          and hr.get_signed_doc(record.id) is not None)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS: {FALHAS}")
        sys.exit(1)
    print(f"32/32 testes OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    main()
