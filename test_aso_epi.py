"""Testes ASO + EPI + novos campos de funcionario (v1.11.0).

Rodar: python test_aso_epi.py
"""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core.employee_repo import EmployeeRepository
from src.core.models import Employee
from src.core.aso_repo import AsoRepository
from src.core.epi_repo import EpiRepository
from src.ui.pages.vencimentos import filter_certs

PASSOS = []


def check(nome, cond):
    PASSOS.append((nome, bool(cond)))
    print(f"[{'OK' if cond else 'FALHOU'}] {nome}")


def make_db(tmp: Path) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    db = tmp / "test.db"
    EmployeeRepository(db_path=db)  # cria employees primeiro (JOINs)
    return db


# ── 1. Sequencias ASO/EPI ────────────────────────────────────

def test_sequencias(tmp: Path):
    db = make_db(tmp)
    aso = AsoRepository(db_path=db)
    epi = EpiRepository(db_path=db)
    check("sequencia ASO", aso.next_aso_number() == "ASO-000001"
          and aso.next_aso_number() == "ASO-000002")
    check("sequencia EPI", epi.next_epi_number() == "EPI-000001"
          and epi.next_epi_number() == "EPI-000002")


# ── 2. Expiracao ASO (renovacao substitui) ───────────────────

def test_aso_expiracao(tmp: Path):
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    aso = AsoRepository(db_path=db)
    emp_repo.create("Joao Pedro", None)
    emp = emp_repo.get_all()[0]

    hoje = date.today().isoformat()
    dois_anos_atras = (date.today() - timedelta(days=730)).isoformat()
    a1 = aso.save("ASO-000001", emp.id, "Periódico", dois_anos_atras, validade_meses=12)
    a2 = aso.save("ASO-000002", emp.id, "Periódico", hoje, validade_meses=12)

    lista = aso.get_asos_with_expiration()
    check("only_latest mantem 1 por funcionario", len(lista) == 1)
    check("vigente e a renovada", lista[0]["cert_number"] == "ASO-000002"
          and lista[0]["nr_code"] == "ASO"
          and lista[0]["descricao_treinamento"] == "Periódico"
          and lista[0]["dias_para_vencer"] > 300)
    todos = aso.get_asos_with_expiration(only_latest=False)
    check("only_latest=False traz todas", len(todos) == 2
          and any(a["status"] == "vencido" for a in todos))

    # outro funcionario nao e afetado
    emp_repo.create("Maria Silva", None)
    maria = emp_repo.get_all()[1]
    aso.save("ASO-000003", maria.id, "Admissional", hoje, validade_meses=6)
    check("dois funcionarios -> 2 vigentes",
          len(aso.get_asos_with_expiration()) == 2)


# ── 3. Novos campos do funcionario ───────────────────────────

def test_campos_funcionario(tmp: Path):
    db = make_db(tmp)
    repo = EmployeeRepository(db_path=db)
    repo.create("Joao Pedro", None, "Eletricista", None, "11999999999",
                data_nascimento="15/03/1990", tipo_sanguineo="a+",
                data_admissao="10/02/2020", registro_ctps="12345/67",
                cnh_ear=True)
    emp = repo.get_all()[0]
    check("create normaliza campos", emp.tipo_sanguineo == "A+"
          and emp.data_admissao == "2020-02-10"
          and emp.registro_ctps == "12345/67" and emp.cnh_ear is True)

    ok = repo.update(emp.id, emp.nome, emp.cpf, emp.funcao,
                     telefone=emp.telefone,
                     tipo_sanguineo=None, limpar_tipo_sanguineo=True,
                     registro_ctps=None, limpar_ctps=True,
                     cnh_ear=False)
    emp2 = repo.get_by_id(emp.id)
    check("update limpa ts/ctps e zera ear", ok and emp2.tipo_sanguineo is None
          and emp2.registro_ctps is None and emp2.cnh_ear is False)
    check("admissao preservada sem flag", emp2.data_admissao == "2020-02-10")

    repo.update(emp.id, emp.nome, emp.cpf, emp.funcao, data_admissao="01/01/2020")
    check("update troca admissao", repo.get_by_id(emp.id).data_admissao == "2020-01-01")


