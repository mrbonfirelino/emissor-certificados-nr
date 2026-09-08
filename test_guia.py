"""Testes do Guia de Introducao (v1.18.0, roadmap 2.21).

Rodar: python test_guia.py
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core.guia_generator import generate_guia_pdf, guia_path

PASSOS = []


def check(nome, cond):
    PASSOS.append((nome, bool(cond)))
    print(f"[{'OK' if cond else 'FALHOU'}] {nome}")


def main():
    import fitz

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        tmp = Path(td)
        out = tmp / "GUIA_NORMATECH.pdf"

        generate_guia_pdf(out)
        check("guia gerado", out.exists() and out.stat().st_size > 5000)

        doc = fitz.open(out)
        check("multi-paginas", doc.page_count >= 3)
        txt = "\n".join(pg.get_text() for pg in doc)

        for termo in ("NormaTech", "Bem-vindo", "Funcionários", "Certificados",
                      "Vencimentos", "Cartões", "Crachás", "ASO", "EPI",
                      "Backups", "Documentos em Rede", "Configurações", "Atalhos",
                      "Ctrl+1", "F1"):
            check(f"contém '{termo}'", termo in txt)
        doc.close()

        check("guia_path aponta para data",
              guia_path().name == "GUIA_NORMATECH.pdf" and "data" in str(guia_path()))

    falhas = [n for n, ok in PASSOS if not ok]
    print(f"\n{len(PASSOS) - len(falhas)}/{len(PASSOS)} testes OK")
    if falhas:
        print("FALHARAM:", falhas)
        sys.exit(1)


if __name__ == "__main__":
    main()
