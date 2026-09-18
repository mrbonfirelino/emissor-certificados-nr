"""Testes v1.43.0: prévia de importação em arquivo (cookie < 4KB),
senha definida pelo admin, data/hora no PDF do certificado (opcional)
e propriedade do veículo (próprio/alugado) no PDF de abastecimento.

Roda direto:  python test_web_v143.py
"""

import io
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import fitz
import openpyxl
from fastapi.testclient import TestClient

import src.utils.paths as paths_mod
import src.core.employee_repo as er_mod
import src.core.history_repo as hr_mod
import src.core.aso_repo as aso_mod
import src.core.integracao_repo as integ_mod
import src.core.frota_repo as fr_mod
import src.core.presenca_repo as pres_mod
import src.core.certificate_service as cert_mod
import src.core.pptx_certificate_service as pptx_cert_mod
import src.web.users_repo as users_mod
import src.web.app as app_mod
import src.core.app_settings as settings_mod

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="test_v143_"))
    tmp.mkdir(parents=True, exist_ok=True)
    paths_mod.get_data_dir = lambda: tmp
    for m in (er_mod, hr_mod, aso_mod, integ_mod, fr_mod, pres_mod, users_mod):
        m.get_db_path = lambda: tmp / "certificados.db"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    pptx_cert_mod.get_templates_dir = lambda: tmp / "sem-pptx"
    settings_mod.SETTINGS_FILE = tmp / "app_settings.json"
    app_mod.get_data_dir = lambda: tmp
    from src.web.app import create_app
    app = create_app(db_path=tmp / "certificados.db",
                     secret_file=tmp / "secret.key")
    return tmp, app


def _login_admin(client):
    from src.web.users_repo import UsersRepository
    u = UsersRepository()
    admin = u.get_by_username("admin")
    prov = u.reset_password(admin["id"])
    client.post("/login", data={"username": "admin", "password": prov})
    client.post("/troca-senha", data={"atual": prov, "nova": "SenhaF0rte",
                                      "confirma": "SenhaF0rte"})