# ── 4. Import/Export colunas F-I ─────────────────────────────

def test_import_export(tmp: Path):
    import openpyxl
    from src.utils.excel_importer import import_employees_from_excel
    from src.utils.excel_exporter import export_employees_to_excel

    db = make_db(tmp)
    repo = EmployeeRepository(db_path=db)

    xlsx_in = tmp / "in.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nome", "CPF", "Funcao", "Telefone", "Nascimento",
               "Tipo Sangue", "Admissao", "CTPS", "CNH EAR"])
    ws.append(["Ana Souza", "52998224725", "Calheireta", "11988887777",
               "01/02/1990", "O+", "05/01/2021", "99887/66", "Sim"])
    ws.append(["Bruno Lima", "", "", "", "", "", "", "", ""])
    ws.append(["Carla Mota", "", "", "", "", "X+", "", "", ""])
    wb.save(xlsx_in)

    criados, duplicados, erros, detalhes = import_employees_from_excel(str(xlsx_in), repo)
    msgs = " | ".join(str(d) for d in detalhes).lower()
    check("import 2 criados 1 erro", criados == 2 and duplicados == 0
          and erros == 1 and "tipo sanguineo" in msgs)
    ana = repo.search("Ana Souza")[0]
    check("import campos F-I", ana.tipo_sanguineo == "O+"
          and ana.data_admissao == "2021-01-05"
          and ana.registro_ctps == "99887/66" and ana.cnh_ear is True)

    xlsx_out = tmp / "out.xlsx"
    n = export_employees_to_excel(repo, str(xlsx_out))
    wb2 = openpyxl.load_workbook(xlsx_out)
    ws2 = wb2.active
    headers = [c.value for c in ws2[1]]
    check("export headers novos", "Tipo Sanguineo" in headers
          and "Data Admissao" in headers and "Registro CTPS" in headers
          and "CNH EAR" in headers and n == 2)
    ana_row = next(r for r in ws2.iter_rows(min_row=2, values_only=True)
                   if r[1] == "Ana Souza")
    ts_i = headers.index("Tipo Sanguineo")
    ear_i = headers.index("CNH EAR")
    check("export valores", ana_row[ts_i] == "O+" and ana_row[ear_i] == "Sim")


# ── 5. EPI CRUD + status ─────────────────────────────────────

def test_epi_crud(tmp: Path):
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    epi = EpiRepository(db_path=db)
    emp_repo.create("Joao Pedro", None)
    emp = emp_repo.get_all()[0]

    items = [
        {"ca": "1234", "descricao": "Luva nitrilica", "quantidade": "2",
         "data_entrega": "2026-09-01", "dev_quantidade": "1",
         "dev_data": "2026-09-03"},
        {"ca": "5678", "descricao": "Capacete aba frontal", "quantidade": "1",
         "data_entrega": "2026-09-01", "dev_quantidade": "", "dev_data": ""},
    ]
    fid = epi.save("EPI-000001", emp.id, "2026-09-01", items)
    ficha = epi.get_by_id(fid)
    check("epi save/get", ficha["epi_number"] == "EPI-000001"
          and ficha["status"] == "aberto" and len(ficha["items"]) == 2)
    check("epi items normalizados", ficha["items"][0]["dev_quantidade"] == "1")

    check("get_by_employee", len(epi.get_by_employee(emp.id)) == 1)
    epi.update_items(fid, items[:1])
    check("update_items", len(epi.get_by_id(fid)["items"]) == 1)

    novo = epi.toggle_status(fid)
    check("toggle aberto->fechado", novo == "fechado"
          and epi.get_by_id(fid)["status"] == "fechado")
    check("toggle fechado->aberto", epi.toggle_status(fid) == "aberto")


