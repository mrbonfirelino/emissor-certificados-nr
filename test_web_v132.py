"""Testes Web — v1.32: Dashboard home, Configurações, busca/paginação
Crachás+Cartões e modal de confirmação.

Standalone: python test_web_v132.py
Mesmo padrão das demais suítes (patches de paths ANTES do create_app).
"""

import sys
import tempfile
from datetime import date
from pathlib import Path

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
    tmp = Path(tempfile.mkdtemp(prefix="web_v132_"))
    (tmp / "cartoes").mkdir()
    (tmp / "certificados").mkdir()

    import src.utils.paths as paths_mod
    paths_mod.get_data_dir = lambda: tmp
    paths_mod.get_cartoes_dir = lambda: tmp / "cartoes"
    logo = tmp / "logo.png"
    logo.write_bytes(_png_bytes())
    paths_mod.get_logo_path = lambda: logo

    import src.core.employee_repo as er_mod
    import src.core.history_repo as hr_mod
    import src.core.aso_repo as aso_mod
    import src.core.integracao_repo as integ_mod
    import src.core.cracha_repo as cr_mod
    import src.core.certificate_service as cert_mod
    for mod in (er_mod, hr_mod, aso_mod, integ_mod, cr_mod):
        mod.get_db_path = lambda: tmp / "certificados.db"
    cert_mod.get_certificados_dir = lambda: tmp / "certificados"
    from types import SimpleNamespace
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")

    import src.core.config as config_mod
    config_mod.CONFIG_FILE = tmp / "company_config.json"
    config_mod.RESTORE_KEY_FILE = tmp / "restore.key"
    import src.core.app_settings as settings_mod
    settings_mod.SETTINGS_FILE = tmp / "app_settings.json"
    import src.utils.error_log as error_mod
    error_mod.ERROR_LOG = tmp / "error.log"
    import src.core.scheduled_task as st_mod
    st_mod.register = lambda hora: True
    st_mod.is_active = lambda: False
    st_mod.remove = lambda: True
    st_mod.validar_hora = lambda hora: True

    import src.web.app as app_mod
    app_mod.get_data_dir = lambda: tmp
    import src.web.routers.cartoes as cartoes_mod
    cartoes_mod.get_cartoes_dir = lambda: tmp / "cartoes"

    from src.web.app import create_app
    from fastapi.testclient import TestClient
    app = create_app(db_path=tmp / "certificados.db", secret_file=tmp / "secret.key")
    client = TestClient(app=app, follow_redirects=False)
    return client, app, tmp


def _trocar_senha(client, atual, nova="SenhaF0rte"):
    return client.post("/troca-senha", data={
        "atual": atual, "nova": nova, "confirma": nova})


def _login(client, users, username):
    u = users.get_by_username(username)
    prov = users.reset_password(u["id"])
    client.post("/login", data={"username": username, "password": prov})
    _trocar_senha(client, prov)


