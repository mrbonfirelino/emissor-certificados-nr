"""Testes do Portal Fase 3 parte 1 (v1.28.0): Vencimentos + ASO no navegador.

Padrao standalone dos demais suites: roda direto `python test_web_fase3.py`.
Patches de paths ANTES de create_app (mesmo padrao test_web_fase2).
"""

import io
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import customtkinter  # noqa: F401  (import antecipado, igual as outras suites)
from PIL import Image
from fastapi.testclient import TestClient

import src.utils.paths as paths_mod
import src.core.employee_repo as er_mod
import src.core.history_repo as hr_mod
import src.core.aso_repo as aso_mod
import src.core.integracao_repo as integ_mod
import src.core.certificate_service as cert_mod
import src.web.app as app_mod

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def _png_bytes(w=120, h=160):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (30, 90, 150)).save(buf, format="PNG")
    return buf.getvalue()


def _pdf_bytes_fake(paginas=1):
    try:
        import fitz
    except Exception:
        return b"%PDF-fake"
    doc = fitz.open()
    for i in range(paginas):
        p = doc.new_page()
        p.insert_text((72, 100 + 30 * i), f"Pagina {i + 1}")
    dados = doc.tobytes()
    doc.close()
    return dados


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="webf3_"))
    tmp.mkdir(parents=True, exist_ok=True)
    paths_mod.get_data_dir = lambda: tmp
    paths_mod.get_asos_dir = lambda: tmp / "asos"
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    aso_mod.get_db_path = lambda: tmp / "certificados.db"
    integ_mod.get_db_path = lambda: tmp / "certificados.db"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA",
        empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste",
        instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ",
    )
    app_mod.get_data_dir = lambda: tmp

    from src.web.app import create_app
    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    client = TestClient(app=app, follow_redirects=False)
    return client, tmp


def _login_admin(client):
    from src.web.users_repo import UsersRepository
    users = UsersRepository(db_path=Path(client.app and str(client.app)) if False else None)
    return users


def _trocar_senha(client, atual, nova="SenhaF0rte"):
    r = client.post("/troca-senha", data={
        "atual": atual, "nova": nova, "confirma": nova})
    return r


def _login(client, username, senha):
    r = client.post("/login", data={"username": username, "password": senha})
    return r


def _login_admin_fluxo(client):
    from src.web.users_repo import UsersRepository
    users = UsersRepository()
    admin = users.get_by_username("admin")
    assert admin is not None and admin["must_change"] == 1
    prov = users.reset_password(admin["id"])
    r = _login(client, "admin", prov)
    assert r.status_code == 303 and "/troca-senha" in r.headers["location"]
    _trocar_senha(client, prov)


