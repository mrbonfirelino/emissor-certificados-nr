"""Testes v1.42.0: 2.30 (nav grupos, toasts, progresso, auditoria, downloads,
card 15 dias) + 2.29.7 (milhar, botão amarelo).

Padrao standalone: python test_web_v142.py
"""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import src.utils.paths as paths_mod
import src.core.employee_repo as er_mod
import src.core.history_repo as hr_mod
import src.core.aso_repo as aso_mod
import src.core.integracao_repo as integ_mod
import src.core.frota_repo as fr_mod
import src.core.certificate_service as cert_mod
import src.core.backup_manager as bm_mod
import src.utils.error_log as err_mod
import src.web.app as app_mod

FALHAS = []
TMP = Path(tempfile.mkdtemp(prefix="test_web_v142_"))


def check(nome, ok):
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")
    if not ok:
        FALHAS.append(nome)


def make_env():
    paths_mod.get_data_dir = lambda: TMP
    er_mod.get_db_path = lambda: TMP / "certificados.db"
    hr_mod.get_db_path = lambda: TMP / "certificados.db"
    aso_mod.get_db_path = lambda: TMP / "certificados.db"
    integ_mod.get_db_path = lambda: TMP / "certificados.db"
    fr_mod.get_db_path = lambda: TMP / "certificados.db"
    cert_mod.get_certificados_dir = lambda: TMP / "certificados"
    cert_mod.load_company_config = lambda: SimpleNamespace(
        empresa_nome="Empresa Teste LTDA", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Planta Teste", instrutor_nome="Instrutor Teste",
        instrutor_registro_mte="MTE 44633/RJ")
    app_mod.get_data_dir = lambda: TMP
    # log de erros em tmp
    err_mod.ERROR_LOG = TMP / "error.log"
    # BackupManager fake (nao toca em pastas reais)
    class _FakeManager:
        def __init__(self, *a, **k):
            pass
        def list_backups(self):
            return [TMP / "b1.db", TMP / "b2.db"]
        def create_backup(self):
            p = TMP / "b3.db"
            p.write_bytes(b"backup-fake")
            return p
    bm_mod.BackupManager = _FakeManager
    (TMP / "b1.db").write_bytes(b"x" * 2048)
    (TMP / "b2.db").write_bytes(b"y" * 4096)

    from src.web.app import create_app
    return create_app(db_path=TMP / "certificados.db",
                      secret_file=TMP / "secret.key")


def login_admin(client):
    from src.web.users_repo import UsersRepository
    users = UsersRepository()
    admin = users.get_by_username("admin")
    prov = users.reset_password(admin["id"])
    r = client.post("/login", data={"username": "admin", "password": prov},
                    follow_redirects=False)
    assert r.status_code == 303, "login admin falhou"
    client.post("/troca-senha", data={"atual": prov, "nova": "SenhaF0rte",
                                      "confirma": "SenhaF0rte"},
                follow_redirects=False)


