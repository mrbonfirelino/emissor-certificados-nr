"""Testes do menu de Integracoes (Fábricas de Clientes) — v1.22.0 (roadmap 2.25).

Roda standalone: python test_integracoes.py
"""
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from src.core.integracao_repo import IntegracaoRepository
import src.core.integracao_repo as ir_mod
from src.core.employee_repo import EmployeeRepository
from src.core.history_repo import HistoryRepository
from src.ui.pages.vencimentos import filter_certs

PASSOS = []


def check(nome, cond):
    PASSOS.append((nome, bool(cond)))
    print(("[OK] " if cond else "[FALHOU] ") + nome)


def main():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        tmp.mkdir(parents=True, exist_ok=True)
        db = tmp / "test.db"

        er = EmployeeRepository(db_path=str(db))
        e1_id = er.create("Joao Pedro", "529.982.247-25", "Mecanico")
        e2_id = er.create("Maria Silva", None, "Eletricista")

        repo = IntegracaoRepository(db_path=str(db))

        # ── 1. Empresas CRUD ─────────────────────────────────
        fab1 = repo.add_empresa("Fábrica Alpha", "12.345.678/0001-90")
        fab2 = repo.add_empresa("Fabrica Beta")
        check("add_empresa retorna id", fab1 == 1 and fab2 == 2)
        try:
            repo.add_empresa("fabrica alpha")
            check("empresa duplicada rejeitada", False)
        except ValueError:
            check("empresa duplicada rejeitada", True)
        try:
            repo.add_empresa("   ")
            check("empresa sem nome rejeitada", False)
        except ValueError:
            check("empresa sem nome rejeitada", True)
        nomes = {e["nome"] for e in repo.list_empresas()}
        check("list_empresas", nomes == {"Fábrica Alpha", "Fabrica Beta"})

        # ── 2. Integrações + expiração ───────────────────────
        hoje = date.today()
        i1 = repo.add_integracao(employee_id=e1_id, empresa_id=fab1, tipo="Máquinas",
                                 data_inicio=(hoje - timedelta(days=30)).isoformat(),
                                 data_validade=(hoje + timedelta(days=60)).isoformat(),
                                 obs="Linha 2")
        try:
            repo.delete_empresa(fab1)
            check("delete_empresa em uso bloqueado", False)
        except ValueError:
            check("delete_empresa em uso bloqueado", True)
        i2 = repo.add_integracao(employee_id=e1_id, empresa_id=fab2, tipo="Assistência",
                                 data_inicio=(hoje - timedelta(days=400)).isoformat(),
                                 data_validade=(hoje - timedelta(days=35)).isoformat())
        i3 = repo.add_integracao(employee_id=e2_id, empresa_id=fab1, tipo=None,
                                 data_inicio=hoje.isoformat(),
                                 data_validade=(hoje + timedelta(days=5)).isoformat())
        check("add_integracao ids sequenciais", (i1, i2, i3) == (1, 2, 3))

        # valida datas erradas rejeitadas
        try:
            repo.add_integracao(employee_id=e1_id, empresa_id=fab1, tipo="X",
                                data_inicio=None, data_validade="data-ruim")
            check("data invalida rejeitada", False)
        except ValueError:
            check("data invalida rejeitada", True)

        all_int = repo.get_integracoes_with_expiration(only_latest=False)
        check("expiracao: 3 itens sem dedupe", len(all_int) == 3)
        vig = [i for i in all_int if i["id"] == i1][0]
        check("formato certificado (nr_code/cert_number)",
              vig["nr_code"] == "INTEGRAÇÃO" and vig["cert_number"] == "INT-000001")
        check("formato (descricao empresa — tipo)", vig["descricao_treinamento"] == "Fábrica Alpha — Máquinas")
        check("formato (dias/status)", 50 <= vig["dias_para_vencer"] <= 60 and vig["status"] in ("atenção", "proximo", "ok"))
        ven = [i for i in all_int if i["id"] == i2][0]
        check("vencida com dias negativo", ven["dias_para_vencer"] < 0 and ven["status"] == "vencido")
        sem_tipo = [i for i in all_int if i["id"] == i3][0]
        check("sem tipo: descricao = empresa", sem_tipo["descricao_treinamento"] == "Fábrica Alpha")

        latest = repo.get_integracoes_with_expiration()  # only_latest por (emp, empresa)
        pares = {(i["employee_id"], i["empresa_id"]) for i in latest}
        check("only_latest: 3 pares distintos", len(latest) == 3 and len(pares) == 3)

        # mesma emp+empresa com nova validade -> antiga sai
        i4 = repo.add_integracao(employee_id=e1_id, empresa_id=fab2, tipo="Renovada",
                                 data_inicio=hoje.isoformat(),
                                 data_validade=(hoje + timedelta(days=200)).isoformat())
        latest2 = repo.get_integracoes_with_expiration()
        par_fab2 = [i for i in latest2 if i["employee_id"] == e1_id and i["empresa_id"] == fab2][0]
        check("renovacao substitui (only_latest)", len(latest2) == 3 and par_fab2["id"] == i4)

        by_emp = repo.get_by_employee(e1_id)
        check("get_by_employee (3 integ e1)", len(by_emp) == 3)

        # ── 3. Update/delete + busca ─────────────────────────
        repo.update_integracao(i1, tipo="Máquinas Prensas", obs="")
        r1 = repo.get_by_id(i1)
        check("update_integracao", r1["tipo"] == "Máquinas Prensas" and r1["obs"] == "")
        repo.delete_integracao(i2)
        check("delete_integracao", repo.get_by_id(i2) is None)
        try:
            repo.delete_empresa(fab1)
            check("delete_empresa em uso apos deletar (ainda 2)", False)
        except ValueError:
            check("delete_empresa em uso apos deletar (ainda 2)", True)
        achou = repo.search("fabrica alpha", limit=10)
        check("search por empresa (normalize)", len(achou) == 2)
        achou2 = repo.search("529.982.247-25", limit=10)
        check("search por cpf", len(achou2) == 2)

        # ── 4. Merge com Vencimentos (filter_certs) ──────────
        hr = HistoryRepository(db_path=str(db))
        from src.core.models import CertificateRecord
        rec = {
            "cert_number": "2026-000001", "nr_code": "NR-35", "nr_name": "NR-35",
            "employee_id": e1_id, "funcionario_nome": "Joao Pedro", "funcionario_cpf": "529.982.247-25",
            "data_inicio": hoje.isoformat(), "data_fim": (hoje + timedelta(days=300)).isoformat(),
            "carga_horaria": "8", "descricao_treinamento": "Trabalho em Altura",
            "campos_extra": "{}",
        }
        hr.save(CertificateRecord(**rec))
        merged = hr.get_certificates_with_expiration() + repo.get_integracoes_with_expiration()
        so_int = filter_certs(merged, "INTEGRAÇÃO", "", "all")
        check("filter_certs isola INTEGRAÇÃO", len(so_int) == 3)
        tudo = filter_certs(merged, "TODAS", "", "all")
        check("filter_certs TODAS inclui cert+integ", len(tudo) == 4)

        # ── 5. Dashboard soma integrações ────────────────────
        orig_get_db = ir_mod.get_db_path
        ir_mod.get_db_path = lambda: str(db)
        try:
            stats = hr.get_dashboard_stats()
            # 1 cert (-300d ok) + integ i1 (+60 v30? 60>30 não conta) + i4 (+200) + i3 (+5 => vencer_7)
            check("dashboard: vencer_7 inclui integração", stats["vencer_7"] == 1)
            check("dashboard: vencidos 0 (integ vencida foi deletada)", stats["vencidos"] == 0)
        finally:
            ir_mod.get_db_path = orig_get_db

    falhas = [n for n, ok in PASSOS if not ok]
    print(f"\n{len(PASSOS) - len(falhas)}/{len(PASSOS)} testes OK")
    if falhas:
        for n in falhas:
            print(f"  FALHOU: {n}")
        sys.exit(1)


if __name__ == "__main__":
    main()