def _planilha(n, nome="CARLOS IMPORT", nr="NR-35", data="15/09/2026"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(("Nome", "NR", "Data"))
    for i in range(n):
        ws.append((nome, nr, data))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def main():
    tmp, app = make_env()
    client = TestClient(app, follow_redirects=False)
    _login_admin(client)

    from src.core.employee_repo import EmployeeRepository
    er = EmployeeRepository()
    emp_id = er.create("CARLOS IMPORT", "11144477735")
    check("C00 funcionario criado", emp_id is not None)

    # ---- parte 1: importacao de certificados (120 linhas) ----
    print("\n--- Importacao de certificados (prvia em arquivo) ---")
    r = client.post(
        "/importacoes/certificados",
        files={"arquivo": ("certs.xlsx", _planilha(120),
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    check("C01 preview 200", r.status_code == 200)
    check("C02 previa lista 120", "Emitir 120 certificado(s)" in r.text)
    sc = r.headers.get("set-cookie") or ""
    check(f"C03 cookie pequeno ({len(sc)}B < 2500)", 0 < len(sc) < 2500)
    r2 = client.post("/importacoes/certificados/confirmar")
    check("C04 confirmar 200", r2.status_code == 200)
    check("C05 PDFs gerados = 120", "120" in r2.text and "PDFs gerados" in r2.text)
    r3 = client.post("/importacoes/certificados/confirmar")
    check("C06 re-confirmar 303", r3.status_code == 303)
    r4 = client.get("/importacoes")
    check("C07 flash 'Nenhuma previa pendente'",
          "Nenhuma pr via pendente".replace(" ", "") in r4.text.replace(" ", "")
          or "Nenhuma prévia pendente" in r4.text)

    # ---- parte 2: definir senha do usuario ----
    print("\n--- Definir senha do usuario ---")
    from src.web.users_repo import UsersRepository
    u = UsersRepository()
    client.post("/usuarios/criar", data={
        "username": "joao", "nome": "Joao Definida", "papel": "consulta"})
    joao = u.get_by_username("joao")
    check("C08 usuario criado", joao is not None)
    r = client.post(f"/usuarios/{joao['id']}/senha",
                    data={"nova": "MinhaSenha1", "confirma": "MinhaSenha1"})
    check("C09 definir senha 303", r.status_code == 303)
    anon = TestClient(app=app, follow_redirects=False)
    r = anon.post("/login", data={"username": "joao", "password": "MinhaSenha1"})
    check("C10 login com senha definida", r.status_code == 303)
    check("C11 sem troca obrigatoria (vai p/ /)",
          (r.headers.get("location") or "") == "/")
    r = anon.post("/login", data={"username": "joao", "password": "errada"})
    check("C12 senha antiga/errada rejeitada",
          r.status_code == 200 and "inv" in r.text.lower())

    # ---- parte 3: data/hora no PDF do certificado (opcional) ----
    print("\n--- Data/hora da emissao no PDF ---")
    from src.core.app_settings import set_setting
    padrao = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")

    def emitir(data_br):
        r = client.post("/certificados/emitir", data={
            "funcionario_id": str(emp_id), "nr": "NR-10",
            "data": data_br, "carga": "8", "descricao": "Treinamento V143"})
        pdfs = sorted((tmp / "certificados").rglob("*.pdf"), key=lambda p: p.stat().st_mtime)
        return pdfs[-1] if pdfs else None

    set_setting("pdf_data_hora_emissao", True)
    pdf1 = emitir("16/09/2026")
    ok1 = False
    if pdf1:
        d = fitz.open(str(pdf1))
        txt = " ".join(p.get_text() for p in d)
        d.close()
        ok1 = bool(padrao.search(txt))
    check("C13 com opcao ativa: data/hora no PDF", ok1)

    set_setting("pdf_data_hora_emissao", False)
    pdf2 = emitir("17/09/2026")
    ok2 = True
    if pdf2:
        d = fitz.open(str(pdf2))
        txt = " ".join(p.get_text() for p in d)
        d.close()
        ok2 = not padrao.search(txt)
    check("C14 com opcao desligada: sem data/hora", ok2)

    # ---- parte 4: proprio/alugado no PDF de abastecimento ----
    print("\n--- Abastecimento: veiculo proprio/alugado ---")
    from src.core.pdf_abastecimento import gerar_pdf_abastecimento
    base = {"serial": "AB-2026-90001", "data_br": "16/09/2026",
            "combustivel": "diesel", "km": "10.000",
            "viagem_servico": "Viagem teste", "fornecedor": {"nome": "Posto X"},
            "condutor": "CARLOS IMPORT", "superior": "CHEFE", "obs": ""}
    p1 = gerar_pdf_abastecimento({**base, "veiculo": {
        "marca": "VW", "modelo": "Delivery", "placa": "ABC1D23",
        "proprio": 1, "contratante": ""}})
    d = fitz.open(str(p1))
    t1 = " ".join(pg.get_text() for pg in d)
    d.close()
    check("C15 proprio marcado", "Pr prio".replace(" ", "") in t1.replace(" ", "")
          or "Próprio" in t1)

    p2 = gerar_pdf_abastecimento({**base, "serial": "AB-2026-90002", "veiculo": {
        "marca": "Ford", "modelo": "Cargo", "placa": "XYZ9C88",
        "proprio": 0, "contratante": "LOCADORA X"}})
    d = fitz.open(str(p2))
    t2 = " ".join(pg.get_text() for pg in d)
    d.close()
    check("C16 alugado + contratante no PDF",
          "Alugado" in t2 and "LOCADORA X" in t2)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}): {', '.join(FALHAS)}")
        sys.exit(1)
    print("TESTES V143 OK")


if __name__ == "__main__":
    main()
