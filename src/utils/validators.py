import re
from datetime import date, datetime
from typing import Optional


def validar_cpf(cpf: str) -> bool:
    """Valida CPF (formato e dígitos verificadores)."""
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    # Calcula primeiro dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    
    # Calcula segundo dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    
    return cpf[-2:] == f"{digito1}{digito2}"


def formatar_cpf(cpf: str) -> str:
    """Formata CPF para XXX.XXX.XXX-XX."""
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ (formato e dígitos verificadores)."""
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    
    # Primeiro dígito
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    digito1 = 11 - (soma % 11)
    if digito1 >= 10:
        digito1 = 0
    
    # Segundo dígito
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    digito2 = 11 - (soma % 11)
    if digito2 >= 10:
        digito2 = 0
    
    return cnpj[-2:] == f"{digito1}{digito2}"


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ para XX.XXX.XXX/XXXX-XX."""
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj


def validar_data(data_str: str) -> Optional[date]:
    """Valida e converte string para date (DD/MM/YYYY)."""
    try:
        return datetime.strptime(data_str, "%d/%m/%Y").date()
    except ValueError:
        return None


def formatar_data(data: date) -> str:
    """Formata date para DD/MM/YYYY."""
    return data.strftime("%d/%m/%Y")


def validar_registro_mte(registro: str) -> bool:
    """Valida formato de registro MTE (ex: 44633/RJ ou MTE 44633/RJ)."""
    pattern = r'^(MTE\s+)?\d{1,6}/[A-Z]{2}$'
    return bool(re.match(pattern, registro.strip(), re.IGNORECASE))


def formatar_registro_mte(registro: str) -> str:
    """Formata registro MTE para padrão MTE XXXXX/UF."""
    registro = registro.strip().upper()
    # Se já tem MTE, mantém; senão adiciona
    if registro.startswith("MTE"):
        match = re.match(r'MTE\s*(\d{1,6})\s*/?\s*([A-Z]{2})', registro)
    else:
        match = re.match(r'(\d{1,6})\s*/\s*([A-Z]{2})', registro)
    if match:
        return f"MTE {match.group(1)}/{match.group(2)}"
    return registro


def validar_carga_horaria(carga: str) -> Optional[int]:
    """Valida carga horária (número inteiro positivo)."""
    try:
        valor = int(carga)
        return valor if valor > 0 else None
    except ValueError:
        return None