# ── 6. EPI docs: multiplas versoes ───────────────────────────

def test_epi_docs_versoes(tmp: Path):
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    epi = EpiRepository(db_path=db)
    emp_repo.create("Maria Silva", None)
    emp = emp_repo.get_all()[0]
    fid = epi.save("EPI-000001", emp.id, "2026-09-01",
                   [{"ca": "1", "descricao": "Bota", "quantidade": "1",
                     "data_entrega": "2026-09-01", "dev_quantidade": "",
                     "dev_data": ""}])

    d1 = epi.add_doc(fid, "EPI-000001_scan1.pdf", b"%PDF-v1", "pdf")
    d2 = epi.add_doc(fid, "EPI-000001_scan2.pdf", b"%PDF-v2", "pdf")
    docs = epi.list_docs(fid)
    check("multiplas versoes convivem", len(docs) == 2 and epi.count_docs(fid) == 2)

    got = epi.get_doc(d1)
    check("get_doc", got and got[0] == fid and got[2] == b"%PDF-v1")

    epi.delete_doc(d2)
    check("delete 1 versao mantem a outra",
          epi.count_docs(fid) == 1 and epi.get_doc(d2) is None)

    try:
        epi.add_doc(fid, "mal.exe", b"MZ", "exe")
        check("exe bloqueado em epi_doc", False)
    except ValueError:
        check("exe bloqueado em epi_doc", True)


# ── 7. Merge vencimentos (formato compativel) ────────────────

def test_merge_vencimentos(tmp: Path):
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    aso = AsoRepository(db_path=db)
    emp_repo.create("Joao Pedro", None)
    emp = emp_repo.get_all()[0]
    hoje = date.today().isoformat()
    aso.save("ASO-000001", emp.id, "Periódico", hoje, validade_meses=12)

    asos = aso.get_asos_with_expiration()
    fake_certs = [{"nr_code": "NR-35", "funcionario_nome": "Joao Pedro",
                   "funcionario_cpf": "", "dias_para_vencer": 100,
                   "status": "ok", "descricao_treinamento": "NR-35",
                   "data_validade": "2027-01-01", "employee_id": emp.id}]
    combined = fake_certs + asos

    check("chaves exigidas pelo filter_certs presentes",
          all(k in asos[0] for k in
              ("nr_code", "funcionario_nome", "funcionario_cpf", "dias_para_vencer")))
    so_aso = filter_certs(combined, "ASO", "", "all")
    check("filtro NR=ASO isola ASOs", len(so_aso) == 1
          and so_aso[0]["cert_number"] == "ASO-000001")
    check("filtro TODAS traz tudo", len(filter_certs(combined, "TODAS", "", "all")) == 2)


# ── 8. PDFs ASO e EPI ────────────────────────────────────────

def test_pdfs(tmp: Path):
    import fitz
    from src.core.aso_pdf_generator import generate_aso_pdf
    from src.core.epi_pdf_generator import generate_epi_pdf

    tmp.mkdir(parents=True, exist_ok=True)
    emp = Employee(id=1, nome="Joao Pedro Teste", cpf="52998224725",
                   funcao="Eletricista", telefone="11999999999",
                   data_admissao="2020-03-10", tipo_sanguineo="O+")

    p_aso = tmp / "ASO-000001.pdf"
    generate_aso_pdf(str(p_aso), "ASO-000001", emp, "Periódico",
                     date.today().isoformat(), validade_meses=12)
    doc = fitz.open(p_aso)
    txt = "".join(pg.get_text() for pg in doc)
    check("pdf ASO gerado com numero e tipo",
          p_aso.exists() and "ASO-000001" in txt and "Periódico" in txt)

    items = [{"ca": "1234", "descricao": "Luva nitrilica", "quantidade": "2",
              "data_entrega": "01/09/2026", "dev_quantidade": "1",
              "dev_data": "03/09/2026"}]
    p_epi = tmp / "EPI-000001.pdf"
    generate_epi_pdf(str(p_epi), "EPI-000001", emp, "2026-09-01", items)
    doc2 = fitz.open(p_epi)
    txt2 = "".join(pg.get_text() for pg in doc2)
    check("pdf EPI gerado com numero e item",
          p_epi.exists() and "EPI-000001" in txt2 and "Luva nitrilica" in txt2)


