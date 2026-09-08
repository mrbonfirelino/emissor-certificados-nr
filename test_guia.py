"""Testes do Guia de Introducao (v1.18.0, roadmap 2.21).

Rodar: python test_guia.py
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core import guia_generator as gg
from src.core.guia_generator import generate_guia_pdf, guia_path, guia_docx_path

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

        # v1.19.0: fonte DOCX em templates + fallback sem Word
        check("guia_docx_path aponta para templates",
              guia_docx_path().name == "GUIA_NORMATECH.docx"
              and "templates" in str(guia_docx_path()))
        check("GUIA_NORMATECH.docx existe no repo", guia_docx_path().exists())

        # v1.20.0: PDF pronto em templates (convertido no build) + fallback ReportLab
        orig_data = gg.get_data_dir
        orig_pronto = gg.guia_pdf_template_path
        gg.get_data_dir = lambda: tmp

        # sem PDF pronto em templates -> gera o embutido (ReportLab)
        gg.guia_pdf_template_path = lambda: tmp / "sem_guia" / "GUIA_NORMATECH.pdf"
        try:
            fallback = gg.garantir_guia()
        finally:
            gg.guia_pdf_template_path = orig_pronto
        check("garantir_guia sem PDF pronto gera ReportLab (fallback)",
              fallback.exists() and fallback.parent == tmp)

        # com PDF pronto em templates -> copia para data/
        (tmp / "GUIA_NORMATECH.pdf").unlink()  # prova que a copia veio do pronto
        pronto = tmp / "pronto" / "GUIA_NORMATECH.pdf"
        pronto.parent.mkdir(parents=True, exist_ok=True)
        generate_guia_pdf(pronto)
        gg.guia_pdf_template_path = lambda: pronto
        try:
            copiado = gg.garantir_guia()
        finally:
            gg.guia_pdf_template_path = orig_pronto
            gg.get_data_dir = orig_data
        check("garantir_guia copia PDF pronto do templates",
              copiado.exists() and copiado.parent == tmp
              and not pronto.samefile(copiado))

    falhas = [n for n, ok in PASSOS if not ok]
    print(f"\n{len(PASSOS) - len(falhas)}/{len(PASSOS)} testes OK")
    if falhas:
        print("FALHARAM:", falhas)
        sys.exit(1)


if __name__ == "__main__":
    main()
