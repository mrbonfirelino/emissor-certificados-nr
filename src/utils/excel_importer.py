import re
from pathlib import Path
from typing import Tuple, List


def _normalize_cpf(val) -> str:
    """Extrai apenas digitos de um valor CPF."""
    if val is None:
        return ""
    s = str(val).strip()
    return re.sub(r'\D', '', s)


def _normalize_name(val) -> str:
    """Extrai e limpa nome."""
    if val is None:
        return ""
    return str(val).strip()


def _normalize_telefone(val) -> str:
    """Extrai apenas digitos do telefone (plano: DDD+numero, ex 21984209236)."""
    if val is None:
        return ""
    # openpyxl pode ler numero como float (21984209236.0)
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return re.sub(r'\D', '', s)


def _is_valid_cpf_digits(cpf: str) -> bool:
    """Valida se tem 11 digitos (validacao basica de formato)."""
    return len(cpf) == 11 and cpf.isdigit()


def _is_valid_telefone_digits(tel: str) -> bool:
    """Celular: 11 digitos, DDD valido, 3o digito 9."""
    if len(tel) != 11 or not tel.isdigit():
        return False
    if tel[2] != '9':
        return False
    ddd = int(tel[:2])
    if ddd < 11 or ddd > 91:
        return False
    return True


def import_employees_from_excel(
    filepath: str,
    employee_repo,
    name_col: int = 0,
    cpf_col: int = 1,
    funcao_col: int = 2,
    telefone_col: int = 3,
    skip_header: bool = True
) -> Tuple[int, int, int, List[str]]:
    """
    Importa funcionarios de um arquivo Excel (.xlsx).
    Colunas: A=Nome, B=CPF (opcional), C=Funcao (opcional), D=Telefone (opcional, 11 digitos).

    Retorna (importados, duplicados, erros, erros_detalhe).
    - importados: numero de novos funcionarios cadastrados
    - duplicados: funcionarios que ja existiam no banco
    - erros: linhas com dados invalidos
    - erros_detalhe: lista de mensagens de erro por linha
    """
    try:
        import openpyxl
    except ImportError:
        return 0, 0, 0, ["Biblioteca openpyxl nao instalada. Instale com: pip install openpyxl"]

    path = Path(filepath)
    if not path.exists():
        return 0, 0, 0, [f"Arquivo nao encontrado: {filepath}"]

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        return 0, 0, 0, [f"Erro ao abrir arquivo: {e}"]

    imported = 0
    duplicates = 0
    errors = 0
    error_details = []

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 and skip_header:
            continue

        if not row or all(c is None for c in row):
            continue

        try:
            name_val = row[name_col] if name_col < len(row) else None
            cpf_val = row[cpf_col] if cpf_col < len(row) else None
            funcao_val = row[funcao_col] if funcao_col < len(row) else None
            tel_val = row[telefone_col] if telefone_col < len(row) else None
        except IndexError:
            errors += 1
            error_details.append(f"Linha {i+1}: coluna fora do intervalo")
            continue

        name = _normalize_name(name_val)
        cpf = _normalize_cpf(cpf_val)
        funcao = str(funcao_val).strip() if funcao_val else None
        telefone = _normalize_telefone(tel_val)

        if not name:
            errors += 1
            error_details.append(f"Linha {i+1}: nome vazio")
            continue

        cpf_formatted = None
        if cpf:
            if not _is_valid_cpf_digits(cpf):
                errors += 1
                error_details.append(f"Linha {i+1}: CPF invalido ({cpf_val})")
                continue
            cpf_formatted = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

        telefone_val = None
        if telefone:
            if not _is_valid_telefone_digits(telefone):
                errors += 1
                error_details.append(f"Linha {i+1}: telefone invalido ({tel_val}) - use 11 digitos DDD+9XXXXXXXX")
                continue
            telefone_val = telefone

        # Verificar se ja existe funcionario com mesmo nome
        existing = employee_repo.search(name, limit=5)
        found = False
        for e in existing:
            if e.nome.lower() == name.lower():
                found = True
                break

        if found:
            duplicates += 1
            continue

        result = employee_repo.create(name, cpf_formatted, funcao, None, telefone_val)
        if result:
            imported += 1
        else:
            errors += 1
            error_details.append(f"Linha {i+1}: erro ao cadastrar '{name}'")

    wb.close()
    return imported, duplicates, errors, error_details