# ── 9. Importacao em lote de ASOs (v1.12.0) ──────────────────

def test_aso_importer(tmp: Path):
    import openpyxl
    import src.utils.paths as paths_mod
    from src.utils.aso_importer import import_asos_from_excel, _parse_tipo

    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    aso = AsoRepository(db_path=db)
    emp_repo.create("Joao Pedro", "529.982.247-25")
    emp_repo.create("Maria Silva", None)

    check("ASO codigos: A/P/M/R/D mapeiam",
          _parse_tipo("A") == "Admissional" and _parse_tipo("p") == "Periódico"
          and _parse_tipo("M") == "Mudança de Função"
          and _parse_tipo("R") == "Retorno ao Trabalho"
          and _parse_tipo("D") == "Demissional")

    xlsx = tmp / "asos.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nome", "CPF", "Tipo de ASO", "Data do Exame", "Validade (meses)"])
    ws.append(["Joao Pedro", "529.982.247-25", "Admissional", "01/09/2026", 12])
    ws.append(["Maria Silva", "", "P", "05/09/2026", ""])
    ws.append(["Joao Pedro", "", "M", "10/09/2026", 6])
    ws.append(["Fantasma", "", "Admissional", "01/09/2026", 12])
    ws.append(["Joao Pedro", "", "Tipo Inexistente", "01/09/2026", 12])
    ws.append(["Maria Silva", "", "Admissional", "99/99/2026", 12])
    wb.save(xlsx)

    dest = tmp / "dados_asos"
    orig_get_data_dir = paths_mod.get_data_dir
    paths_mod.get_data_dir = lambda: dest
    try:
        res = import_asos_from_excel(xlsx, aso, emp_repo)
    finally:
        paths_mod.get_data_dir = orig_get_data_dir

    check("import ASO: 3 criados / 3 erros",
          len(res["criados"]) == 3 and res["erros"] == 3)
    check("import ASO: detalhes apontam linha/motivo",
          any("Fantasma" in d for d in res["detalhes"])
          and any("tipo" in d.lower() for d in res["detalhes"])
          and any("data" in d.lower() for d in res["detalhes"]))

    todos = aso.get_all(limit=10)
    check("import ASO: numeros sequenciais",
          {a["aso_number"] for a in todos} == {"ASO-000001", "ASO-000002", "ASO-000003"})
    joao = next(a for a in todos if a["funcionario_nome"] == "Joao Pedro"
                and a["tipo_aso"] == "Admissional")
    maria = next(a for a in todos if a["funcionario_nome"] == "Maria Silva")
    check("import ASO: match por CPF e nome",
          joao["tipo_aso"] == "Admissional" and maria["tipo_aso"] == "Periódico")
    check("import ASO: codigo M vira Mudança de Função",
          any(a["tipo_aso"] == "Mudança de Função" and a["validade_meses"] == 6
              for a in todos))
    check("import ASO: tipo normalizado e validade default",
          maria["validade_meses"] == 12)
    check("import ASO: PDFs gerados em data/asos/{pasta}",
          joao["pdf_path"] and Path(joao["pdf_path"]).exists()
          and Path(maria["pdf_path"]).exists()
          and dest.as_posix() in Path(joao["pdf_path"]).as_posix())


# ── 10. ASO embutido no PDF (v1.16.0) ────────────────────────

