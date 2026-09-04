"""
Testes dos filtros do historico (texto + NR + periodo + assinado),
do painel de indicadores (dashboard stats) e da exportacao xlsx/csv.

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
    repo = HistoryRepository(tmp / "test.db")
    # stub da tabela employees p/ os LEFT JOINs da expiracao (certs e ASOs)
    with repo._get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY, nome TEXT, cpf TEXT, funcao TEXT)""")
    return repo


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


def test_filtro_assinado():
    repo = make_repo()
    seed(repo)
    certs = repo.query(assinado="sim")
    assert [c.cert_number for c in certs] == ["CERT-000001"]
    certs = repo.query(assinado="nao")
    assert len(certs) == 4 and all(not c.has_signed_doc for c in certs)
    assert repo.count_query(assinado="sim") == 1
    assert repo.count_query(assinado="nao") == 4
    # combinado com texto
    certs = repo.query(query="jose", assinado="nao")
    assert [c.funcionario_nome for c in certs] == ["José Ferreira"]
    print("[OK] filtro assinado (sim/nao + combinado com texto)")


def test_dashboard_stats():
    import src.core.aso_repo as ar_mod
    from src.core.aso_repo import AsoRepository
    from datetime import date, timedelta
    repo = make_repo()
    seed(repo)
    # ASOs entram nos mesmos contadores (redireciona o repo interno p/ db do teste)
    # vigente no funcionario 2; vencido como unico ASO do funcionario 1
    # (only_latest=True mantem apenas o ASO mais recente de cada funcionario)
    aso = AsoRepository(db_path=repo.db_path)
    aso.save("ASO-000001", 2, "Periódico", date.today().isoformat(), validade_meses=12)
    aso.save("ASO-000002", 1, "Periódico",
             (date.today() - timedelta(days=400)).isoformat(), validade_meses=12)
    orig_get_db = ar_mod.get_db_path
    ar_mod.get_db_path = lambda: repo.db_path
    try:
        stats = repo.get_dashboard_stats()
    finally:
        ar_mod.get_db_path = orig_get_db
    assert stats["total"] == 5
    assert stats["assinados"] == 1
    assert dict(stats["por_nr"]) == {"NR-10": 2, "NR-12": 1, "NR-35": 2}
    assert stats["por_nr"][0][1] == 2  # ordenado por n DESC
    meses = dict(stats["por_mes"])
    assert meses.get("2026-01") == 1 and meses.get("2026-02") == 1
    assert meses.get("2026-03") == 1 and meses.get("2026-05") == 1
    # contagens de vencimento coerentes com a lista de expiracao (+ ASO vencido)
    certs = repo.get_certificates_with_expiration()
    vencidos = sum(1 for c in certs if c["dias_para_vencer"] < 0)
    v7 = sum(1 for c in certs if 0 <= c["dias_para_vencer"] <= 7)
    v30 = sum(1 for c in certs if 7 < c["dias_para_vencer"] <= 30)
    assert stats["vencidos"] == vencidos + 1  # ASO-000002 (400 dias, val. 12m)
    assert stats["vencer_7"] == v7
    assert stats["vencer_30"] == v30
    print("[OK] dashboard stats (total/assinados/NR/mes/vencimentos + ASO)")


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


def test_ultima_emissao_por_nr():
    repo = make_repo()
    # mesmo funcionario: NR-35 antiga (sem CPF, vencida) renovada com CPF + NR-10 vigente
    add(repo, 10, "NR-35", "Joao Pedro", "", "2024-01-10")
    add(repo, 11, "NR-35", "Joao Pedro", "529.982.247-25", "2027-01-01")
    add(repo, 12, "NR-10", "Joao Pedro", "529.982.247-25", "2027-01-01")

    certs = repo.get_certificates_with_expiration()
    assert len(certs) == 2, certs
    nr35 = next(c for c in certs if c["nr_code"] == "NR-35")
    assert nr35["data_fim"] == "2027-01-01" and nr35["funcionario_cpf"] == "529.982.247-25"
    assert all(c["dias_para_vencer"] >= 0 for c in certs)  # renovada nao fica vencida

    todos = repo.get_certificates_with_expiration(only_latest=False)
    assert len(todos) == 3
    assert any(c["dias_para_vencer"] < 0 for c in todos)  # a antiga so aparece sem dedupe

    stats = repo.get_dashboard_stats()
    assert stats["vencidos"] == 0  # dashboard nao conta emissao renovada como vencida
    print("[OK] vencimentos/dashboard: apenas a ultima emissao por NR (renovacao)")


if __name__ == "__main__":
    test_distinct_nrs()
    test_texto_normalizado()
    test_filtro_nr()
    test_filtro_periodo()
    test_combinados()
    test_sem_filtros_equivale_get_all()
    test_filtro_assinado()
    test_dashboard_stats()
    test_ultima_emissao_por_nr()
    test_exportador()
    print("\nTodos os testes de filtros/dashboard/export do historico passaram.")
