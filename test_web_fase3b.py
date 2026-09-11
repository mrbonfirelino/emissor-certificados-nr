"""Testes do portal web — Fase 3 parte 2: EPI e Crachas (v1.29.0).

Roda standalone: python test_web_fase3b.py
Padrao dos demais testes web: patches nos modulos ANTES de create_app.
"""

import io
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import src.core.certificate_service as cert_mod
import src.core.cracha_repo as cr_mod
import src.core.badge_service as badge_mod
import src.core.employee_repo as er_mod
import src.core.epi_repo as epi_repo_mod
import src.core.history_repo as hr_mod
import src.core.aso_repo as aso_mod
import src.core.integracao_repo as integ_mod
import src.utils.paths as paths_mod
import src.web.app as app_mod
import src.web.routers.epi as epi_router_mod
import src.web.routers.crachas as crachas_router_mod


FALHAS = []


def check(nome, ok):
    print(f"[{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def _png_bytes(w=120, h=160):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (30, 60, 120)).save(buf, format="PNG")
    return buf.getvalue()


def _pdf_bytes_fake(pages=1):
    import fitz
    doc = fitz.open()
    for i in range(pages):
        p = doc.new_page()
        p.insert_text((72, 72 + 20 * i), f"Pagina {i + 1} de {pages}")
    data = doc.tobytes()
    doc.close()
    return data


def _trocar_senha(client, atual, nova="SenhaF0rte"):
    return client.post("/troca-senha", data={"atual": atual, "nova": nova, "confirma": nova})


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="webf3b_"))
    tmp.mkdir(parents=True, exist_ok=True)

    paths_mod.get_data_dir = lambda: tmp
    paths_mod.get_epis_dir = lambda: tmp / "epis"
    paths_mod.get_crachas_dir = lambda: tmp / "crachas"
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    aso_mod.get_db_path = lambda: tmp / "certificados.db"
    integ_mod.get_db_path = lambda: tmp / "certificados.db"
    cr_mod.get_db_path = lambda: tmp / "certificados.db"
    badge_mod.get_crachas_dir = lambda: tmp / "crachas"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    app_mod.get_data_dir = lambda: tmp
    # routers podem ter importado a funcao direto do paths — cobre os dois casos
    epi_router_mod.get_epis_dir = lambda: tmp / "epis"
    crachas_router_mod.get_crachas_dir = lambda: tmp / "crachas"

    from src.web.app import create_app
    from fastapi.testclient import TestClient
    app = create_app(db_path=tmp / "certificados.db", secret_file=tmp / "secret.key")
    client = TestClient(app=app, follow_redirects=False)
    return client, tmp


