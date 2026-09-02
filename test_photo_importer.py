"""
Testes do casamento de fotos em massa (match_photos).

Uso:  python test_photo_importer.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core.models import Employee
from src.utils.photo_importer import match_photos


def make_employees():
    return [
        Employee(id=1, nome="Fabio Luiz Soares Ferreira", cpf="529.982.247-25"),
        Employee(id=2, nome="João D'Ávila Machado", cpf="111.444.777-35"),
        Employee(id=3, nome="Maria Souza", cpf=None),  # sem CPF: so casa por nome
    ]


def test_match():
    tmp = Path(tempfile.mkdtemp(prefix="test_fotos_"))
    # arquivos: CPF (com pontos), nome exato com acento/caixa diferente, sem match, nao-imagem
    (tmp / "529.982.247-25.jpg").write_bytes(b"x")
    (tmp / "JOAO D'AVILA MACHADO.png").write_bytes(b"x")
    (tmp / "maria souza.jpeg").write_bytes(b"x")
    (tmp / "Fulaninho De Tal.jpg").write_bytes(b"x")
    (tmp / "documento.pdf").write_bytes(b"x")  # ignorado (nao é imagem)

    casados, nao = match_photos(make_employees(), tmp)

    nomes = {c["employee"].nome: c["path"].name for c in casados}
    assert nomes["Fabio Luiz Soares Ferreira"] == "529.982.247-25.jpg", nomes
    assert nomes["João D'Ávila Machado"] == "JOAO D'AVILA MACHADO.png", nomes
    assert nomes["Maria Souza"] == "maria souza.jpeg", nomes
    assert len(casados) == 3, casados

    assert len(nao) == 1 and nao[0]["path"].name == "Fulaninho De Tal.jpg", nao
    assert "nome" in nao[0]["motivo"]
    print("[OK] fotos: CPF (com pontuacao), nome com acento/caixa e sem CPF; nao-imagens ignoradas")


def test_cpf_nao_cadastrado():
    tmp = Path(tempfile.mkdtemp(prefix="test_fotos2_"))
    (tmp / "99988877766.jpg").write_bytes(b"x")
    casados, nao = match_photos(make_employees(), tmp)
    assert not casados
    assert len(nao) == 1 and "CPF" in nao[0]["motivo"], nao
    print("[OK] fotos: CPF com 11 digitos nao cadastrado -> nao casado com motivo")


if __name__ == "__main__":
    test_match()
    test_cpf_nao_cadastrado()
    print("\nTODOS OS TESTES PASSARAM")