def main():
    print("--- v1.42: infra 2.30 + frota 2.29.7 (web) ---")
    app = make_env()
    client = TestClient(app, follow_redirects=False)
    login_admin(client)

    from src.core.employee_repo import EmployeeRepository
    from src.core.history_repo import HistoryRepository, CertificateRecord
    er = EmployeeRepository()
    emp_id = er.create("Marcos Milhar", None, "Motorista")

    hoje = date.today()
    hr = HistoryRepository()
    hr.save(CertificateRecord(
        cert_number="CERT-000V42", nr_code="NR-35",
        employee_id=emp_id, funcionario_nome="Marcos Milhar",
        funcionario_cpf="", data_inicio=hoje.isoformat(),
        data_fim=(hoje + timedelta(days=12)).isoformat(),
        carga_horaria=8, descricao_treinamento="Trabalho em Altura",
        campos_extra="{}"))

    # frota com movimentacao (km grande para o milhar)
    from src.core.frota_repo import FrotaRepository
    repo = FrotaRepository()
    vid = repo.add_veiculo("2428", "Mercedes", "caminhao", "munck",
                           "V42AA11", True, "", None, "")
    repo.add_mov_saida(vid, hoje.isoformat(), "07:00", 100000,
                       "Obra", "", "", "Marcos", "Chefe")

    # 2.30.1 nav em grupos + overlay de progresso
    r = client.get("/")
    check("V01 dashboard 200", r.status_code == 200)
    check("V02 nav em grupos (dropdown)", "nav-grupo" in r.text
          and "Cadastros" in r.text)
    check("V03 overlay de progresso no base", "ov-progresso" in r.text)

    # toasts no lugar de banners
    r = client.post("/frota/criar", data={
        "modelo": "", "marca": "", "tipo": "carro", "subtipo": "",
        "placa": "", "proprio": "1", "contratante": "", "empresa_id": "",
        "obs": ""}, follow_redirects=False)
    r = client.get("/frota")
    check("V04 flash renderiza como toast", "toast" in r.text)

    # 2.29.7 milhar + botão amarelo
    r = client.get(f"/frota/{vid}")
    check("V05 KM com ponto de milhar", "100.000" in r.text)
    check("V06 botão de abastecimento amarelo", "btn amarelo" in r.text)
    check("V07 abast a partir da ficha (?veiculo=)",
          f"/frota/abastecimentos/novo?veiculo={vid}" in r.text)

    # 2.30.2 auditoria: per + busca por data + coluna Ação truncada
    r = client.get("/auditoria?per=10")
    check("V08 auditoria per=10", r.status_code == 200
          and 'value="10"' in r.text)
    r = client.get(f"/auditoria?data_de={hoje.isoformat()}"
                   f"&data_ate={hoje.isoformat()}")
    check("V09 auditoria busca por data", r.status_code == 200
          and "Milhar" not in r.text or "frota" in r.text)
    check("V10 coluna Ação truncada (col-acao)", "col-acao" in r.text)

    # download do log de erros
    (TMP / "error.log").write_text("2026-09-17 ERRO de teste\n",
                                   encoding="utf-8")
    r = client.get("/configuracoes/log/download")
    check("V11 download do log", r.status_code == 200
          and "ERRO de teste" in r.text)

    # download de backups (admin)
    r = client.get("/backup")
    check("V12 lista backups com botão Baixar", "Baixar" in r.text
          and "/backup/b1.db/download" in r.text)
    r = client.get("/backup/b2.db/download")
    check("V13 download backup", r.status_code == 200
          and b"y" * 4096 in r.content)
    r = client.get("/backup/../../secret.key/download")
    check("V14 anti-traversal no download",
          r.status_code != 200 or b"secret" not in r.content)
    r = client.post("/backup/criar", follow_redirects=False)
    check("V15 criar backup fake -> 303", r.status_code == 303)

    # 2.30.3 card de 15 dias em Vencimentos (ASO: exame -18d + 1 mes = vence em ~12d)
    from src.core.aso_repo import AsoRepository
    aso_repo = AsoRepository()
    aso_repo.save(aso_repo.next_aso_number(), emp_id, "Periódico",
                  (hoje - timedelta(days=18)).isoformat(), 1)
    r = client.get("/vencimentos")
    check("V16 card 8 a 15 dias", "Vencem em 8 a 15 dias" in r.text
          and "/vencimentos?periodo=dias_15" in r.text)
    import re as _re
    m = _re.search(r'href="/vencimentos\?periodo=dias_15"[^>]*>\s*'
                   r'<span class="num-p">(\d+)</span>', r.text)
    check("V18 numero do card 15 dias reflete o item",
          m and int(m.group(1)) >= 1)

    # filtro dias_15 retorna o item
    r = client.get("/vencimentos?periodo=dias_15")
    check("V19 filtro dias_15 mostra o item", "Marcos Milhar" in r.text)

    print("\n--- permissao consulta: auditoria/config continua admin ---")
    from src.web.users_repo import UsersRepository
    users = UsersRepository()
    users.create_user("vera", "Vera Consulta", "consulta")
    vp = users.reset_password(users.get_by_username("vera")["id"])
    c2 = TestClient(app=app, follow_redirects=False)
    c2.post("/login", data={"username": "vera", "password": vp},
            follow_redirects=False)
    c2.post("/troca-senha", data={"atual": vp, "nova": "SenhaV3ra",
                                  "confirma": "SenhaV3ra"},
            follow_redirects=False)
    r = c2.get("/auditoria")
    check("V20 consulta NÃO acessa auditoria", r.status_code == 303)
    r = c2.get("/backup/b1.db/download")
    check("V21 consulta NÃO baixa backup", r.status_code == 303)
    r = c2.get("/configuracoes/log/download")
    check("V22 consulta NÃO baixa log", r.status_code == 303)

    print()
    if FALHAS:
        print(f"FALHAS ({len(FALHAS)}): {', '.join(FALHAS)}")
        sys.exit(1)
    print(f"TODOS OS 22 CHECKS V142 PASSARAM")


if __name__ == "__main__":
    main()