def main():
    client, tmp = make_env()
    from src.core.employee_repo import EmployeeRepository
    from src.core.epi_repo import EpiRepository
    from src.core.cracha_repo import CrachaRepository
    from src.core.history_repo import HistoryRepository, CertificateRecord
    from src.core.aso_repo import AsoRepository
    from src.web.users_repo import UsersRepository

    er = EmployeeRepository()
    epi_repo = EpiRepository()
    cr_repo = CrachaRepository()
    hr = HistoryRepository()
    aso_repo = AsoRepository()
    users = UsersRepository()
    hoje = date.today()
    hoje_br = hoje.strftime("%d/%m/%Y")
    hoje_iso = hoje.isoformat()

    # ── login admin (bootstrap + troca obrigatoria) ──────────────
    r = client.get("/login")
    check("L01 login form 200", r.status_code == 200)
    admin = users.get_by_username("admin")
    check("L02 admin must_change", admin is not None and admin["must_change"] == 1)
    prov = users.reset_password(admin["id"])
    r = client.post("/login", data={"username": "admin", "password": prov})
    check("L03 login 303 troca-senha", r.status_code == 303 and "/troca-senha" in r.headers["location"])
    r = _trocar_senha(client, prov)
    check("L04 troca senha 303 /", r.status_code == 303 and r.headers["location"] == "/")

    # ── dados base ───────────────────────────────────────────────
    # er.create devolve o id (int) do funcionario
    e1 = er.create("Ana Epi", "529.982.247-25", "Eletricista")
    e2 = er.create("Bruno Cracha", "529.982.247-25", "Mecanico")
    foto = _png_bytes()
    e3 = er.create("Carla Epi", "390.533.447-05", "Soldador", foto=foto)
    # cracha: A/B elegiveis (foto+NR+ASO), C sem foto (bloqueado)
    eA = er.create("Alice Cracha", "123.456.789-09", "Operador", foto=foto)
    eB = er.create("Bruno Elegivel", "987.654.321-00", "Eletricista", foto=foto)
    eC = er.create("Carlos SemFoto", "111.444.777-35", "Auxiliar")  # sem foto
    hr.save(CertificateRecord(
        cert_number="CERT-900101", nr_code="NR-35", employee_id=eA,
        funcionario_nome="Alice Cracha", funcionario_cpf="123.456.789-09",
        data_inicio=hoje_iso, data_fim=hoje_iso, carga_horaria=8,
        descricao_treinamento="Trabalho em Altura", campos_extra="{}"))
    hr.save(CertificateRecord(
        cert_number="CERT-900102", nr_code="NR-12", employee_id=eB,
        funcionario_nome="Bruno Elegivel", funcionario_cpf="987.654.321-00",
        data_inicio=hoje_iso, data_fim=hoje_iso, carga_horaria=8,
        descricao_treinamento="Maquinas", campos_extra="{}"))
    hr.save(CertificateRecord(
        cert_number="CERT-900103", nr_code="NR-35", employee_id=eC,
        funcionario_nome="Carlos SemFoto", funcionario_cpf="111.444.777-35",
        data_inicio=hoje_iso, data_fim=hoje_iso, carga_horaria=8,
        descricao_treinamento="Trabalho em Altura", campos_extra="{}"))
    aso_repo.save(aso_repo.next_aso_number(), eA, "Periódico", hoje_iso, 12)
    aso_repo.save(aso_repo.next_aso_number(), eB, "Admissional", hoje_iso, 12)
    aso_repo.save(aso_repo.next_aso_number(), eC, "Periódico", hoje_iso, 12)

    # ── EPI: listar + criar ficha ────────────────────────────────
    check("E01 /epi 200", client.get("/epi").status_code == 200)
    check("E02 /epi/nova 200", client.get("/epi/nova").status_code == 200)
    r = client.post("/epi/nova", data={
        "funcionario_id": str(e1),
        "item_ca_0": "CA 12345", "item_desc_0": "Luva nitrilica",
        "item_qtd_0": "5", "item_data_0": hoje_br,
        "data_emissao": hoje_br})
    check("E03 criar ficha 303 /epi/{id}", r.status_code == 303 and "/epi/" in r.headers.get("location", ""))
    fichas = epi_repo.get_by_employee(e1)
    check("E04 registro gravado", len(fichas) == 1 and fichas[0]["epi_number"] == "EPI-000001")
    ficha = epi_repo.get_by_id(fichas[0]["id"])
    check("E05 status aberto", ficha["status"] == "aberto")
    check("E06 pdf existe %PDF", ficha["pdf_path"] and Path(ficha["pdf_path"]).exists()
          and Path(ficha["pdf_path"]).read_bytes()[:4] == b"%PDF")
    eid = ficha["id"]
    r = client.get(f"/epi/{eid}")
    check("E07 ficha 200 com item", r.status_code == 200 and "Luva nitrilica" in r.text)

    # ── EPI: devolucao parcial + termo ───────────────────────────
    r = client.post(f"/epi/{eid}/devolucao", data={
        "dev_modo_0": "parcial", "dev_qtd_0": "2", "data_devolucao": hoje_br})
    check("E08 devolucao 303", r.status_code == 303)
    ficha = epi_repo.get_by_id(eid)
    it = ficha["items"][0]
    check("E09 item parcial gravado", it["dev_quantidade"] == "2" and it["dev_data"] == hoje_iso)
    termo = list((tmp / "epis").rglob("Devolucao -*.pdf"))
    check("E10 termo devolucao existe", len(termo) == 1 and termo[0].read_bytes()[:4] == b"%PDF")

    # ── EPI: pdf ver/baixar, status, anexos ──────────────────────
    r = client.get(f"/epi/{eid}/pdf")
    check("E11 pdf inline", r.status_code == 200 and r.content[:4] == b"%PDF"
          and "attachment" not in r.headers.get("content-disposition", ""))
    r = client.get(f"/epi/{eid}/pdf/download")
    check("E12 pdf download attachment", r.status_code == 200
          and "attachment" in r.headers.get("content-disposition", ""))
    r = client.post(f"/epi/{eid}/status")
    check("E13 fechar ficha", epi_repo.get_by_id(eid)["status"] == "fechado")
    r = client.post(f"/epi/{eid}/status")
    check("E14 reabrir ficha", epi_repo.get_by_id(eid)["status"] == "aberto")
    r = client.post(f"/epi/{eid}/doc", files={"arquivo": ("contrato.txt", b"conteudo do anexo", "text/plain")})
    check("E15 anexo upload 303", r.status_code == 303)
    docs = epi_repo.list_docs(eid)
    check("E16 anexo listado", len(docs) == 1)
    doc_id = docs[0]["id"]
    r = client.get(f"/epi/{eid}/doc/{doc_id}")
    check("E17 anexo download bytes", r.status_code == 200 and r.content == b"conteudo do anexo")
    r = client.post(f"/epi/{eid}/doc/{doc_id}/excluir")
    check("E18 anexo excluido", len(epi_repo.list_docs(eid)) == 0)

    # ── Crachas: lista + novo + emitir lote ──────────────────────
    check("C01 /crachas 200", client.get("/crachas").status_code == 200)
    r = client.get("/crachas/novo")
    check("C02 /crachas/novo 200", r.status_code == 200)
    check("C03 novo lista elegiveis", "Alice Cracha" in r.text and "Bruno Elegivel" in r.text)
    check("C04 novo bloqueia sem foto", "BLOQUEADO" in r.text and "Carlos SemFoto" in r.text
          and "sem foto" in r.text)
    r = client.post("/crachas/emitir", data={
        "template_code": "CRACHA-ALTEC", "tamanho": "real",
        "data_emissao": hoje_br, f"sel_{eA}": "on", f"sel_{eB}": "on"})
    check("C05 emitir 200 resultado", r.status_code == 200 and "emitidos" in r.text.lower())
    check("C06 2 crachas gravados", cr_repo.count_all() == 2)
    nums = sorted(c["cracha_number"] for c in cr_repo.get_all(500))
    check("C07 numeros sequenciais", nums == ["CRACHA-000001", "CRACHA-000002"])
    lotes = list((tmp / "crachas").rglob("CRACHAS_*.pdf"))
    check("C08 lote A4 existe %PDF", len(lotes) == 1 and lotes[0].read_bytes()[:4] == b"%PDF")
    numA = [c for c in cr_repo.get_all(500) if c["employee_id"] == eA][0]["cracha_number"]
    r = client.get(f"/crachas/{numA}/pdf")
    check("C09 pdf individual inline", r.status_code == 200 and r.content[:4] == b"%PDF")
    r = client.get("/crachas/baixar/0")
    check("C10 baixar lote por sessao", r.status_code == 200 and r.content[:4] == b"%PDF")

    # ── consulta (maria): leitura apenas ─────────────────────────
    users.create_user("maria", "Maria Consulta", "consulta")
    m = users.get_by_username("maria")
    mprov = users.reset_password(m["id"])
    client.get("/logout")
    client.post("/login", data={"username": "maria", "password": mprov})
    _trocar_senha(client, mprov)
    check("M01 maria ve /epi", client.get("/epi").status_code == 200)
    check("M02 maria ve /crachas", client.get("/crachas").status_code == 200)
    r = client.post("/epi/nova", data={
        "funcionario_id": str(e2), "item_ca_0": "X", "item_desc_0": "Y",
        "item_qtd_0": "1", "item_data_0": hoje_br, "data_emissao": hoje_br})
    check("M03 maria nao cria ficha", r.status_code == 303 and len(epi_repo.get_by_employee(e2)) == 0)
    antes = cr_repo.count_all()
    r = client.post("/crachas/emitir", data={
        "template_code": "CRACHA-ALTEC", "tamanho": "real",
        "data_emissao": hoje_br, f"sel_{eA}": "on"})
    check("M04 maria nao emite cracha", r.status_code == 303 and cr_repo.count_all() == antes)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS: " + "; ".join(FALHAS))
        sys.exit(1)
    print("TESTES WEB FASE 3B OK")
    sys.exit(0)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    main()
