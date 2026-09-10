"""Testes da Emissão em Lote (2.26) — fundacao de validade por certificado.

Roda standalone: python test_emissao_lote.py
"""

import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import src.core.certificate_service as cert_service_mod
import src.core.employee_repo as er_mod
from src.core.history_repo import HistoryRepository
from src.core.employee_repo import EmployeeRepository
from src.core.models import CertificateRecord, CompanyConfig, Employee
from src.core.network_sync import _cert_vencido

TMP = Path(tempfile.mkdtemp(prefix="normatech_lote_"))
TMP.mkdir(parents=True, exist_ok=True)
DB = TMP / "certificados.db"

FALHAS = []


def check(nome, cond):
    print(f"  [{'OK' if cond else 'FALHOU'}] {nome}")
    if not cond:
        FALHAS.append(nome)


def make_db():
    repo = EmployeeRepository(db_path=str(DB))
    repo.create("Ana Lote", "529.982.247-25", "Soldadora")
    repo.create("Bruno Lote", None, "Eletricista")  # sem CPF (bloqueado na UI)
    return repo


def t_validade_override():
    print("[1] validade por certificado (vencimentos)")
    from src.core.template_loader import load_all_templates
    val_template = load_all_templates()["NR-35"].validade_meses
    hr = HistoryRepository(db_path=str(DB))
    d300 = (date.today() - timedelta(days=300)).isoformat()

    hr.save(CertificateRecord(
        cert_number="CERT-900001", nr_code="NR-35", employee_id=1,
        funcionario_nome="Ana Lote", funcionario_cpf="529.982.247-25",
        data_inicio=d300, data_fim=d300, carga_horaria=8,
        descricao_treinamento="Trabalho em Altura", campos_extra="{}",
        pdf_path=None, validade_meses=6))
    hr.save(CertificateRecord(
        cert_number="CERT-900002", nr_code="NR-35", employee_id=1,
        funcionario_nome="Ana Lote", funcionario_cpf="529.982.247-25",
        data_inicio=d300, data_fim=d300, carga_horaria=8,
        descricao_treinamento="Trabalho em Altura", campos_extra="{}",
        pdf_path=None, validade_meses=None))

    exp = {c["cert_number"]: c for c in hr.get_certificates_with_expiration(only_latest=False)}
    r1 = exp["CERT-900001"]
    r2 = exp["CERT-900002"]
    check("override 6m gravado", r1["validade_meses"] == 6)
    check("override 6m: -300d + 6m = vencido", r1["status"] == "vencido")
    check(f"NULL usa o template ({val_template}m)", r2["validade_meses"] == val_template)
    check("NULL 12m: -300d + 12m = valido", r2["status"] != "vencido")


def t_cert_vencido():
    print("[2] network_sync._cert_vencido respeita override")
    d40 = (date.today() - timedelta(days=40)).isoformat()
    c_override = SimpleNamespace(nr_code="NR-35", data_fim=d40, validade_meses=1)
    c_template = SimpleNamespace(nr_code="NR-35", data_fim=d40, validade_meses=None)
    check("override 1m: -40d vencido", _cert_vencido(c_override) is True)
    check("NULL -> template 12m: -40d valido", _cert_vencido(c_template) is False)


def t_generate_com_validade(repo):
    print("[3] generate_certificate(validade_meses=6)")
    TMP_CERT = TMP / "certs_out"
    TMP_CERT.mkdir(parents=True, exist_ok=True)

    orig_cfg = cert_service_mod.load_company_config
    orig_dir = cert_service_mod.get_certificados_dir
    orig_db = er_mod.get_db_path
    cert_service_mod.load_company_config = lambda: CompanyConfig(
        empresa_nome="Empresa Teste", empresa_cnpj="11.222.333/0001-81",
        local_treinamento="Obra", instrutor_nome="Instrutor",
        instrutor_registro_mte="44633/RJ")
    cert_service_mod.get_certificados_dir = lambda: TMP_CERT
    er_mod.get_db_path = lambda: str(DB)
    try:
        svc = cert_service_mod.CertificateService()
        # repos internos do service apontam para o DB real do teste
        svc.history = HistoryRepository(db_path=str(DB))
        emp = Employee(id=1, nome="Ana Lote", cpf="529.982.247-25", funcao="Soldadora")
        path = svc.generate_certificate(
            nr_code="NR-35", employee=emp, data_treinamento=date.today(),
            carga_horaria=8, descricao_treinamento="Trabalho em Altura",
            campos_extra={}, validade_meses=6)
        check("PDF gerado", path is not None and Path(path).exists())
    finally:
        cert_service_mod.load_company_config = orig_cfg
        cert_service_mod.get_certificados_dir = orig_dir
        er_mod.get_db_path = orig_db

    hr = HistoryRepository(db_path=str(DB))
    recs = hr.get_all(limit=50)
    alvo = [r for r in recs if r.funcionario_nome == "Ana Lote" and r.data_inicio == date.today().isoformat()]
    check("registro do lote gravado", len(alvo) == 1)
    if alvo:
        check("validade_meses=6 no registro", alvo[0].validade_meses == 6)
        check("pdf_path aponta para tmp", str(TMP_CERT) in (alvo[0].pdf_path or ""))


def main():
    print(f"TMP: {TMP}")
    repo = make_db()
    t_validade_override()
    t_cert_vencido()
    t_generate_com_validade(repo)
    total = 11
    print(f"{total - len(FALHAS)}/{total} testes OK")
    if FALHAS:
        print("FALHAS:", FALHAS)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
