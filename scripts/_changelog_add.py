# -*- coding: utf-8 -*-
"""Insere entrada de versao no topo do CHANGELOG.md (evitar Set-Content PS5.1)."""
import sys
from pathlib import Path

ver, data = sys.argv[1], sys.argv[2]
secoes = sys.argv[3]  # texto ja formatado com ### secoes

p = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
txt = p.read_text(encoding="utf-8")
entry = f"## [{ver}] - {data}\n\n{secoes.strip()}\n\n"
p.write_text(entry + txt, encoding="utf-8")
print("CHANGELOG ok:", ver)
