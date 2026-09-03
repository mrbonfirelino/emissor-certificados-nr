"""
Testes dos filtros do historico (texto + NR + periodo) e da exportacao xlsx/csv.

Uso:  python test_history_filters.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core.history_repo import HistoryRepository
from src.core.models import CertificateRecord


def make_repo() -> HistoryRepository:
    tmp = Path(tempfile.mkdtemp(prefix="test_hist_filters_"))
    return HistoryRepository(tmp / "test.db")


def add(repo: HistoryRepository, num: int, nr: str, nome: str, cpf: str,
        data_fim: str, signed: bool = False) -> int:
    rec = CertificateRecord(
        cert_number=f"CERT-{num:06d}",
        nr_code=nr,
        employee_id=1,
        funcionario_nome=nome,
        funcionario_cpf=cpf,
        data_inicio=data_fim,
        data_fim=data_fim,
        carga_horaria=8,
        descricao_treinamento="Treinamento",
        campos_extra="{}",
    )
    cid = repo.save(rec)
    if signed:
        repo.attach_signed_doc(cid, b"%PDF-fake", "pdf")
    return cid


def seed(repo: HistoryRepository):
    add(repo, 1, "NR-35", "José Machado", "529.982.247-25", "2026-01-10", signed=True)
    add(repo, 2, "NR-35", "Ana Souza", "111.222.333-44", "2026-03-15")
    add(repo, 3, "NR-10", "Carlos Lima", "555.666.777-88", "2026-02-20")
    add(repo, 4, "NR-12", "José Ferreira", "999.888.777-66", "2026-05-05")
    add(repo, 5, "NR-10", "Maria Oliveira", "123.456.789-00", "2025-12-31")


def test_distinct_nrs():
    repo = make_repo()
    seed(repo)
    nrs = repo.distinct_nrs()
    assert nrs == ["NR-10", "NR-12", "NR-35"], nrs
    print("[OK] distinct_nrs ordenado")


def test_texto_normalizado():
    repo = make_repo()
    seed(repo)
    certs = repo.query(query="jose machado")
    assert len(certs) == 1 and certs[0].funcionario_nome == "José Machado"
    certs = repo.query(query="jose")
    assert len(certs) == 2
    certs = repo.query(query="NR-12")
    assert len(certs) == 1 and certs[0].nr_code == "NR-12"
    certs = repo.query(query="CERT-000003")
    assert len(certs) == 1 and certs[0].cert_number == "CERT-000003"
    assert repo.search("ana") == repo.query(query="ana")
    assert repo.count_search("ana") == repo.count_query(query="ana")
    print("[OK] busca por texto (acentos) + delegacao search")


def test_filtro_nr():
    repo = make_repo()
    seed(repo)
    certs = repo.query(nr_code="NR-10")
    assert {c.nr_code for c in certs} == {"NR-10"} and len(certs) == 2
    assert repo.count_query(nr_code="NR-10") == 2
    certs = repo.query(nr_code="NR-99")
    assert certs == []
    print("[OK] filtro por NR exata")


def test_filtro_periodo():
    repo = make_repo()
    seed(repo)
    certs = repo.query(data_de="2026-01-01", data_ate="2026-03-31")
    assert sorted(c.data_fim for c in certs) == ["2026-01-10", "2026-02-20", "2026-03-15"]
    certs = repo.query(data_de="2026-04-01")
    assert [c.data_fim for c in certs] == ["2026-05-05"]
    certs = repo.query(data_ate="2025-12-31")
    assert [c.data_fim for c in certs] == ["2025-12-31"]
    print("[OK] filtro por periodo (de/ate)")


def test_combinados():
    repo = make_repo()
    seed(repo)
    certs = repo.query(query="jose", nr_code="NR-35", data_de="2026-01-01", data_ate="2026-06-30")
    assert [c.funcionario_nome for c in certs] == ["José Machado"]
    certs = repo.query(nr_code="NR-10", data_de="2026-01-01", data_ate="2026-03-01")
    assert [c.funcionario_nome for c in certs] == ["Carlos Lima"]
    assert repo.count_query(nr_code="NR-10", data_de="2026-01-01", data_ate="2026-03-01") == 1
    print("[OK] filtros combinados + count consistente")


def test_sem_filtros_equivale_get_all():
    repo = make_repo()
    seed(repo)
    assert repo.query(limit=100) == repo.get_all(limit=100)
    assert repo.count_query() == repo.count_all() == 5
    print("[OK] query sem filtros = listagem completa")


def test_exportador():
    from src.utils.history_exporter import export_certificates_to_file
    repo = make_repo()
    seed(repo)
    certs = repo.query(nr_code="NR-10", limit=100)

    tmp = Path(tempfile.mkdtemp(prefix="test_hist_export_"))

    xlsx = tmp / "hist.xlsx"
    n = export_certificates_to_file(certs, str(xlsx))
    assert n == 2
    import openpyxl
    wb = openpyxl.load_workbook(xlsx)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    assert rows[0][0] == "Numero" and rows[0][8] == "Assinado"
    assert [r[2] for r in rows[1:]] == ["Carlos Lima", "Maria Oliveira"]
    wb.close()

    csv_path = tmp / "hist.csv"
    certs2 = repo.query(limit=100)
    n2 = export_certificates_to_file(certs2, str(csv_path))
    assert n2 == 5
    raw = csv_path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    lines = [l for l in text.splitlines() if l.strip()]
    assert len(lines) == 6
    assert "José Machado" in text and ";" in text
    assert "SIM" in text

    print("[OK] exportacao xlsx + csv (BOM, ;, acentos)")


if __name__ == "__main__":
    test_distinct_nrs()
    test_texto_normalizado()
    test_filtro_nr()
    test_filtro_periodo()
    test_combinados()
    test_sem_filtros_equivale_get_all()
    test_exportador()
    print("\nTodos os testes de filtros/export do historico passaram.")
