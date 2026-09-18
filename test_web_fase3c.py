"""Testes Web — Fase 3C: Cartões de bloqueio, Importações e Integrações.

Standalone: python test_web_fase3c.py
Mesmo padrão de test_web_fase3b.py (patches de paths ANTES do create_app).
"""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

FALHAS = []


def check(nome, ok):
    print(f"[{'OK ' if ok else 'FALHA'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def _png_bytes():
    import struct
    import zlib
    def chunk(tipo, dados):
        c = tipo + dados
        return struct.pack(">I", len(dados)) + c + struct.pack(">I", zlib.crc32(c))
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def _xlsx(tmp, nome, linhas):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    for linha in linhas:
        ws.append(linha)
    caminho = tmp / nome
    wb.save(caminho)
    return caminho


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="web_fase3c_"))
    (tmp / "cartoes").mkdir()
    (tmp / "certificados").mkdir()

    import src.utils.paths as paths_mod
    paths_mod.get_data_dir = lambda: tmp
    paths_mod.get_cartoes_dir = lambda: tmp / "cartoes"

    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.aso_repo as aso_mod
    import src.core.integracao_repo as integ_mod
    import src.core.certificate_service as cert_mod
    for mod in (er_mod, hr_mod, aso_mod, integ_mod):
        mod.get_db_path = lambda: tmp / "certificados.db"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")

    import src.web.app as app_mod
    app_mod.get_data_dir = lambda: tmp
    import src.web.routers.cartoes as cartoes_mod
    cartoes_mod.get_cartoes_dir = lambda: tmp / "cartoes"

    from src.web.app import create_app
    from fastapi.testclient import TestClient
    app = create_app(db_path=tmp / "certificados.db", secret_file=tmp / "secret.key")
    client = TestClient(app=app, follow_redirects=False)
    return client, tmp


def _trocar_senha(client, atual, nova="SenhaF0rte"):
    return client.post("/troca-senha", data={
        "atual": atual, "nova": nova, "confirma": nova})


def _login_admin(client, users):
    admin = users.get_by_username("admin")
    prov = users.reset_password(admin["id"])
    client.post("/login", data={"username": "admin", "password": prov})
    _trocar_senha(client, prov)