def main():
    client, app, tmp = make_env()
    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository, CertificateRecord
    from src.core.cracha_repo import CrachaRepository
    from src.web.users_repo import UsersRepository

    er = EmployeeRepository()
    hr = HistoryRepository()
    users = UsersRepository()
    hoje = date.today()
    hoje_iso = hoje.isoformat()

    _login(client, users, "admin")

    # ── dados base ───────────────────────────────────────────────
    nasc_hoje = f"1990-{hoje.month:02d}-{hoje.day:02d}"
    foto = _png_bytes()
    eAna = er.create("Ana V132", "529.982.247-25", "Operador",
                     foto=foto, data_nascimento=nasc_hoje)
    eBruno = er.create("Bruno V132", "390.533.447-05", "Eletricista", foto=foto)
    check("V01 funcionarios criados", eAna is not None and eBruno is not None)
    hr.save(CertificateRecord(
        cert_number="V132-0001", nr_code="NR-35", employee_id=eAna,
        funcionario_nome="Ana V132", funcionario_cpf="529.982.247-25",
        data_inicio=hoje_iso, data_fim=hoje_iso, carga_horaria=8,
        descricao_treinamento="Trabalho em Altura", campos_extra="{}"))
    hr.save(CertificateRecord(
        cert_number="V132-0002", nr_code="NR-10", employee_id=eBruno,
        funcionario_nome="Bruno V132", funcionario_cpf="390.533.447-05",
        data_inicio=hoje_iso, data_fim=hoje_iso, carga_horaria=8,
        descricao_treinamento="NR 10 Eletrico", campos_extra="{}"))
    from src.core.aso_repo import AsoRepository
    aso_repo = AsoRepository()
    aso_repo.save(aso_repo.next_aso_number(), eAna, "Periódico", hoje_iso, 12)
    aso_repo.save(aso_repo.next_aso_number(), eBruno, "Periódico", hoje_iso, 12)

    # ── DASHBOARD ────────────────────────────────────────────────
    r = client.get("/")
    check("V02 dashboard 200 com boas-vindas",
          r.status_code == 200 and "Bem-vindo ao NormaTech!" in r.text)
    _DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
             "sexta-feira", "sábado", "domingo"]
    _MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
              "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    data_ext = (f"{_DIAS[hoje.weekday()]}, {hoje.day} de "
                f"{_MESES[hoje.month - 1]} de {hoje.year}")
    check("V03 data extensa + relógio",
          data_ext in r.text and 'id="hora"' in r.text)
    check("V04 logo no hero", '/img' not in r.text and '<img src="/logo.png"' in r.text)
    check("V05 aniversariantes de hoje/mês com Ana",
          "Aniversariantes de hoje" in r.text
          and f"Aniversariantes de {_MESES[hoje.month - 1].capitalize()}" in r.text
          and "Ana V132" in r.text)
    check("V06 stat cards",
          "Certificados emitidos" in r.text
          and "Funcionários cadastrados" in r.text
          and "NRs disponíveis" in r.text)
    check("V07 indicadores viraram details", "Ver indicadores" in r.text)
    check("V08 JS do modal carregado no base",
          "data-confirmar-lista" in r.text and "modal-topo" in r.text)

    r = client.get("/logo.png")
    check("V09 /logo.png 200 PNG", r.status_code == 200 and r.content[:4] == b"\x89PNG")
    from fastapi.testclient import TestClient
    anon = TestClient(app=app, follow_redirects=False)
    r = anon.get("/logo.png")
    check("V10 logo exige login", r.status_code == 303)

    # ── CONFIGURAÇÕES ────────────────────────────────────────────
    r = client.get("/configuracoes")
    check("V11 configuracoes GET 200 (admin)",
          r.status_code == 200 and "Dados da Empresa" in r.text
          and "Backups" in r.text and "Log de Erros" in r.text)
    r = client.post("/configuracoes/salvar", data={
        "empresa": "Empresa Teste Config", "cnpj": "11.222.333/0001-81",
        "local": "Planta V132", "instrutor": "Instrutor V132",
        "registro": "MTE 44633/RJ", "senha_restore": "Segred0!", "senha_confirm": "Segred0!",
        "backup_intervalo": "15", "backup_duplo": "1", "backup_rede": "1",
        "backup_rede_caminho": r"Z:\\SEGURANCA\\NORMATECH-BACKUP",
        "rede_docs": "", "rede_docs_caminho": "", "tarefa_ativa": "", "tarefa_hora": "12:00"})
    check("V12 salvar configuração 303", r.status_code == 303)
    r = client.get("/configuracoes")
    check("V13 flash + valores salvos",
          "Configuração salva!" in r.text and "Empresa Teste Config" in r.text
          and "já configurada" in r.text)
    check("V14 app_settings.json gravado",
          (tmp / "app_settings.json").exists()
          and '"backup_intervalo_min": 15' in (tmp / "app_settings.json").read_text(encoding="utf-8"))
    cc = (tmp / "company_config.json").read_text(encoding="utf-8")
    check("V15 company_config.json gravado",
          (tmp / "company_config.json").exists() and "Empresa Teste Config" in cc)
    r = client.post("/configuracoes/salvar", data={
        "empresa": "X", "cnpj": "11111111111111", "local": "Y", "instrutor": "Z",
        "registro": "MTE 1/XX", "backup_intervalo": "15"})
    check("V16 CNPJ inválido re-renderiza com erro",
          r.status_code == 200 and "CNPJ inválido" in r.text)
    r = client.post("/configuracoes/salvar", data={
        "empresa": "X", "cnpj": "11.222.333/0001-81", "local": "Y", "instrutor": "Z",
        "registro": "MTE 44633/RJ", "backup_intervalo": "9999"})
    check("V17 intervalo fora da faixa", r.status_code == 200
          and "entre 1 e 720 minutos" in r.text)

    users.create_user("pedro", "Pedro Consulta", "consulta")
    client.get("/logout")
    _login(client, users, "pedro")
    r = client.get("/configuracoes")
    check("V18 consulta bloqueado em /configuracoes", r.status_code == 303)
    r = client.get("/")
    check("V19 menu sem Configurações p/ consulta", 'href="/configuracoes"' not in r.text)
    client.get("/logout")
    _login(client, users, "admin")

    # ── CRACHÁS: busca + paginação ───────────────────────────────
    repo = CrachaRepository()
    repo.save(repo.next_cracha_number(), eAna, "Ana V132", hoje_iso,
              [{"nr": "NR-35"}])
    repo.save(repo.next_cracha_number(), eBruno, "Bruno V132", hoje_iso,
              [{"nr": "NR-10"}])
    for i in range(25):
        repo.save(repo.next_cracha_number(), eAna, "Ana V132", hoje_iso,
                  [{"nr": "NR-35"}])
    r = client.get("/crachas")
    check("V20 crachas lista 200 (pagina 1)", r.status_code == 200
          and "Ana V132" in r.text and "27 crach" in r.text)
    r = client.get("/crachas", params={"busca": "ana"})
    check("V21 busca crachas filtra", "Ana V132" in r.text and "Bruno V132" not in r.text)
    r = client.get("/crachas", params={"busca": "NR-10"})
    check("V22 busca crachas por NR", "Bruno V132" in r.text and "Ana V132" not in r.text)
    r = client.get("/crachas")
    check("V23 paginacao crachas (27 -> 2 paginas)",
          "Página 1 de 2" in r.text and "page=2" in r.text)
    r = client.get("/crachas", params={"page": 2})
    check("V24 pagina 2 acessível (Bruno nela)",
          "Página 2 de 2" in r.text and "Bruno V132" in r.text)
    r = client.get("/crachas", params={"page": 5})
    check("V25 page fora da faixa satura", "Página 2 de 2" in r.text)

    # ── CARTÕES: busca + paginação ───────────────────────────────
    base = tmp / "cartoes"
    def _pdf(nome):
        p = base / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"%PDF-1.4\n%fake\n")
        return p
    _pdf("Func A/loteA.pdf")
    _pdf("Func B/loteB.pdf")
    for i in range(21):
        _pdf(f"Func A/extras{i:02d}.pdf")
    r = client.get("/cartoes")
    check("V26 cartoes lista 200 (pagina 1)", r.status_code == 200
          and "loteA.pdf" in r.text and "23 PDF(s)" in r.text)
    r = client.get("/cartoes", params={"page": 2})
    check("V26b cartoes pagina 2 (loteB nela)", "loteB.pdf" in r.text)
    r = client.get("/cartoes", params={"busca": "Func B"})
    check("V27 busca cartoes filtra pasta",
          "loteB.pdf" in r.text and "loteA.pdf" not in r.text)
    r = client.get("/cartoes")
    check("V28 paginacao cartoes (23 -> 2 paginas)",
          "Página 1 de 2" in r.text)

    # ── MODAL de confirmação ─────────────────────────────────────
    r = client.get("/emissao-lote")
    check("V29 lote tem data-confirmar-lista", "data-confirmar-lista" in r.text)
    r = client.get("/crachas/novo")
    check("V30 crachas novo tem modal + data-nome",
          "data-confirmar-lista" in r.text and "data-nome=" in r.text
          and "data-det=" in r.text)
    r = client.get("/cartoes/novo", params={"sel": f"{eAna},{eBruno}"})
    check("V31 cartoes novo tem modal", r.status_code == 200
          and "data-confirmar-lista" in r.text and 'data-nome="Ana V132"' in r.text)

    # ── sincronizar (sem rede) + log ─────────────────────────────
    r = client.post("/configuracoes/sincronizar")
    check("V32 sincronizar sem rede 303", r.status_code == 303)
    r = client.get("/configuracoes")
    check("V33 aviso sincronizar", "Ative o salvamento em rede" in r.text)
    r = client.post("/configuracoes/log/limpar")
    check("V34 limpar log 303", r.status_code == 303)
    r = client.get("/configuracoes")
    check("V35 log limpo", "Log de erros limpo." in r.text)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}):")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("TESTES WEB v1.32 OK")


if __name__ == "__main__":
    main()