def test_aso_pdf_embedded(tmp: Path):
    import fitz
    from src.core.aso_pdf_generator import (generate_aso_pdf, rebuild_aso_pdf,
                                            rebuild_aso_pdf_sem_doc)
    db = make_db(tmp)
    emp_repo = EmployeeRepository(db_path=db)
    emp_repo.create("Joao Pedro", "52998224725")
    emp = emp_repo.get_all()[0]

    capa = tmp / "ASO-000001.pdf"
    aso = {"aso_number": "ASO-000001", "tipo_aso": "Periódico",
           "data_exame": date.today().isoformat(), "validade_meses": 12,
           "pdf_path": str(capa)}
    generate_aso_pdf(str(capa), "ASO-000001", emp, "Periódico",
                     date.today().isoformat(), 12)
    doc = fitz.open(capa)
    check("capa placeholder: 1 pagina", doc.page_count == 1)
    check("capa placeholder: quadro reservado", "ASO" in doc[0].get_text())
    doc.close()

    med = fitz.open()
    for i in range(2):
        med.new_page().insert_text((72, 72), f"PARECER MEDICO pagina {i + 1}")
    medico_pdf = tmp / "medico.pdf"
    med.save(str(medico_pdf))
    med.close()

    rebuild_aso_pdf(aso, emp, medico_pdf.read_bytes(), "pdf")
    doc = fitz.open(capa)
    check("PDF medico: capa + 2 paginas", doc.page_count == 3)
    check("PDF medico: texto do medico presente",
          "PARECER MEDICO" in doc[1].get_text() and "MEDICO" in doc[2].get_text())
    check("PDF medico: capa marca anexo", "ANEXADO" in doc[0].get_text())
    t1, t2 = doc[1].get_text(), doc[2].get_text()
    check("PDF medico: moldura altec nas paginas do doc",
          "Documento do medico" in t1 and "Documento do medico" in t2
          and "ASO-000001" in t1 and "ASO-000001" in t2
          and "Pagina 1 de 2" in t1 and "Pagina 2 de 2" in t2)
    doc.close()

    from io import BytesIO
    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", (400, 300), "white").save(buf, "PNG")
    rebuild_aso_pdf(aso, emp, buf.getvalue(), "png")
    doc = fitz.open(capa)
    check("imagem: capa + 1 pagina A4", doc.page_count == 2
          and abs(doc[1].rect.width - 595.28) < 2)
    check("imagem: capa marca anexo", "ANEXADO" in doc[0].get_text())
    t1 = doc[1].get_text()
    check("imagem: moldura altec na pagina do doc",
          "ASO-000001" in t1 and "Pagina 1 de 1" in t1)
    doc.close()

    rebuild_aso_pdf_sem_doc(aso, emp)
    doc = fitz.open(capa)
    check("remover doc: volta capa placeholder",
          doc.page_count == 1 and "ANEXADO" not in doc[0].get_text())
    doc.close()


# ── 11. Devolucao de EPI separada (v1.16.0) ──────────────────

