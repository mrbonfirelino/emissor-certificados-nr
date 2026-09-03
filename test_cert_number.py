"""
Teste standalone: numero do certificado presente em TODAS as paginas do PDF.
Gera um certificado real (2 folhas: texto + conteudo programatico) e verifica
via PyMuPDF que o numero aparece no texto de cada pagina.
"""
import sys
import os
import tempfile
from pathlib import Path
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

from src.core.models import CertificateData, NRTemplate
from src.core.pdf_generator import generate_certificate_pdf


def _make_data() -> CertificateData:
    return CertificateData(
        cert_number="2026-000123",
        nr_code="NR-35",
        nr_name="Trabalho em Altura",
        funcionario_nome="JOAO DA SILVA",
        funcionario_cpf="123.456.789-00",
        empresa_nome="ALTEC TREINAMENTOS",
        empresa_cnpj="12.345.678/0001-90",
        local_treinamento="Cordeiro",
        instrutor_nome="MARIA SOUZA",
        instrutor_registro_mte="44633/RJ",
        data_treinamento=date(2026, 9, 1),
        carga_horaria=8,
        descricao_treinamento="Treinamento NR-35",
        campos_extra={},
        conteudo_programatico=["Item A", "Item B"],
        assinaturas=[],
    )


def _make_template() -> NRTemplate:
    return NRTemplate(
        nr_code="NR-35",
        nr_name="Trabalho em Altura",
        carga_horaria_minima=8,
        descricao_padrao="Treinamento NR-35",
        conteudo_programatico=["Item A", "Item B", "Item C"],
        texto_certificado=(
            "Certificamos que {nome_funcionario}, CPF {cpf}, "
            "participou do treinamento de {nr_name} com carga horaria de "
            "{carga_horaria} horas em {data_treinamento}."
        ),
        assinaturas=[],
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "cert_teste.pdf"
        generate_certificate_pdf(_make_data(), _make_template(), pdf_path)

        doc = fitz.open(str(pdf_path))
        try:
            n_pages = len(doc)
            assert n_pages >= 2, f"esperado >=2 paginas, obtido {n_pages}"

            falhas = []
            for i, page in enumerate(doc, start=1):
                texto = page.get_text()
                # prefix CERT- vem do layout (certificate_number.prefix) +
                # sufixo numerico do cert_number
                if "CERT-000123" not in texto:
                    falhas.append(i)

            assert not falhas, f"numero do certificado ausente nas paginas: {falhas}"
            print(f"[OK] CERT-000123 presente nas {n_pages} paginas")
        finally:
            doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
