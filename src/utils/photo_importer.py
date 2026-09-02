"""
Casamento de fotos 3x4 em massa com funcionarios cadastrados.

Regra: nome do arquivo SEM extensao ->
- se tiver 11 digitos -> CPF (comparacao por digitos)
- senao -> nome exato do funcionario (ignorando acentos/maiusculas/espacos extras)

Nao casou -> lista de nao encontrados com motivo.
"""

import re
import unicodedata
from pathlib import Path
from typing import List, Tuple

EXTENSOES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def match_photos(employees, folder) -> Tuple[List[dict], List[dict]]:
    """
    Retorna (casados, nao_casados):
    - casados: [{"path": Path, "employee": Employee}]
    - nao_casados: [{"path": Path, "motivo": str}]
    """
    por_cpf = {}
    por_nome = {}
    for e in employees:
        if getattr(e, "cpf", None):
            por_cpf[re.sub(r"\D", "", e.cpf)] = e
        por_nome[_norm(e.nome)] = e

    casados, nao = [], []
    for p in sorted(Path(folder).iterdir()):
        if not p.is_file() or p.suffix.lower() not in EXTENSOES:
            continue
        stem = p.stem.strip()
        digits = re.sub(r"\D", "", stem)
        emp = None
        if len(digits) == 11:
            emp = por_cpf.get(digits)
            motivo = "CPF nao cadastrado"
        else:
            emp = por_nome.get(_norm(stem))
            motivo = "nome nao encontrado no cadastro"
        if emp is not None:
            casados.append({"path": p, "employee": emp})
        else:
            nao.append({"path": p, "motivo": motivo})
    return casados, nao