def main():
    client, tmp = make_env()
    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository, CertificateRecord
    from src.core.aso_repo import AsoRepository
    from src.core.integracao_repo import IntegracaoRepository
    from src.web.users_repo import UsersRepository

    er = EmployeeRepository()
    hr = HistoryRepository()
    aso_repo = AsoRepository()
    integ = IntegracaoRepository()
    users = UsersRepository()
    hoje = date.today()
    hoje_iso = hoje.isoformat()

    _login_admin(client, users)

    # ── dados base ───────────────────────────────────────────────
    foto = _png_bytes()
    eFoto = er.create("Danilo Cartao", "529.982.247-25", "Operador",
                      foto=foto, telefone="21984209236")
    eSimples = er.create("Elisa Simples", "390.533.447-05", "Auxiliar")
    check("B01 funcionarios criados", eFoto is not None and eSimples is not None)

    from src.core.blocking_card_service import load_card_templates
    tpls = load_card_templates()
    t_json = next(t for t in tpls.values()
                  if t.get("template_type") in (None, "json")
                  and "CRACHA" not in str(t.get("card_code", "")).upper())
    t_pptx = next((t for t in tpls.values()
                   if t.get("template_type") == "pptx"
                   and "MATRICULA" in set(t.get("used_fields") or [])), None)

    # ── CARTÕES: lista, formulário, emissão JSON ─────────────────
    r = client.get("/cartoes")
    check("CA01 /cartoes 200", r.status_code == 200)
    r = client.get("/cartoes/novo")
    check("CA02 /cartoes/novo 200 com modelos", r.status_code == 200
          and "Modelo do cartão" in r.text and "Danilo Cartao" in r.text)

    r = client.post("/cartoes/emitir", data={
        "template_code": t_json["card_code"], "saida": "folha",
        f"sel_{eFoto}": "on", f"matricula_{eFoto}": "123",
        f"papel_{eFoto}": "LIDER"})
    check("CA03 emissao JSON 200 resultado", r.status_code == 200
          and "PDF" in r.text)
    lotes = list((tmp / "cartoes" / "LOTES").rglob("CARTOES_*.pdf"))
    check("CA04 lote %PDF em LOTES", len(lotes) == 1
          and lotes[0].read_bytes()[:4] == b"%PDF")
    rel = lotes[0].relative_to(tmp / "cartoes").as_posix()
    r = client.get(f"/cartoes/pdf?rel={rel}")
    check("CA05 ver pdf inline", r.status_code == 200 and r.content[:4] == b"%PDF"
          and "attachment" not in r.headers.get("content-disposition", ""))
    r = client.get(f"/cartoes/pdf/download?rel={rel}")
    check("CA06 baixar pdf attachment", r.status_code == 200
          and "attachment" in r.headers.get("content-disposition", ""))
    r = client.get("/cartoes/pdf?rel=..%2Fsecret.key")
    check("CA07 traversal bloqueado", r.status_code == 404)
    r = client.post("/cartoes/emitir", data={"template_code": t_json["card_code"]})
    check("CA08 sem selecao 303", r.status_code == 303)
    r = client.get("/cartoes")
    check("CA09 lista mostra o lote", "LOTES" in r.text and "CARTOES_" in r.text)

    if t_pptx is not None:
        r = client.post("/cartoes/emitir", data={
            "template_code": t_pptx["card_code"], f"sel_{eFoto}": "on"})
        check("CA10 pptx exige matricula", r.status_code == 303
              and "Matrícula" in client.get("/cartoes/novo").text)

    # ── INTEGRAÇÕES ──────────────────────────────────────────────
    r = client.get("/integracoes")
    check("I01 /integracoes 200", r.status_code == 200)
    r = client.post("/empresas/criar", data={"nome": "Fábrica Teste",
                                             "cnpj": "12.345.678/0001-95"})
    check("I02 criar empresa 303", r.status_code == 303)
    empresas = integ.list_empresas()
    check("I03 empresa gravada", len(empresas) == 1
          and empresas[0]["nome"] == "Fábrica Teste")
    client.post("/empresas/criar", data={"nome": "fábrica teste"})
    check("I04 empresa duplicada rejeitada", len(integ.list_empresas()) == 1)
    client.get("/empresas")  # consome flash de erro antes do GET do formulário
    r = client.get("/integracoes/novo")
    check("I05 /integracoes/novo 200", r.status_code == 200
          and "Fábrica Teste" in r.text and "Danilo Cartao" in r.text)
    emp_id = empresas[0]["id"]
    r = client.post("/integracoes/novo", data={
        "employee_id": str(eSimples), "empresa_id": str(emp_id),
        "tipo": "Máquinas", "data_inicio": hoje_iso,
        "data_validade": (hoje + timedelta(days=365)).isoformat(),
        "obs": "linha 1"})
    check("I06 criar integracao 303", r.status_code == 303
          and integ.count_all() == 1)
    iid = integ.get_all(10)[0]["id"]
    r = client.get("/integracoes")
    check("I07 lista mostra Em dia", r.status_code == 200
          and "Em dia" in r.text and "Máquinas" in r.text)
    r = client.post("/integracoes/novo", data={
        "employee_id": str(eSimples), "empresa_id": str(emp_id),
        "tipo": "X", "data_inicio": hoje_iso, "data_validade": ""})
    check("I08 validade obrigatoria", r.status_code == 303
          and integ.count_all() == 1)
    client.get("/integracoes")  # consome flash de erro antes do GET do formulário
    r = client.get(f"/integracoes/{iid}/editar")
    check("I09 form editar 200", r.status_code == 200
          and "Máquinas" in r.text)
    r = client.post(f"/integracoes/{iid}/editar", data={
        "employee_id": str(eSimples), "empresa_id": str(emp_id),
        "tipo": "Assistência técnica", "data_inicio": hoje_iso,
        "data_validade": (hoje + timedelta(days=365)).isoformat()})
    check("I10 editar salva", r.status_code == 303
          and integ.get_by_id(iid)["tipo"] == "Assistência técnica")

    # status vencido
    integ.add_integracao(eSimples, emp_id, "Curta",
                         (hoje - timedelta(days=30)).isoformat(),
                         (hoje - timedelta(days=1)).isoformat())
    r = client.get("/integracoes")
    check("I11 status vencida", "Vencida" in r.text)

    r = client.post(f"/integracoes/{iid}/excluir")
    check("I12 excluir integracao", r.status_code == 303
          and integ.count_all() == 1)
    restante = integ.get_all(10)[0]["id"]
    client.post("/empresas/criar", data={"nome": "Segunda Empresa"})
    seg_id = [e for e in integ.list_empresas()
              if e["nome"] == "Segunda Empresa"][0]["id"]
    r = client.post(f"/empresas/{seg_id}/excluir")
    check("I13 excluir empresa sem uso", r.status_code == 303
          and integ.get_empresa(seg_id) is None)
    r = client.post(f"/empresas/{emp_id}/excluir")
    check("I14 empresa com integracao protegida",
          r.status_code == 303 and integ.get_empresa(emp_id) is not None)
    client.post(f"/integracoes/{restante}/excluir")
    client.post(f"/empresas/{emp_id}/excluir")
    check("I15 excluir apos limpar", integ.get_empresa(emp_id) is None)

    # ── IMPORTAÇÕES ──────────────────────────────────────────────
    r = client.get("/importacoes")
    check("IM01 /importacoes 200", r.status_code == 200
          and "Funcionários" in r.text and "Modelos" in r.text)
    r = client.get("/importacoes/modelo/funcionarios")
    check("IM02 modelo xlsx download", r.status_code == 200
          and r.content[:2] == b"PK")
    r = client.get("/importacoes/modelo/leiame")
    check("IM03 modelo leiame download", r.status_code == 200
          and "text/plain" in r.headers.get("content-type", ""))
    r = client.get("/importacoes/modelo/inexistente")
    check("IM04 slug invalido 404", r.status_code == 404)

    plan = _xlsx(tmp, "func.xlsx", [
        ["Nome", "CPF", "Função", "Telefone", "Nascimento", "Tipo Sanguíneo",
         "Admissão", "CTPS", "CNH EAR"],
        ["Fabio Importado", "111.444.777-35", "Soldador", "21984209236",
         "01/02/1990", "O+", "01/03/2020", "123456", "Sim"],
        ["Gilda Importada", "123.456.789-09", "Auxiliar", "", "", "", "", "", ""],
        ["", "000.000.000-00", "Erro", "", "", "", "", "", ""],
    ])
    antes = len(er.get_all(limit=100000))
    with open(plan, "rb") as f:
        r = client.post("/importacoes/funcionarios",
                        files={"arquivo": ("func.xlsx", f.read(),
                                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    depois = len(er.get_all(limit=100000))
    check("IM05 importar funcionarios", r.status_code == 200
          and "Importados" in r.text and depois - antes == 2)

    hr.save(CertificateRecord(
        cert_number="CERT-900201", nr_code="NR-35", employee_id=eSimples,
        funcionario_nome="Elisa Simples", funcionario_cpf="390.533.447-05",
        data_inicio=hoje_iso, data_fim=hoje_iso, carga_horaria=8,
        descricao_treinamento="Trabalho em Altura", campos_extra="{}"))
    plan = _xlsx(tmp, "certs.xlsx", [
        ["Nome", "NR", "Data"],
        ["Elisa Simples", "NR-35", hoje.strftime("%d/%m/%Y")],
        ["Hugo Sem CPF", "NR-12", hoje.strftime("%d/%m/%Y")],
        ["Sem Data", "NR-35", "texto"],
    ])
    with open(plan, "rb") as f:
        r = client.post("/importacoes/certificados",
                        files={"arquivo": ("certs.xlsx", f.read(),
                                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    check("IM06 previa certificados", r.status_code == 200
          and "Elisa Simples" in r.text and "Hugo Sem CPF" in r.text
          and "criados automaticamente" in r.text)
    r = client.post("/importacoes/certificados/confirmar")
    check("IM07 confirmar gera lote", r.status_code == 200
          and "PDFs gerados" in r.text)
    pdfs = list((tmp / "certificados").rglob("*.pdf"))
    check("IM08 pdf do lote existe", len(pdfs) >= 1
          and pdfs[0].read_bytes()[:4] == b"%PDF")
    r = client.post("/importacoes/certificados/confirmar")
    check("IM09 confirmar sem previa 303", r.status_code == 303)

    plan = _xlsx(tmp, "asos.xlsx", [
        ["Nome", "CPF", "Tipo", "Data Exame", "Validade (meses)"],
        ["Elisa Simples", "390.533.447-05", "P", hoje.strftime("%d/%m/%Y"), 12],
        ["Nome Inexistente", "", "A", hoje.strftime("%d/%m/%Y"), ""],
    ])
    qtd_aso = aso_repo.count_all() if hasattr(aso_repo, "count_all") else None
    with open(plan, "rb") as f:
        r = client.post("/importacoes/asos",
                        files={"arquivo": ("asos.xlsx", f.read(),
                                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    check("IM10 importar asos", r.status_code == 200
          and "ASOs criados" in r.text and "Nome Inexistente" in r.text)

    plan = _xlsx(tmp, "bloqueio.xlsx", [
        ["Nome", "CPF"],
        ["Danilo Cartao", "529.982.247-25"],
        ["Fulano Ausente", "999.999.999-99"],
    ])
    with open(plan, "rb") as f:
        r = client.post("/importacoes/cartoes",
                        files={"arquivo": ("bloqueio.xlsx", f.read(),
                                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    check("IM11 bloqueio redireciona com sel", r.status_code == 303
          and f"sel={eFoto}" in r.headers.get("location", ""))
    r = client.get(f"/cartoes/novo?sel={eFoto}")
    check("IM12 cartoes/novo pre-selecionado", r.status_code == 200
          and "checked" in r.text)

    plano = _xlsx(tmp, "invalido.txt", [["x"]])
    with open(plano, "rb") as f:
        r = client.post("/importacoes/funcionarios",
                        files={"arquivo": ("invalido.txt", f.read(), "text/plain")})
    check("IM13 extensao invalida 303", r.status_code == 303)

    # ── consulta (maria): leitura apenas nos 3 módulos novos ─────
    users.create_user("maria", "Maria Consulta", "consulta")
    m = users.get_by_username("maria")
    mprov = users.reset_password(m["id"])
    client.get("/logout")
    client.post("/login", data={"username": "maria", "password": mprov})
    _trocar_senha(client, mprov)
    check("P01 maria /cartoes 303", client.get("/cartoes").status_code == 303)
    check("P02 maria /integracoes 303", client.get("/integracoes").status_code == 303)
    check("P03 maria /importacoes 303", client.get("/importacoes").status_code == 303)
    r = client.post("/empresas/criar", data={"nome": "Hack Corp"})
    check("P04 maria nao cria empresa", r.status_code == 303
          and all(e["nome"] != "Hack Corp" for e in integ.list_empresas()))
    r = client.post("/importacoes/certificados/confirmar")
    check("P05 maria nao confirma lote", r.status_code == 303)
    nav = client.get("/").text
    check("P06 menu sem modulos restritos",
          "Cartões" not in nav and "Integrações" not in nav
          and "Importações" not in nav)

    client.get("/logout")
    _login_admin(client, users)
    nav = client.get("/").text
    check("P07 menu admin com modulos novos",
          "/cartoes" in nav and "/integracoes" in nav and "/importacoes" in nav)

    # ── regressão: /funcionarios/novo não pode cair na rota {emp_id} ──
    r = client.get("/funcionarios/novo")
    check("RG01 GET /funcionarios/novo 200", r.status_code == 200
          and "int_parsing" not in r.text and "Novo funcion" in r.text)

    # ── cartões: campos condicionais por modelo ───────────────────
    r = client.get("/cartoes/novo")
    check("RG02 cartoes/novo flags por modelo", r.status_code == 200
          and "data-usa-setor" in r.text and "data-usa-papel" in r.text
          and "data-usa-matricula" in r.text)
    check("RG03 cartoes/novo classes condicionais", r.status_code == 200
          and "col-matricula" in r.text and "col-papel" in r.text
          and "campo-setor" in r.text and "aplicarCampos" in r.text)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHAS: " + "; ".join(FALHAS))
        sys.exit(1)
    print("TESTES WEB FASE 3C OK")
    sys.exit(0)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    main()
