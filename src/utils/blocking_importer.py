"""
Importador de lista de bloqueios a partir de planilha Excel.

Formato: Coluna A = Nome, Coluna B = CPF (opcional, ajuda a desempatar
homonimos). Primeira linha (cabecalho) ignorada.

Casa cada linha com um funcionario cadastrado (CPF exato -> nome exato)
e retorna os funcionarios prontos para selecao na tela de cartoes.
"""

import re
from typing import List, Tuple


def _digits(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return re.sub(r"\D", "", s)


def _match_employee(nome: str, cpf: str, employee_repo):
    """Casa por CPF exato; sem CPF (ou sem match), por nome exato."""
    if cpf:
        for e in employee_repo.search(cpf, limit=5):
            if e.cpf and re.sub(r"\D", "", e.cpf) == cpf:
                return e
    for e in employee_repo.search(nome, limit=5):
        if e.nome.strip().lower() == nome.lower():
            return e
    return None


def import_blocking_list(filepath: str, employee_repo) -> Tuple[List, List[str]]:
    """
    Le a planilha e casa com funcionarios cadastrados.

    Retorna (encontrados: List[Employee], nao_encontrados: List[str]).
    Duplicatas (mesmo funcionario em varias linhas) contam uma unica vez.
    """
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("Biblioteca openpyxl nao instalada")

    from pathlib import Path

    path = Path(filepath)
    if not path.exists():
        raise RuntimeError(f"Arquivo nao encontrado: {filepath}")

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        encontrados, nao_encontrados = [], []
        seen = set()
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # cabecalho
            if not row or all(c is None for c in row):
                continue
            nome = str(row[0] or "").strip()
            cpf = _digits(row[1] if len(row) > 1 else None)
            if not nome:
                continue
            emp = _match_employee(nome, cpf, employee_repo)
            if emp:
                if emp.id not in seen:
                    seen.add(emp.id)
                    encontrados.append(emp)
            else:
                nao_encontrados.append(nome)
        return encontrados, nao_encontrados
    finally:
        wb.close()
