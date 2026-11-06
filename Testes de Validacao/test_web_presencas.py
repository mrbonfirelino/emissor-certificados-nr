"""Testes web da aba Listas de Presenca (v1.36.0; fluxo do dia v1.37.0).

Parte 1 (rotas, sem Excel): make_env com patches + gerador mockado (gera
PDF valido de 1 pagina via fitz para o merge do compilado funcionar).
Parte 2 (E2E com Excel COM, skip sem Office): emite listas de 3 NRs no dia
pelo fluxo real (nova -> emitir-dia -> compilado) e salva os PDFs de
exemplo em comparacao_listas/ para conferencia manual.

Roda direto:  python test_web_presencas.py
"""

import re
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import fitz
from fastapi.testclient import TestClient

# funcao REAL capturada antes de qualquer mock (Parte 2 usa esta)
from src.core.presenca_generator import gerar_pdf_lista as _gerar_real

# paths REAIS capturados antes de qualquer patch (Parte 2 usa nos exemplos:
# exercita o modelo XLSX real do registry e a logo verdadeira da empresa)
from src.utils.paths import get_templates_dir as _real_get_templates_dir
from src.utils.paths import get_logo_path as _real_get_logo_path

FALHAS = []


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="presencas_web_"))
    tmp.mkdir(parents=True, exist_ok=True)
    import src.utils.paths as paths_mod
    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.aso_repo as aso_mod
    import src.core.integracao_repo as integ_mod
    import src.core.presenca_repo as pres_mod
    import src.core.presenca_generator as gen_mod
    import src.core.certificate_service as cert_mod
    import src.web.app as app_mod

    paths_mod.get_data_dir = lambda: tmp
    er_mod.get_db_path = lambda: tmp / "certificados.db"
    hr_mod.get_db_path = lambda: tmp / "certificados.db"
    aso_mod.get_db_path = lambda: tmp / "certificados.db"
    integ_mod.get_db_path = lambda: tmp / "certificados.db"
    pres_mod.DB_PATH = tmp / "certificados.db"
    gen_mod.get_templates_dir = lambda: tmp / "sem-registry"
    gen_mod.get_data_dir = lambda: tmp
    gen_mod.get_logo_path = lambda: tmp / "logo.png"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    app_mod.get_data_dir = lambda: tmp

    return tmp, paths_mod, er_mod, hr_mod, pres_mod, gen_mod


def _login_admin(client):
    from src.web.users_repo import UsersRepository
    users = UsersRepository()
    users.bootstrap_admin()
    admin = users.get_by_username("admin")
    prov = users.reset_password(admin["id"])
    r = client.post("/login", data={"username": "admin", "password": prov},
                    follow_redirects=False)
    assert r.status_code == 303, r.status_code
    r = client.post("/troca-senha",
                    data={"atual": prov, "nova": "SenhaF0rte", "confirma": "SenhaF0rte"},
                    follow_redirects=False)
    assert r.status_code == 303, r.status_code


def _criar_funcionario_certificado(er, hr, nome, nr, iso):
    emp_id = er.create(nome, cpf=None, funcao="Eletricista")
    from src.core.history_repo import CertificateRecord
    hr.save(CertificateRecord(
        cert_number="CERT-0" + str(emp_id).zfill(4), nr_code=nr,
        employee_id=emp_id, funcionario_nome=nome, funcionario_cpf="",
        data_inicio=iso, data_fim=iso, carga_horaria=8,
        descricao_treinamento="Teste", campos_extra="{}"))
    return emp_id


