"""Testes Web — UX v1.30.1: layout fluido, paginação numerada, combobox,
filtros EPI (status/per), fichas por funcionário, anexo clean, painéis.

Standalone: python test_web_ux.py
Mesmo padrão de test_web_fase3c.py (patches de paths ANTES do create_app).
"""

import sys
import tempfile
from datetime import date
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


def make_env():
    tmp = Path(tempfile.mkdtemp(prefix="web_ux_"))
    (tmp / "cartoes").mkdir()
    (tmp / "certificados").mkdir()

    import src.utils.paths as paths_mod
    paths_mod.get_data_dir = lambda: tmp
    paths_mod.get_cartoes_dir = lambda: tmp / "cartoes"

    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.aso_repo as aso_mod
    import src.core.integracao_repo as integ_mod
    import src.core.epi_repo as epi_mod
    import src.core.certificate_service as cert_mod
    for mod in (er_mod, hr_mod, aso_mod, integ_mod, epi_mod):
        mod.get_db_path = lambda: tmp / "certificados.db"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")

    import src.web.app as app_mod
    app_mod.get_data_dir = lambda: tmp

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
    from src.core.epi_repo import EpiRepository
    from src.web.users_repo import UsersRepository

    er = EmployeeRepository()
    hr = HistoryRepository()
    epi_repo = EpiRepository()
    users = UsersRepository()
    hoje = date.today()
    hoje_iso = hoje.isoformat()
    hoje_br = hoje.strftime("%d/%m/%Y")

    _login_admin(client, users)

    # ── dados base ───────────────────────────────────────────────
    eA = er.create("Alice UX", "529.982.247-25", "Operador", foto=_png_bytes())
    eB = er.create("Bruno UX", "390.533.447-05", "Auxiliar")
    extras = [er.create(f"Func UX {i:02d}", None, "Geral") for i in range(1, 12)]
    check("U01 funcionarios criados", eA is not None and eB is not None
          and all(e is not None for e in extras))

    r = client.get("/funcionarios")
    check("U02 layout fluido (sem max-width 1080)", "max-width:1080px" not in r.text)
    check("U03 tabela com contorno preto",
          "table { width:100%; border-collapse:collapse; font-size:14px; border:1px solid #000; }" in r.text)

    # ── paginação numerada + per (funcionários) ──────────────────
    r = client.get("/funcionarios")
    check("U04 per select presente", 'name="per"' in r.text and ">20</option>" in r.text)
    r = client.get("/funcionarios?per=10")
    check("U05 per=10 pagina 1 de 2", "Página 1 de 2" in r.text)
    check("U06 link numerado pagina 2", 'href="/funcionarios?per=10&amp;page=2"' in r.text
          or 'href="/funcionarios?per=10&page=2"' in r.text)
    check("U07 pagina atual destacada", 'class="pg-atual"' in r.text)
    r = client.get("/funcionarios?per=50&page=1")
    check("U08 per=50 unica pagina", "Página 1 de 1" not in r.text or "pg-atual" not in r.text)
    r = client.get("/funcionarios?busca=Alice&per=25")
    check("U09 busca+per preservados", "Alice UX" in r.text)

    # ── certificados: combobox + campos opcionais ────────────────
    r = client.get("/certificados")
    check("U10 combobox busca funcionario", 'id="func_busca"' in r.text
          and 'name="funcionario_id"' in r.text and 'id="combo_lista"' in r.text)
    # v1.45.3: NR troca sem recarregar (JSON embutido), seleção preservada
    check("U11 nr troca sem recarregar (TMPLS embutido)",
          "var TMPLS = {" in r.text
          and "window.location='/certificados?nr='" not in r.text
          and 'id="extras-din"' in r.text)
    check("U12 campos opcionais em details", 'details class="opcoes"' in r.text
          or "Campos adicionais (opcional)" in r.text)

    # ── emissao lote: busca/per junto à tabela ───────────────────
    r = client.get("/emissao-lote")
    check("U13 lote barra junto à tabela", 'id="f-busca"' in r.text
          and 'id="f-per"' in r.text and 'id="f-pager"' in r.text)
    check("U14 lote linhas com data-busca", 'class="linha-func"' in r.text)

    # ── EPI: fichas com estados distintos ────────────────────────
    itens_dev = [{"ca": "CA1", "descricao": "Luva", "quantidade": "2",
                  "data_entrega": hoje_iso, "dev_quantidade": "2",
                  "dev_data": hoje_iso}]
    itens_pen = [{"ca": "CA2", "descricao": "Capacete", "quantidade": "1",
                  "data_entrega": hoje_iso, "dev_quantidade": "", "dev_data": ""}]
    num1 = epi_repo.next_epi_number()
    f1 = epi_repo.save(num1, eA, hoje_iso, itens_dev, status="aberto",
                       pdf_path=str(tmp / "f1.pdf"))
    num2 = epi_repo.next_epi_number()
    f2 = epi_repo.save(num2, eB, hoje_iso, itens_pen, status="aberto",
                       pdf_path=str(tmp / "f2.pdf"))
    check("U15 fichas criadas", f1 is not None and f2 is not None)

    r = client.get("/epi")
    check("U16 lista tem filtros novos", 'name="status"' in r.text
          and 'name="per"' in r.text and "Itens devolvidos" in r.text)
    r = client.get("/epi?status=devolvidos")
    check("U17 filtro devolvidos mostra Alice", "Alice UX" in r.text
          and "Bruno UX" not in r.text)
    r = client.get("/epi?status=aberto")
    check("U18 filtro abertas mostra Bruno", "Bruno UX" in r.text
          and "Alice UX" not in r.text)
    r = client.get("/epi?status=fechado")
    check("U19 filtro fechadas vazio", "Nenhuma ficha encontrada" in r.text)

    r = client.get(f"/epi/funcionario/{eA}")
    check("U20 fichas por funcionario", r.status_code == 200
          and str(num1) in r.text and "Ver todas as fichas" in r.text
          and str(num2) not in r.text)

    r = client.get(f"/epi/{f1}")
    check("U21 badge itens devolvidos na ficha", "Itens devolvidos" in r.text
          and "b-azul" in r.text)
    check("U22 trava qtd no modo total", 'onchange="alternarQtd(this)"' in r.text
          and "alternarQtd" in r.text)

    r = client.post(f"/epi/{f2}/devolucao", data={
        "dev_modo_0": "total", "dev_qtd_0": "", "data_devolucao": hoje_br})
    check("U23 devolucao total gravada", r.status_code == 303)
    r = client.get("/epi?status=devolvidos")
    check("U24 Bruno agora devolvidos", "Bruno UX" in r.text)

    # ── perfil: voltar largo + link EPI ──────────────────────────
    r = client.get(f"/funcionarios/{eA}")
    check("U25 voltar largo no topo", 'class="btn-voltar"' in r.text
          and r.text.index("btn-voltar") < r.text.index("Foto"))
    check("U26 link fichas EPI no perfil", "Fichas de EPI (1)" in r.text)

    # ── historico: anexo clean ───────────────────────────────────
    rec = CertificateRecord(cert_number="UX-0001", nr_code="NR-35",
                            employee_id=eA, funcionario_nome="Alice UX",
                            funcionario_cpf="529.982.247-25",
                            data_inicio=hoje_iso, data_fim=hoje_iso,
                            carga_horaria=8, descricao_treinamento="NR 35 UX",
                            campos_extra="{}")
    hr.save(rec)
    r = client.get("/historico")
    check("U27 anexo assinado em details", "anexo-pop" in r.text
          and "upload-area" in r.text and "arq-txt" in r.text)
    check("U28 input file cru removido", 'style="width:auto; max-width:200px' not in r.text)

    # ── vencimentos: painéis ─────────────────────────────────────
    r = client.get("/vencimentos")
    check("U29 paineis de severidade", "painel p-vermelho" in r.text
          and "painel p-laranja" in r.text and "painel p-ambar" in r.text)
    check("U30 painel clicavel", 'href="/vencimentos?periodo=vencidos"' in r.text)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}):")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TESTES WEB UX OK")


if __name__ == "__main__":
    main()