def main():
    print("=== test_web_fase3 — Vencimentos + ASO no portal ===")
    client, tmp = make_env()
    from src.web.users_repo import UsersRepository
    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository, CertificateRecord
    from src.core.aso_repo import AsoRepository
    from src.core.integracao_repo import IntegracaoRepository

    users = UsersRepository()
    er = EmployeeRepository()
    hr = HistoryRepository()
    aso_repo = AsoRepository()
    integ_repo = IntegracaoRepository()

    # -- login admin (bootstrap + troca obrigatoria)
    r = client.get("/login")
    check("F01 login page 200", r.status_code == 200)
    admin = users.get_by_username("admin")
    prov = users.reset_password(admin["id"])
    r = _login(client, "admin", prov)
    check("F02 login admin 303 troca-senha",
          r.status_code == 303 and "/troca-senha" in r.headers["location"])
    _trocar_senha(client, prov)

    # -- dados base: funcionarios + cert + aso + integracao
    hoje = date.today()
    e1 = er.create("Bruno Vencimentos", None, "Eletricista")
    e2 = er.create("Carla Aso", None, "Tecnica")

    rec = CertificateRecord(
        cert_number="CERT-900001", nr_code="NR-35", employee_id=e1,
        funcionario_nome="Bruno Vencimentos", funcionario_cpf="",
        data_inicio=hoje.isoformat(), data_fim=hoje.isoformat(),
        carga_horaria=8, descricao_treinamento="Trabalho em Altura",
        campos_extra="{}", pdf_path=None)
    hr.save(rec)
    aso_repo.save(aso_repo.next_aso_number(), e2, "Periódico",
                  hoje.isoformat(), 12, None)
    aso_id_vencido = aso_repo.save(
        aso_repo.next_aso_number(), e1, "Admissional",
        (hoje - timedelta(days=400)).isoformat(), 12, None)

    fab = integ_repo.add_empresa("Fábrica Teste")
    integ_repo.add_integracao(
        employee_id=e1, empresa_id=fab, tipo="Máquinas", data_inicio=None,
        data_validade=(hoje + timedelta(days=365)).isoformat())

    # -- vencimentos: pagina, cards, filtros
    r = client.get("/vencimentos")
    check("F03 /vencimentos 200", r.status_code == 200)
    corpo = r.text
    check("F04 card vencidos = 1 (ASO 400d)", ">1<" in corpo and "vencidos" in corpo.lower())
    check("F05 linha NR-35 presente", "NR-35" in corpo)
    check("F06 linha ASO presente", "Admissional" in corpo or "Periódico" in corpo or "Periodico" in corpo)
    check("F07 integracao presente", "INT-000001" in corpo)

    r = client.get("/vencimentos", params={"nr": "ASO"})
    check("F08 filtro nr=ASO",
          r.status_code == 200 and "Trabalho em Altura" not in r.text)
    r = client.get("/vencimentos", params={"periodo": "vencidos"})
    check("F09 filtro periodo=vencidos", r.status_code == 200)
    r = client.get("/vencimentos", params={"busca": "bruno"})
    check("F10 filtro busca bruno", r.status_code == 200 and "Bruno Vencimentos" in r.text)

    # -- aso: lista
    r = client.get("/aso")
    check("F11 /aso 200", r.status_code == 200)
    check("F12 aso listado na tabela", "Periódico" in r.text or "Periodico" in r.text)
    check("F13 botao novo aso (pode escrever)", "/aso/novo" in r.text)

    # -- aso: criar pelo portal
    r = client.get("/aso/novo")
    check("F14 form novo aso 200", r.status_code == 200)
    r = client.post("/aso/novo", data={
        "funcionario_id": str(e2), "tipo_aso": "Admissional",
        "data_exame": hoje.strftime("%d/%m/%Y"), "validade_meses": "24"})
    check("F15 criar aso 303", r.status_code == 303 and "/aso/" in r.headers["location"])
    novo_id = int(r.headers["location"].rsplit("/", 1)[-1])
    aso = aso_repo.get_by_id(novo_id)
    check("F16 registro gravado validade 24", aso is not None and aso["validade_meses"] == 24)
    check("F17 pdf criado no tmp", aso["pdf_path"] and Path(aso["pdf_path"]).exists())
    if aso["pdf_path"] and Path(aso["pdf_path"]).exists():
        cabe = Path(aso["pdf_path"]).read_bytes()[:5]
        check("F18 pdf real (%PDF)", cabe == b"%PDF-")

    # -- aso: ficha + pdf inline + download
    r = client.get(f"/aso/{novo_id}")
    check("F19 ficha 200", r.status_code == 200)
    r = client.get(f"/aso/{novo_id}/pdf")
    check("F20 pdf inline %PDF", r.status_code == 200 and r.content[:5] == b"%PDF-")
    check("F21 inline sem attachment",
          "attachment" not in (r.headers.get("content-disposition") or ""))
    r = client.get(f"/aso/{novo_id}/pdf/download")
    check("F22 download attachment", r.status_code == 200
          and "attachment" in (r.headers.get("content-disposition") or ""))

    # -- aso: doc upload -> rebuild embutido -> download -> remover
    doc = _pdf_bytes_fake(paginas=2)
    r = client.post(f"/aso/{novo_id}/doc",
                    files={"arquivo": ("aso_medico.pdf", doc, "application/pdf")})
    check("F23 upload doc 303 ficha", r.status_code == 303)
    aso2 = aso_repo.get_by_id(novo_id)
    check("F24 doc anexado", aso2["has_doc"] == 1)
    r = client.get(f"/aso/{novo_id}/pdf")
    check("F25 pdf embutido > 1 pagina", r.status_code == 200 and len(r.content) > len(_pdf_bytes_fake(1)))
    r = client.get(f"/aso/{novo_id}/doc")
    check("F26 download doc", r.status_code == 200 and r.content == doc)
    r = client.post(f"/aso/{novo_id}/doc/remover")
    check("F27 remover doc 303", r.status_code == 303)
    check("F28 doc removido", aso_repo.get_by_id(novo_id)["has_doc"] == 0)

    # -- validacao: carga/datas invalidas no vencimentos router nao se aplica;
    #    aso form: validade fora de faixa
    r = client.post("/aso/novo", data={
        "funcionario_id": str(e2), "tipo_aso": "Admissional",
        "data_exame": hoje.strftime("%d/%m/%Y"), "validade_meses": "500"})
    check("F29 validade 500 rejeitada (303 flash)",
          r.status_code == 303)  # volta com flash, sem gravar
    total_asos = aso_repo.count_all()
    check("F30 nada gravado com validade invalida", total_asos == 3)

    # -- consulta: so leitura
    cid, prov_c = users.create_user("maria", "Maria Consulta", "consulta")
    client.get("/logout")
    _login(client, "maria", prov_c)
    _trocar_senha(client, prov_c)
    r = client.get("/aso")
    check("F31 consulta ve /aso", r.status_code == 200)
    check("F32 consulta sem botao novo", "/aso/novo" not in r.text)
    r = client.post("/aso/novo", data={
        "funcionario_id": str(e2), "tipo_aso": "Admissional",
        "data_exame": hoje.strftime("%d/%m/%Y"), "validade_meses": "12"})
    check("F33 consulta nao cria (303 sem gravar)", r.status_code == 303)
    check("F34 nada gravado pela consulta", aso_repo.count_all() == 3)
    r = client.post(f"/aso/{novo_id}/doc",
                    files={"arquivo": ("x.png", _png_bytes(), "image/png")})
    check("F35 consulta nao anexa", r.status_code == 303
          and aso_repo.get_by_id(novo_id)["has_doc"] == 0)
    r = client.get("/vencimentos")
    check("F36 consulta ve vencimentos", r.status_code == 200)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} falha(s): {FALHAS}")
        return 1
    print("TODOS OS TESTES PASSARAM")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # erro inesperado = suite vermelha
        import traceback
        traceback.print_exc()
        print(f"ERRO: {e}")
        sys.exit(1)
