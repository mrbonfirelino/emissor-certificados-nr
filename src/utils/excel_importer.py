import re
from pathlib import Path
from typing import Tuple, List
from src.ui.pages.funcoes import load_funcoes, save_funcoes


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


def _parse_nascimento(val):
    """Converte valor da planilha em ISO aaaa-mm-dd. Retorna None se vazio, ValueError se invalido."""
    if val is None or str(val).strip() == "":
        return None
    import datetime as _dt
    if isinstance(val, (_dt.datetime, _dt.date)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(s)


_TIPOS_SANGUINEOS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


def _parse_tipo_sanguineo(val):
    """Normaliza tipo sanguineo (A+, AB-, ...). None se vazio, ValueError se invalido."""
    if val is None or str(val).strip() == "":
        return None
    s = str(val).strip().upper().replace(" ", "")
    if s not in _TIPOS_SANGUINEOS:
        raise ValueError(s)
    return s


def _parse_ear(val) -> bool:
    """Converte Sim/Nao/S/N/1/0 em bool. Vazio -> False; desconhecido -> ValueError."""
    if val is None or str(val).strip() == "":
        return False
    s = str(val).strip().lower()
    if s.endswith(".0"):
        s = s[:-2]
    if s in {"sim", "s", "1", "true", "x"}:
        return True
    if s in {"nao", "não", "n", "0", "false"}:
        return False
    raise ValueError(s)


def import_employees_from_excel(
    filepath: str,
    employee_repo,
    name_col: int = 0,
    cpf_col: int = 1,
    funcao_col: int = 2,
    telefone_col: int = 3,
    nasc_col: int = 4,
    ts_col: int = 5,
    adm_col: int = 6,
    ctps_col: int = 7,
    ear_col: int = 8,
    skip_header: bool = True
) -> Tuple[int, int, int, List[str]]:
    """
    Importa funcionarios de um arquivo Excel (.xlsx).
    Colunas: A=Nome, B=CPF (opcional), C=Funcao (opcional), D=Telefone (opcional, 11 digitos),
    E=Data de Nascimento (opcional, dd/mm/aaaa), F=Tipo Sanguineo (opcional, ex: O+),
    G=Data de Admissao (opcional, dd/mm/aaaa), H=Registro CTPS (opcional),
    I=CNH EAR (opcional, Sim/Nao).

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
    funcoes_encontradas = set()

    def cell(row, col):
        return row[col] if col < len(row) else None

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 and skip_header:
            continue

        if not row or all(c is None for c in row):
            continue

        try:
            name_val = cell(row, name_col)
            cpf_val = cell(row, cpf_col)
            funcao_val = cell(row, funcao_col)
            tel_val = cell(row, telefone_col)
            nasc_val = cell(row, nasc_col)
            ts_val = cell(row, ts_col)
            adm_val = cell(row, adm_col)
            ctps_val = cell(row, ctps_col)
            ear_val = cell(row, ear_col)
        except IndexError:
            errors += 1
            error_details.append(f"Linha {i+1}: coluna fora do intervalo")
            continue

        name = _normalize_name(name_val)
        cpf = _normalize_cpf(cpf_val)
        funcao = str(funcao_val).strip() if funcao_val else None
        if funcao:
            funcoes_encontradas.add(funcao)
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

        nascimento_iso = None
        try:
            nascimento_iso = _parse_nascimento(nasc_val)
        except ValueError:
            errors += 1
            error_details.append(f"Linha {i+1}: data de nascimento invalida ({nasc_val}) - use dd/mm/aaaa")
            continue

        ts_iso = None
        try:
            ts_iso = _parse_tipo_sanguineo(ts_val)
        except ValueError:
            errors += 1
            error_details.append(f"Linha {i+1}: tipo sanguineo invalido ({ts_val}) - use A+, A-, B+, B-, AB+, AB-, O+ ou O-")
            continue

        admissao_iso = None
        try:
            admissao_iso = _parse_nascimento(adm_val)
        except ValueError:
            errors += 1
            error_details.append(f"Linha {i+1}: data de admissao invalida ({adm_val}) - use dd/mm/aaaa")
            continue

        ctps = str(ctps_val).strip() if ctps_val is not None and str(ctps_val).strip() != "" else None

        ear = False
        try:
            ear = _parse_ear(ear_val)
        except ValueError:
            errors += 1
            error_details.append(f"Linha {i+1}: CNH EAR invalida ({ear_val}) - use Sim ou Nao")
            continue

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

        result = employee_repo.create(name, cpf_formatted, funcao, None, telefone_val,
                                      data_nascimento=nascimento_iso, tipo_sanguineo=ts_iso,
                                      data_admissao=admissao_iso, registro_ctps=ctps, cnh_ear=ear)
        if result:
            imported += 1
        else:
            errors += 1
            error_details.append(f"Linha {i+1}: erro ao cadastrar '{name}'")

    wb.close()
    if funcoes_encontradas:
        try:
            funcoes_existentes = load_funcoes()
            funcoes_atualizadas = list(set(funcoes_existentes + list(funcoes_encontradas)))
            funcoes_atualizadas.sort()
            save_funcoes(funcoes_atualizadas)
        except Exception as e:
            error_details.append(f"Aviso: erro ao sincronizar funcoes: {e}")
    return imported, duplicates, errors, error_details