def test_devolucao(tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    import fitz
    from src.ui.components.epi_manager_dialog import _iso, _resolver_devolucao
    from src.core.epi_pdf_generator import generate_devolucao_pdf
    from src.core.models import Employee as Emp

    # _iso: ano obrigatoriamente 4 digitos
    check("_iso aceita dd/mm/aaaa", _iso("05/09/2026") == "2026-09-05")
    try:
        _iso("05/09/26")
        check("_iso rejeita ano de 2 digitos", False)
    except ValueError:
        check("_iso rejeita ano de 2 digitos", True)
    try:
        _iso("31/02/2026")
        check("_iso rejeita data inexistente", False)
    except ValueError:
        check("_iso rejeita data inexistente", True)

    items = [
        {"ca": "1234", "descricao": "Luva nitrilica", "quantidade": "10",
         "data_entrega": "2026-09-01", "dev_quantidade": "", "dev_data": ""},
        {"ca": "5678", "descricao": "Oculos amber", "quantidade": "2",
         "data_entrega": "2026-09-01", "dev_quantidade": "", "dev_data": ""},
    ]

    res = _resolver_devolucao(items, {0: ("total", None), 1: ("parcial", "1")},
                              "2026-09-08")
    check("resolver: total grava quantidade cheia",
          res[0]["dev_quantidade"] == "10" and res[0]["dev_data"] == "2026-09-08")
    check("resolver: parcial grava qtde informada",
          res[1]["dev_quantidade"] == "1" and res[1]["dev_data"] == "2026-09-08")

    res2 = _resolver_devolucao(items, {0: ("pendente", None), 1: ("pendente", None)},
                               "2026-09-08")
    check("resolver: pendente limpa devolucao",
          res2[0]["dev_quantidade"] == "" and res2[1]["dev_data"] == "")

    for escolha, nome in [({0: ("parcial", "11")}, "maior que entregue"),
                          ({0: ("parcial", "0")}, "zero"),
                          ({0: ("parcial", "abc")}, "nao numerica")]:
        try:
            _resolver_devolucao(items, escolha, "2026-09-08")
            check(f"resolver rejeita {nome}", False)
        except ValueError:
            check(f"resolver rejeita {nome}", True)

    # termo de devolucao em PDF
    emp = Emp(id=1, nome="Joao Pedro", cpf="529.982.247-25", funcao="Eletricista")
    termo = tmp / "Devolucao - 08-09-2026 (EPI-000001).pdf"
    dev_items = _resolver_devolucao(items, {0: ("total", None), 1: ("parcial", "1")},
                                    "2026-09-08")
    generate_devolucao_pdf(str(termo), "EPI-000001", emp, "2026-09-08", dev_items)
    doc = fitz.open(termo)
    txt = doc[0].get_text()
    check("termo devolucao: gerado", termo.exists() and doc.page_count == 1)
    check("termo devolucao: titulo e numero",
          "DEVOLUCAO" in txt.upper() and "EPI-000001" in txt)
    check("termo devolucao: itens e estados",
          "Luva nitrilica" in txt and "Total" in txt and "Parcial" in txt)
    check("termo devolucao: assinaturas",
          "Empregado" in txt and "Responsavel" in txt)
    doc.close()


# ── 12. Ficha EPI v1.17.0: estado por item, quebra de pagina, merge ──

def test_ficha_epi_v1170(tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    import fitz
    from src.core.epi_pdf_generator import generate_epi_pdf
    from src.ui.components.epi_manager_dialog import _merge_devolucoes
    from src.core.models import Employee as Emp

    emp = Emp(id=1, nome="Joao Pedro", cpf="529.982.247-25", funcao="Eletricista")

    # (a) estado por item no PDF da ficha
    items = [
        {"ca": "1234", "descricao": "Luva nitrilica", "quantidade": "5",
         "data_entrega": "2026-09-01", "dev_quantidade": "2",
         "dev_data": "2026-09-08"},
        {"ca": "5678", "descricao": "Oculos amber", "quantidade": "3",
         "data_entrega": "2026-09-01", "dev_quantidade": "3",
         "dev_data": "2026-09-08"},
    ]
    ficha = tmp / "Ficha de EPI - 01-09-2026 (EPI-000001).pdf"
    generate_epi_pdf(str(ficha), "EPI-000001", emp, "2026-09-01", items)
    doc = fitz.open(ficha)
    txt = doc[0].get_text()
    check("ficha: estado parcial por item", "Devolvido: 2/5 (Parcial)" in txt)
    check("ficha: estado total por item", "(Total)" in txt)
    check("ficha: numero presente", "EPI-000001" in txt)
    doc.close()

    # (b) 25 itens -> quebra de pagina DURANTE A TABELA com cabecalho repetido
    many = [{"ca": f"CA{i:04d}", "descricao": f"Equipamento de teste numero {i}",
             "quantidade": "1", "data_entrega": "2026-09-01",
             "dev_quantidade": "", "dev_data": ""} for i in range(1, 26)]
    ficha2 = tmp / "ficha_25_itens.pdf"
    generate_epi_pdf(str(ficha2), "EPI-000002", emp, "2026-09-01", many)
    doc = fitz.open(ficha2)
    pgs_entrega = [p.get_text().count("ENTREGA DE EQUIPAMENTO") for p in doc]
    check("ficha 25 itens: multipagina", doc.page_count >= 2)
    check("ficha 25 itens: cabecalho repetido", sum(1 for n in pgs_entrega if n > 0) >= 2)
    todo = "".join(p.get_text() for p in doc)
    check("ficha 25 itens: ultimo item presente", "Equipamento de teste numero 25" in todo)
    doc.close()

    # (c) merge de devolucoes por conteudo
    antigos = [
        {"ca": "111", "descricao": "Capacete", "quantidade": "2",
         "data_entrega": "2026-09-01", "dev_quantidade": "2", "dev_data": "2026-09-05"},
        {"ca": "222", "descricao": "Luva", "quantidade": "5",
         "data_entrega": "2026-09-01", "dev_quantidade": "1", "dev_data": "2026-09-05"},
        {"ca": "333", "descricao": "Bota", "quantidade": "1",
         "data_entrega": "2026-09-01", "dev_quantidade": "1", "dev_data": "2026-09-06"},
    ]
    # remover item do meio (Luva)
    novos = [dict(antigos[0], quantidade="2"), dict(antigos[2])]
    m = _merge_devolucoes(antigos, novos)
    check("merge: remocao do meio preserva dev dos demais",
          m[0]["dev_quantidade"] == "2" and m[1]["dev_quantidade"] == "1"
          and m[0]["dev_data"] == "2026-09-05" and m[1]["dev_data"] == "2026-09-06")

    # reordenar mantem dev junto do item certo
    novos2 = [dict(antigos[2]), dict(antigos[0]), dict(antigos[1])]
    m2 = _merge_devolucoes(antigos, novos2)
    check("merge: reordenacao mantem dev por chave",
          m2[0]["descricao"] == "Bota" and m2[0]["dev_quantidade"] == "1"
          and m2[1]["descricao"] == "Capacete" and m2[1]["dev_quantidade"] == "2"
          and m2[2]["descricao"] == "Luva" and m2[2]["dev_quantidade"] == "1")

    # quantidade menor que devolucao descarta dev (Capacete: dev 2 > nova qtd 1)
    novos3 = [dict(antigos[0], quantidade="1")]
    m3 = _merge_devolucoes(antigos, novos3)
    check("merge: qtd menor que dev descarta dev",
          m3[0]["dev_quantidade"] == "" and m3[0]["dev_data"] == "")


def main():
    with tempfile.TemporaryDirectory(prefix="normatech_asoepi_",
                                     ignore_cleanup_errors=True) as td:
        tmp = Path(td)
        test_sequencias(tmp / "t1")
        test_aso_expiracao(tmp / "t2")
        test_campos_funcionario(tmp / "t3")
        test_import_export(tmp / "t4")
        test_epi_crud(tmp / "t5")
        test_epi_docs_versoes(tmp / "t6")
        test_merge_vencimentos(tmp / "t7")
        test_pdfs(tmp / "t8")
        test_aso_importer(tmp / "t9")
        test_aso_pdf_embedded(tmp / "t10")
        test_devolucao(tmp / "t11")
        test_ficha_epi_v1170(tmp / "t12")

    falhas = [n for n, ok in PASSOS if not ok]
    print(f"\n{len(PASSOS) - len(falhas)}/{len(PASSOS)} testes OK")
    if falhas:
        print("FALHARAM:", falhas)
        sys.exit(1)


if __name__ == "__main__":
    main()
