"""
Testes de certificados assinados (scan anexado) — HistoryRepository.

Uso:  python test_signed_docs.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core.history_repo import HistoryRepository
from src.core.models import CertificateRecord


def make_repo() -> HistoryRepository:
    tmp = Path(tempfile.mkdtemp(prefix="test_signed_"))
    return HistoryRepository(tmp / "test.db")


def make_cert(repo: HistoryRepository) -> int:
    rec = CertificateRecord(
        cert_number=f"CERT-{make_cert.seq:06d}",
        nr_code="NR-35",
        employee_id=1,
        funcionario_nome="Teste Assinado",
        funcionario_cpf="529.982.247-25",
        data_inicio="2026-01-01",
        data_fim="2026-01-01",
        carga_horaria=8,
        descricao_treinamento="Treinamento",
        campos_extra="{}",
    )
    make_cert.seq += 1
    return repo.save(rec)

make_cert.seq = 1


def test_attach_get_remove():
    repo = make_repo()
    cert_id = make_cert(repo)

    # sem documento
    assert repo.get_signed_doc(cert_id) is None
    rec = repo.get_all()[0]
    assert rec.has_signed_doc is False

    # anexa PDF fake
    data = b"%PDF-1.4 fake assinado"
    repo.attach_signed_doc(cert_id, data, "pdf")
    got = repo.get_signed_doc(cert_id)
    assert got == (data, "pdf"), got
    rec = repo.get_all()[0]
    assert rec.has_signed_doc is True
    print("[OK] anexar + ler + indicador na listagem")

    # substitui por JPG (jpeg normaliza p/ jpg)
    repo.attach_signed_doc(cert_id, b"\xff\xd8 fake jpg", "jpeg")
    data2, tipo2 = repo.get_signed_doc(cert_id)
    assert tipo2 == "jpg" and data2.startswith(b"\xff\xd8")
    print("[OK] substituir (jpeg -> jpg)")

    # remove
    repo.remove_signed_doc(cert_id)
    assert repo.get_signed_doc(cert_id) is None
    assert repo.get_all()[0].has_signed_doc is False
    print("[OK] remover")

    # validacoes
    try:
        repo.attach_signed_doc(cert_id, b"x", "exe")
        raise AssertionError("deveria recusar formato")
    except ValueError:
        pass
    try:
        repo.attach_signed_doc(cert_id, b"x" * (11 * 1024 * 1024), "pdf")
        raise AssertionError("deveria recusar >10MB")
    except ValueError:
        pass
    print("[OK] validacoes de formato e tamanho")


def test_migracao_db_antigo():
    """Banco criado SEM as colunas signed_* recebe ALTER TABLE automatico."""
    import sqlite3
    tmp = Path(tempfile.mkdtemp(prefix="test_migr_"))
    db = tmp / "old.db"
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cert_number TEXT UNIQUE NOT NULL,
                nr_code TEXT NOT NULL,
                employee_id INTEGER NOT NULL,
                funcionario_nome TEXT NOT NULL,
                funcionario_cpf TEXT NOT NULL,
                data_inicio TEXT NOT NULL,
                data_fim TEXT NOT NULL,
                carga_horaria INTEGER NOT NULL,
                descricao_treinamento TEXT NOT NULL,
                campos_extra TEXT,
                pdf_path TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            INSERT INTO certificates (cert_number, nr_code, employee_id, funcionario_nome,
                funcionario_cpf, data_inicio, data_fim, carga_horaria, descricao_treinamento)
                VALUES ('CERT-000001', 'NR-10', 1, 'Antigo', '111.111.111-11',
                        '2025-01-01', '2025-01-01', 8, 'Antigo');
        """)
    repo = HistoryRepository(db)  # _init_db roda a migracao
    rec = repo.get_all()[0]
    assert rec.cert_number == "CERT-000001" and rec.has_signed_doc is False
    repo.attach_signed_doc(rec.id, b"scan", "png")
    assert repo.get_signed_doc(rec.id) == (b"scan", "png")
    print("[OK] migracao de banco antigo (ALTER TABLE automatico)")


if __name__ == "__main__":
    test_attach_get_remove()
    test_migracao_db_antigo()
    print("\nTODOS OS TESTES PASSARAM")
