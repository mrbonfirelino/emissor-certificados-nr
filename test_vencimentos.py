"""
Testes do filtro de vencimentos (filter_certs).

Uso:  python test_vencimentos.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.ui.pages.vencimentos import filter_certs


def cert(nome, nr, dias):
    return {
        "employee_id": 1, "funcionario_nome": nome, "funcionario_cpf": "000.000.000-00",
        "nr_code": nr, "dias_para_vencer": dias, "status": "ok", "funcionario_funcao": "",
    }


def test_periodos():
    certs = [
        cert("Vencido", "NR-35", -30),
        cert("VenceOntem", "NR-35", -1),
        cert("Hoje", "NR-35", 0),
        cert("D3", "NR-35", 3),
        cert("D10", "NR-10", 10),
        cert("D45", "NR-10", 45),
        cert("D200", "NR-10", 200),
    ]

    # 7 dias: SOMENTE 0..7 (vencidos nao podem aparecer)
    r = filter_certs(certs, "TODAS", "", "dias_7")
    nomes = [c["funcionario_nome"] for c in r]
    assert nomes == ["Hoje", "D3"], nomes

    r = filter_certs(certs, "TODAS", "", "dias_15")
    assert [c["funcionario_nome"] for c in r] == ["Hoje", "D3", "D10"]

    r = filter_certs(certs, "TODAS", "", "mes_1")
    assert [c["funcionario_nome"] for c in r] == ["Hoje", "D3", "D10"]

    r = filter_certs(certs, "TODAS", "", "meses_3")
    assert [c["funcionario_nome"] for c in r] == ["Hoje", "D3", "D10", "D45"]

    # vencidos: somente negativos
    r = filter_certs(certs, "TODAS", "", "vencidos")
    assert [c["funcionario_nome"] for c in r] == ["Vencido", "VenceOntem"]

    # todos
    r = filter_certs(certs, "TODAS", "", "all")
    assert len(r) == 7
    print("[OK] periodos: vencidos fora dos filtros futuros (7/15/30/90)")


def test_nr_busca():
    certs = [
        cert("Joao", "NR-35", 3),
        cert("Maria", "NR-10", 300),
    ]
    r = filter_certs(certs, "NR-35", "", "all")
    assert [c["funcionario_nome"] for c in r] == ["Joao"]
    r = filter_certs(certs, "TODAS", "maria", "all")
    assert [c["funcionario_nome"] for c in r] == ["Maria"]
    r = filter_certs(certs, "TODAS", "nr-10", "all")
    assert [c["funcionario_nome"] for c in r] == ["Maria"]
    print("[OK] filtros por NR e busca textual")


if __name__ == "__main__":
    test_periodos()
    test_nr_busca()
    print("\nTODOS OS TESTES PASSARAM")
