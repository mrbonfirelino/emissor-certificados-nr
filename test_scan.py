"""
Testes da digitalizacao (roadmap 2.9): combinacao de paginas em PDF unico,
ajustes de imagem e tratamento de erros do WIA (sem scanner necessario).

Uso:  python test_scan.py
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from PIL import Image

from src.utils.scanner_wia import pages_to_pdf_bytes, ScanError, ScanCancelado, _eh_cancelamento


def _png_bytes(cor, w=120, h=160) -> bytes:
    img = Image.new("RGB", (w, h), cor)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def test_pdf_unico():
    pdf = pages_to_pdf_bytes([_png_bytes((255, 0, 0)), _png_bytes((0, 255, 0))])
    assert pdf[:5] == b"%PDF-", pdf[:10]
    import pymupdf

    d = pymupdf.open(stream=pdf, filetype="pdf")
    try:
        assert len(d) == 2, len(d)  # 2 paginas num UNICO pdf
    finally:
        d.close()
    try:
        pages_to_pdf_bytes([])
        raise AssertionError("deveria exigir pelo menos 1 pagina")
    except ScanError:
        pass
    print("[OK] multi-pagina -> 1 PDF unico com 2 paginas; vazio rejeitado")


def test_wia_cancelamento():
    class COMErr(Exception):
        def __init__(self, hresult):
            super().__init__(f"hresult {hresult:#x}")
            self.hresult = hresult

    assert _eh_cancelamento(COMErr(0x80210064)) is True   # cancelado pelo usuario
    assert _eh_cancelamento(COMErr(0x8021006E)) is True   # nenhum dispositivo
    assert _eh_cancelamento(COMErr(0x80004005)) is False  # outro erro
    assert issubclass(ScanCancelado, ScanError)
    print("[OK] WIA: cancelamento/dispositivo ausente reconhecidos pelo hresult")


def test_ajustes_imagem():
    """Rotina equivalente a do ScanDialog: girar + brilho + contraste + crop."""
    from PIL import ImageEnhance

    img = Image.new("RGB", (200, 100), (128, 128, 128))

    girada = img.rotate(-90, expand=True)
    assert girada.size == (100, 200), girada.size

    brilho = ImageEnhance.Brightness(girada).enhance(1.2)
    claro = brilho.getpixel((10, 10))[0]
    assert claro > 128, claro

    contraste = ImageEnhance.Contrast(girada).enhance(0.5)
    assert contraste.size == girada.size

    recorte = girada.crop((10, 10, 50, 60))
    assert recorte.size == (40, 50), recorte.size
    print("[OK] ajustes: girar 90 (expand), brilho, contraste e crop")


if __name__ == "__main__":
    test_pdf_unico()
    test_wia_cancelamento()
    test_ajustes_imagem()
    print("\nTODOS OS TESTES PASSARAM")
