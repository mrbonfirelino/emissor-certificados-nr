"""Importador de veiculos via planilha Excel (2.29.7, v1.42.0).

Colunas (linha 1 = cabecalho, ignorada):
    A Modelo*        B Marca        C Tipo*            D Subtipo
    E Placa          F Proprio      G Contratante      H Empresa
    I Cor            J Carroceria   K Ano              L Fim do contrato
    M KM/L esperado  N Obs

Tipo aceita os rotulos comuns (Caminhao, Pickup, Carro, Van, Empilhadeira,
Retroescavadeira, Outros). Proprio aceita Sim/Nao/1/0. Empresa e localizada
por nome; se nao existir, e criada. Devolve (importados, erros) onde erros
e uma lista de strings 'Linha N: motivo'.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from src.core.frota_repo import TIPOS_VEICULO


def _sem_acentos(txt: str) -> str:
    mapa = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
                         "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC")
    return (txt or "").translate(mapa).strip().lower()


_ROTULO_TIPO = {
    "caminhao": "caminhao", "caminhoes": "caminhao",
    "pickup": "pickup", "picape": "pickup",
    "carro": "carro", "automovel": "carro",
    "van": "van", "furgao": "van",
    "empilhadeira": "empilhadeira",
    "retroescavadeira": "retroescavadeira",
    "outros": "outros", "outro": "outros",
}


def _txt(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0") and re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def _bool(val) -> bool:
    s = _sem_acentos(_txt(val))
    if s in ("nao", "n", "0", "false", "f"):
        return False
    return True


def _tipo(val) -> str:
    s = _sem_acentos(_txt(val))
    return _ROTULO_TIPO.get(s, s)


def _fim_contrato(val) -> str:
    """Aceita datetime do Excel, ISO ou dd/mm/aaaa -> ISO ("" se vazio)."""
    if val is None or not _txt(val):
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = _txt(val)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s  # deixa o repo/router validar


def _km_l(val):
    s = _txt(val).replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def import_veiculos_from_excel(filepath, frota_repo) -> Tuple[int, List[str]]:
    import openpyxl

    wb = openpyxl.load_workbook(str(filepath), read_only=True, data_only=True)
    ws = wb.active
    tipos_validos = dict(TIPOS_VEICULO)
    importados = 0
    erros: List[str] = []

    try:
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # cabecalho
            if not row or not any(row):
                continue

            def _col(idx):
                return row[idx] if idx < len(row) else None

            modelo = _txt(_col(0))
            tipo = _tipo(_col(2))
            if not modelo:
                erros.append(f"Linha {i + 1}: informe o modelo.")
                continue
            if tipo not in tipos_validos:
                erros.append(f"Linha {i + 1}: tipo inválido "
                             f"('{_txt(_col(2)) or '?'}').")
                continue

            empresa_nome = _txt(_col(7))
            empresa_id = None
            if empresa_nome:
                emp = frota_repo.get_empresa_por_nome(empresa_nome)
                if emp:
                    empresa_id = emp["id"]
                else:
                    try:
                        empresa_id = frota_repo.add_empresa(empresa_nome)
                    except ValueError:
                        emp = frota_repo.get_empresa_por_nome(empresa_nome)
                        empresa_id = emp["id"] if emp else None

            try:
                frota_repo.add_veiculo(
                    modelo, _txt(_col(1)), tipo,
                    _sem_acentos(_txt(_col(3))) or "",
                    _txt(_col(4)).upper(), _bool(_col(5)),
                    _txt(_col(6)), empresa_id, _txt(_col(13)),
                    cor=_txt(_col(8)),
                    carroceria=_sem_acentos(_txt(_col(9))) or "",
                    ano=_txt(_col(10)),
                    fim_contrato_aluguel=_fim_contrato(_col(11)),
                    km_l_esperado=_km_l(_col(12)))
                importados += 1
            except (ValueError, TypeError) as e:
                erros.append(f"Linha {i + 1}: {e}")
    finally:
        wb.close()
    return importados, erros