def parte1_rotas():
    print("\n--- Parte 1: rotas (gerador mockado com PDF valido) ---")
    tmp, paths_mod, er_mod, hr_mod, pres_mod, gen_mod = make_env()

    pdfs_gerados = []

    def fake_gerar(nr, label, iso, carga, part, assunto, saida, serial=""):
        saida = Path(saida)
        saida.parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open()
        p = doc.new_page()
        p.insert_text((72, 72), f"LISTA {nr} {saida.stem}")
        doc.save(str(saida))
        doc.close()
        pdfs_gerados.append(saida)
        return saida

    gen_mod.gerar_pdf_lista = fake_gerar

    from src.web.app import create_app
    app = create_app(db_path=tmp / "certificados.db", secret_file=tmp / "secret.key")
    client = TestClient(app, follow_redirects=False)
    _login_admin(client)

    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository
    er = EmployeeRepository()
    hr = HistoryRepository()
    _criar_funcionario_certificado(er, hr, "CARLOS SOUZA", "NR-35", "2026-09-15")
    _criar_funcionario_certificado(er, hr, "ANA LIMA", "NR-35", "2026-09-15")
    _criar_funcionario_certificado(er, hr, "BRUNO DIAS", "NR-10", "2026-09-01")
    _criar_funcionario_certificado(er, hr, "DANIEL OLIVEIRA", "NR-12", "2026-09-15")

    r = client.get("/presencas")
    check("P01 lista abre", r.status_code == 200 and "Listas de Presen" in r.text)

    # --- nova: secoes por NR na data ---
    r = client.get("/presencas/nova", params={"data": "2026-09-15"})
    check("P02 secao NR-35 com participantes",
          r.status_code == 200 and "CARLOS SOUZA" in r.text and "ANA LIMA" in r.text)
    check("P03 checkbox incluir_NR-35 marcado",
          'name="incluir_NR-35"' in r.text and "checked" in r.text)
    check("P04 NR-12 do mesmo dia aparece", "DANIEL OLIVEIRA" in r.text
          and 'name="incluir_NR-12"' in r.text)
    check("P05 NR-10 de outro dia NAO aparece", 'name="incluir_NR-10"' not in r.text)

    r = client.get("/presencas/nova", params={"data": "2026-09-01"})
    check("P06 secao NR-10 no dia certo", "BRUNO DIAS" in r.text
          and 'name="incluir_NR-10"' in r.text)

    r = client.get("/presencas/nova", params={"data": "2030-01-01"})
    check("P07 data sem emissoes mostra aviso",
          r.status_code == 200 and "Nenhuma emiss" in r.text
          and 'name="incluir_' not in r.text)

    # --- emitir-dia: 1 NR ---
    r = client.post("/presencas/emitir-dia",
                    data={"data": "2026-09-15", "incluir_NR-35": "on"},
                    follow_redirects=False)
    check("P08 emitir-dia -> 303 resultado",
          r.status_code == 303 and r.headers["location"] == "/presencas/resultado")

    r = client.get("/presencas/resultado")
    check("P09 resumo com serial e dialog do compilado",
          r.status_code == 200 and "LP-2026-00001" in r.text
          and "Baixar compilado" in r.text
          and 'href="/presencas/compilado/2026-09-15?ids=' in r.text)
    m = re.search(r'href="/presencas/(\d+)"', r.text)
    pid = int(m.group(1)) if m else 0

    r = client.get("/presencas")  # consome flash
    check("P10 lista mostra LP-2026-00001 Pendente",
          "LP-2026-00001" in r.text and "Pendente" in r.text)

    r = client.get(f"/presencas/{pid}")
    check("P11 detalhe com participantes",
          r.status_code == 200 and "CARLOS SOUZA" in r.text)

    r = client.get(f"/presencas/{pid}/pdf")
    check("P12 PDF servido", r.status_code == 200 and r.content.startswith(b"%PDF"))

    r = client.get("/presencas/compilado/2026-09-15")
    check("P13 compilado 200 PDF (1 lista)", r.status_code == 200
          and r.content.startswith(b"%PDF"))
    doc = fitz.open(stream=r.content, filetype="pdf")
    check("P14 compilado com 1 pagina", len(doc) == 1)
    doc.close()

    # --- emitir-dia: 2 NRs de uma vez ---
    r = client.post("/presencas/emitir-dia",
                    data={"data": "2026-09-15", "incluir_NR-12": "on",
                          "incluir_NR-35": "on"},
                    follow_redirects=False)
    check("P15 emitir 2 NRs -> 303", r.status_code == 303)
    r = client.get("/presencas/resultado")
    check("P16 resumo com 2 listas", "LP-2026-00002" in r.text
          and "LP-2026-00003" in r.text)

    r = client.get("/presencas")
    check("P17 lista com os 3 registros", "LP-2026-00002" in r.text
          and "LP-2026-00003" in r.text)

    r = client.get("/presencas/compilado/2026-09-15")
    doc = fitz.open(stream=r.content, filetype="pdf")
    check("P18 compilado junta as 3 listas", r.status_code == 200 and len(doc) == 3)
    doc.close()

    # --- emitir-dia sem NR marcada ---
    r = client.post("/presencas/emitir-dia", data={"data": "2026-09-15"},
                    follow_redirects=False)
    check("P19 sem checkbox -> 303 nova",
          r.status_code == 303 and "/presencas/nova" in r.headers["location"])
    r = client.get("/presencas/nova", params={"data": "2026-09-15"})
    r = client.get("/presencas")
    check("P20 nada criado", "LP-2026-00004" not in r.text)

    # --- falha de geracao: sem registro orfao ---
    def gerar_ruim(*a, **k):
        raise RuntimeError("Excel nao encontrado")
    gen_mod.gerar_pdf_lista = gerar_ruim
    r = client.post("/presencas/emitir-dia",
                    data={"data": "2026-09-15", "incluir_NR-12": "on"},
                    follow_redirects=False)
    check("P21 falha de PDF -> 303 resultado", r.status_code == 303)
    r = client.get("/presencas/resultado")
    check("P22 resumo mostra falha", "falha ao gerar PDF" in r.text)
    r = client.get("/presencas")
    check("P23 sem registro orfao", "LP-2026-00004" not in r.text)
    gen_mod.gerar_pdf_lista = fake_gerar

    # --- NR marcada sem emissoes na data ---
    r = client.post("/presencas/emitir-dia",
                    data={"data": "2030-01-01", "incluir_NR-10": "on"},
                    follow_redirects=False)
    r = client.get("/presencas/resultado")
    check("P24 falha sem emissoes no resumo", "sem emiss" in r.text
          and "Nenhuma lista foi gerada" in r.text)

    # --- detalhe/status/assinar/excluir (lista 00001) ---
    r = client.post(f"/presencas/{pid}/status", data={"status": "parcial"},
                    follow_redirects=False)
    check("P25 status parcial -> 303", r.status_code == 303)
    r = client.get(f"/presencas/{pid}")
    check("P26 detalhe Parcial", "Parcial" in r.text)

    png = bytes.fromhex("89504e470d0a1a0a0000000d494844520000000100000001080600000"
                        "01f15c4890000000d4944415478da63fcffff3f0300050201cfa02d"
                        "ef0000000049454e44ae426082")
    r = client.post(f"/presencas/{pid}/assinar",
                    files={"arquivo": ("lista_assinada.png", png, "image/png")},
                    follow_redirects=False)
    check("P27 assinar -> 303", r.status_code == 303)
    r = client.get(f"/presencas/{pid}")
    check("P28 detalhe Assinada + arquivo",
          "Assinada" in r.text and "lista_assinada.png" in r.text)
    r = client.get(f"/presencas/{pid}/assinada")
    check("P29 download assinada", r.status_code == 200 and r.content == png)

    r = client.post(f"/presencas/{pid}/assinada/excluir", follow_redirects=False)
    check("P30 remover anexo -> 303", r.status_code == 303)
    r = client.get(f"/presencas/{pid}")
    check("P31 voltou para Pendente", "Pendente" in r.text)

    r = client.post(f"/presencas/{pid}/excluir", follow_redirects=False)
    check("P32 excluir -> 303 /presencas",
          r.status_code == 303 and r.headers["location"] == "/presencas")
    r = client.get("/presencas")
    check("P33 lista sem o registro", 'href="/presencas/%d"' % pid not in r.text)
    check("P34 arquivo PDF apagado", not pdfs_gerados[0].exists())

    # --- compilado sem listas na data ---
    r = client.get("/presencas/compilado/2030-01-01")
    check("P35 compilado vazio -> 303",
          r.status_code == 303 and r.headers["location"] == "/presencas")

    # --- consulta: ve, nao escreve ---
    from src.web.users_repo import UsersRepository
    users = UsersRepository()
    users.create_user("pedro", "Pedro Consulta", "consulta")
    pprov = users.reset_password(users.get_by_username("pedro")["id"])
    client.get("/logout")
    client.post("/login", data={"username": "pedro", "password": pprov},
                follow_redirects=False)
    client.post("/troca-senha",
                data={"atual": pprov, "nova": "SenhaC0nsulta", "confirma": "SenhaC0nsulta"},
                follow_redirects=False)
    r = client.get("/presencas")
    check("P36 consulta ve a lista", r.status_code == 200)
    r = client.get("/presencas/nova", params={"data": "2026-09-15"})
    check("P37 consulta sem botao emitir",
          r.status_code == 200 and "Emitir listas do dia" not in r.text)
    r = client.post("/presencas/emitir-dia",
                    data={"data": "2026-09-15", "incluir_NR-12": "on"},
                    follow_redirects=False)
    check("P38 consulta nao emite", r.status_code == 303)
    r = client.get("/presencas")
    check("P39 nada criado pela consulta", "LP-2026-00004" not in r.text)

    shutil.rmtree(tmp, ignore_errors=True)


def _excel_ok() -> bool:
    try:
        import comtypes.client

        app = comtypes.client.CreateObject("Excel.Application", dynamic=True)
        app.Quit()
        return True
    except Exception:
        return False


def parte2_e2e_excel():
    print("\n--- Parte 2: E2E com Excel COM (PDFs reais + compilado) ---")
    try:
        if not _excel_ok():
            print("  [SKIP] Microsoft Excel nao disponivel")
            return
        import src.core.presenca_generator as gen

        # restaura o gerador REAL e os paths REAIS (Parte 1 deixou mocks no
        # modulo): os exemplos devem exercitar o modelo XLSX do registry e a
        # logo verdadeira, como em producao
        gen.gerar_pdf_lista = _gerar_real
        gen.get_templates_dir = _real_get_templates_dir
        gen.get_logo_path = _real_get_logo_path

        comp = Path(__file__).resolve().parent / "comparacao_listas"
        comp.mkdir(exist_ok=True)
        participantes = [
            {"nome": "CARLOS EDUARDO SOUZA", "funcao": "Eletricista de Manutencao", "cpf": "111.222.333-44"},
            {"nome": "ANA BEATRIZ LIMA", "funcao": "Tecnica de Seguranca", "cpf": "555.666.777-88"},
            {"nome": "BRUNO ROCHA DIAS", "funcao": "Soldador", "cpf": None},
        ]

        # 2a. individuais (modelos NR-01/NR-06 e layout padrao NR-33)
        # NR-01 com carga FLOAT 8.0 (vem REAL do banco) — exercita o fix
        # que converte para int antes do formato '{:02d}HS' do modelo
        for nr, iso, carga in [("NR-01", "2026-09-15", 8.0), ("NR-06", "2026-09-15", 3),
                               ("NR-33", "2026-09-15", 8)]:
            saida = comp / f"LISTA_{nr.replace('-', '')}_EXEMPLO.pdf"
            try:
                _gerar_real(nr, nr, iso, carga, participantes,
                            f"Treinamento {nr}", saida, serial="LP-TESTE-00001")
            except Exception as e:
                check(f"E2E {nr} PDF ({e})", False)
                continue
            tamanho = saida.stat().st_size if saida.exists() else 0
            check(f"E2E {nr} PDF com conteudo (>1KB)", tamanho > 1000)
            texto = ""
            try:
                doc = fitz.open(str(saida))
                texto = " ".join(p.get_text() for p in doc)
                paginas = len(doc)
                doc.close()
            except Exception as e:
                check(f"E2E {nr} PDF abre no leitor ({e})", False)
                continue
            check(f"E2E {nr} PDF abre no leitor", True)
            check(f"E2E {nr} participante no PDF", "CARLOS EDUARDO SOUZA" in texto)
            check(f"E2E {nr} data no PDF", "15/09/2026" in texto)
            if nr == "NR-01":
                check("E2E NR-01 carga float 8.0 formatada 08HS",
                      "08HS" in texto)
            check(f"E2E {nr} tem paginas ({paginas})", paginas >= 1)
            retrato = all(p.rect.width < p.rect.height for p in fitz.open(str(saida)))
            check(f"E2E {nr} folha vertical (retrato)", retrato)
            # v1.39: logo presente, nenhuma folha em branco, sem dados de exemplo
            imgs = sum(len(p.get_images()) for p in fitz.open(str(saida)))
            check(f"E2E {nr} logo presente", imgs >= 1)
            brancas = sum(1 for p in fitz.open(str(saida)) if not p.get_text().strip())
            check(f"E2E {nr} sem folhas em branco", brancas == 0)
            exemplos = [x for x in ("JONATAS", "FELIPE DOS REIS", "27/08/2026",
                                    "18 de agosto de 2026", "28 de agosto de 2026")
                        if x in texto]
            check(f"E2E {nr} sem dados de exemplo do template", not exemplos)
            # v1.41: empresa fixa nas linhas, tokens substituidos, serial/pag
            check(f"E2E {nr} empresa ALTEC INDUSTRIAL nas linhas",
                  "ALTEC INDUSTRIAL" in texto)
            check(f"E2E {nr} sem tokens literais",
                  "{SERIAL}" not in texto and "{PAGINACAO}" not in texto)
            if nr in ("NR-06", "NR-33"):
                check(f"E2E {nr} serial e paginacao no PDF",
                      "LP-TESTE-00001" in texto and "Pag 1 de 1" in texto)
            # v1.40: conteudo programatico intacto e sem lixo de COM/outras abas
            check(f"E2E {nr} sem rastro de comtypes", "comtypes" not in texto)
            if nr == "NR-06":
                check("E2E NR-06 carga original '03 HORAS' preservada",
                      "03 HORAS" in texto)
                check("E2E NR-06 sem abas de outras NRs",
                      "PINTURA" not in texto and "PGR" not in texto)
            print(f"        copia: comparacao_listas/{saida.name} ({tamanho} bytes)")

        # 2b. NR-06 com 25 participantes -> 2 folhas (23 vagas/folha), Pag i de N
        print("  --- NR-06 com 25 participantes (2 folhas) ---")
        muitos = [{"nome": f"PARTICIPANTE {i:02d} DA SILVA", "funcao": "Operador",
                   "cpf": None} for i in range(1, 26)]
        saida2 = comp / "LISTA_NR06_2FOLHAS_EXEMPLO.pdf"
        try:
            _gerar_real("NR-06", "NR-06", "2026-09-15", 3, muitos,
                        "Treinamento NR-06 (2 folhas)", saida2,
                        serial="LP-TESTE-00002")
        except Exception as e:
            check(f"E2G NR-06 2 folhas PDF ({e})", False)
        else:
            doc = fitz.open(str(saida2))
            pags = [p.get_text() for p in doc]
            tam = [(p.rect.width, p.rect.height) for p in doc]
            imgs2 = sum(len(p.get_images()) for p in doc)
            doc.close()
            check("E2G 25 participantes -> 2 folhas", len(pags) == 2)
            check("E2G folha 1 com Pag 1 de 2", "Pag 1 de 2" in pags[0])
            check("E2G folha 2 com Pag 2 de 2", len(pags) > 1 and "Pag 2 de 2" in pags[1])
            check("E2G mesmo serial nas duas folhas",
                  all("LP-TESTE-00002" in t for t in pags))
            check("E2G participante 23 na folha 1",
                  "PARTICIPANTE 23" in pags[0] and "PARTICIPANTE 24" not in pags[0])
            check("E2G participantes 24/25 na folha 2",
                  len(pags) > 1 and "PARTICIPANTE 24" in pags[1]
                  and "PARTICIPANTE 25" in pags[1])
            check("E2G ALTEC INDUSTRIAL nas duas folhas",
                  all("ALTEC INDUSTRIAL" in t for t in pags))
            check("E2G folhas verticais (retrato)",
                  all(w < h for (w, h) in tam))
            check("E2G logo presente", imgs2 >= 1)
            check("E2G sem folhas em branco",
                  all(t.strip() for t in pags))
            check("E2G sem tokens literais",
                  "{SERIAL}" not in " ".join(pags)
                  and "{PAGINACAO}" not in " ".join(pags))
            print(f"        copia: comparacao_listas/{saida2.name} "
                  f"({saida2.stat().st_size} bytes, {len(pags)} folhas)")

        # 3. fluxo completo pelo app com Excel real: nova -> emitir-dia -> compilado
        print("  --- fluxo completo (app + Excel real) ---")
        tmp, paths_mod, er_mod, hr_mod, pres_mod, gen_mod = make_env()
        gen_mod.gerar_pdf_lista = _gerar_real
        from src.web.app import create_app
        app = create_app(db_path=tmp / "certificados.db", secret_file=tmp / "secret.key")
        client = TestClient(app, follow_redirects=False)
        _login_admin(client)

        from src.core.employee_repo import EmployeeRepository
        from src.core.history_repo import HistoryRepository
        er = EmployeeRepository()
        hr = HistoryRepository()
        _criar_funcionario_certificado(er, hr, "CARLOS SOUZA", "NR-01", "2026-09-15")
        _criar_funcionario_certificado(er, hr, "ANA LIMA", "NR-06", "2026-09-15")
        _criar_funcionario_certificado(er, hr, "BRUNO DIAS", "NR-33", "2026-09-15")

        r = client.get("/presencas/nova", params={"data": "2026-09-15"})
        check("E2F nova mostra 3 secoes", 'name="incluir_NR-01"' in r.text
              and 'name="incluir_NR-06"' in r.text
              and 'name="incluir_NR-33"' in r.text)

        r = client.post("/presencas/emitir-dia",
                        data={"data": "2026-09-15", "incluir_NR-01": "on",
                              "incluir_NR-06": "on", "incluir_NR-33": "on"},
                        follow_redirects=False)
        check("E2F emitir-dia -> 303 resultado", r.status_code == 303)
        r = client.get("/presencas/resultado")
        check("E2F resumo com 3 listas", r.status_code == 200
              and r.text.count("LP-2026-0000") == 3)

        # v1.40: dialog linka o compilado com os ids EXATOS da emissao
        m_ids = re.search(r'href="/presencas/compilado/2026-09-15\?ids=([\d,]+)"',
                          r.text)
        ids_emissao = m_ids.group(1) if m_ids else ""
        check("E2F dialog com ?ids= das 3 listas",
              bool(ids_emissao) and len(ids_emissao.split(",")) == 3)

        r = client.get(f"/presencas/compilado/2026-09-15?ids={ids_emissao}")
        check("E2F compilado por ids 200", r.status_code == 200
              and r.content.startswith(b"%PDF"))
        comp_pdf = comp / "COMPILADO_EXEMPLO.pdf"
        comp_pdf.write_bytes(r.content)
        doc = fitz.open(str(comp_pdf))
        texto = " ".join(p.get_text() for p in doc)
        paginas = len(doc)
        doc.close()
        check("E2F compilado com 1+ pagina por lista (>=3)",
              paginas >= 3)
        doc2 = fitz.open(str(comp_pdf))
        check("E2F compilado folha vertical (retrato)",
              all(p.rect.width < p.rect.height for p in doc2))
        doc2.close()
        check("E2F compilado com os participantes",
              "CARLOS SOUZA" in texto and "ANA LIMA" in texto and "BRUNO DIAS" in texto)
        check("E2F Pag 1 de 1 em cada lista", "Pag 1 de 1" in texto)
        check("E2F sem tokens literais no compilado",
              "{SERIAL}" not in texto and "{PAGINACAO}" not in texto)

        # v1.40: lista emitida DEPOIS na mesma data NAO entra no compilado por ids
        _criar_funcionario_certificado(er, hr, "RITA FARIA", "NR-33", "2026-09-15")
        r = client.post("/presencas/emitir-dia",
                        data={"data": "2026-09-15", "incluir_NR-33": "on"},
                        follow_redirects=False)
        check("E2F 2a emissao -> 303 resultado", r.status_code == 303)
        r = client.get(f"/presencas/compilado/2026-09-15?ids={ids_emissao}")
        d = fitz.open(stream=r.content, filetype="pdf")
        t_ids = " ".join(p.get_text() for p in d)
        d.close()
        check("E2F compilado por ids EXCLUI lista posterior", "RITA FARIA" not in t_ids)
        check("E2F compilado por ids mantem participantes",
              "CARLOS SOUZA" in t_ids and "BRUNO DIAS" in t_ids)
        r = client.get("/presencas/compilado/2026-09-15")
        d = fitz.open(stream=r.content, filetype="pdf")
        t_dia = " ".join(p.get_text() for p in d)
        d.close()
        check("E2F compilado do dia inteiro INCLUI a posterior", "RITA FARIA" in t_dia)

        print(f"        copia: comparacao_listas/COMPILADO_EXEMPLO.pdf "
              f"({comp_pdf.stat().st_size} bytes, {paginas} paginas)")
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        pass


def main():
    try:
        parte1_rotas()
        parte2_e2e_excel()
    finally:
        pass
    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}): {', '.join(FALHAS)}")
        sys.exit(1)
    print("TESTES LISTAS DE PRESENCA OK")


if __name__ == "__main__":
    main()
