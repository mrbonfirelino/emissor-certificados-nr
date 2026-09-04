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

from src.utils import scanner_wia
from src.utils.scanner_wia import (
    pages_to_pdf_bytes, ScanError, ScanCancelado, _eh_cancelamento, scan_one_page,
)


# ── fakes do WIA (API real: DeviceManager/Connect/ShowSelectDevice/ShowTransfer) ──

class COMErr(Exception):
    def __init__(self, hresult):
        super().__init__(f"hresult {hresult:#x}")
        self.hresult = hresult


class FakeFileData:
    def __init__(self, data):
        self.BinaryData = data


class FakeImageFile:
    def __init__(self, data):
        self.FileData = FakeFileData(data)


class FakeItems:
    def __call__(self, idx):
        assert idx == 1, "deve pedir o item 1 (flatbed)"
        return "ITEM-1"


class FakeDevice:
    def __init__(self, transfer_data=None, transfer_exc=None):
        self.Items = FakeItems()
        self._transfer_data = transfer_data
        self._transfer_exc = transfer_exc


class FakeDialog:
    def __init__(self, device=None, select_exc=None, transfer_data=None, transfer_exc=None):
        self._device = device
        self._select_exc = select_exc
        self._transfer_data = transfer_data
        self._transfer_exc = transfer_exc
        self.select_chamado = False

    def ShowSelectDevice(self):
        self.select_chamado = True
        if self._select_exc:
            raise self._select_exc
        return self._device

    def ShowTransfer(self, item, fmt, cancel_error):
        assert item == "ITEM-1"
        if self._transfer_exc:
            raise self._transfer_exc
        return FakeImageFile(self._transfer_data)


class FakeDeviceInfo:
    def __init__(self, dev_type, device):
        self.Type = dev_type
        self._device = device

    def Connect(self):
        return self._device


class FakeDeviceInfos:
    def __init__(self, infos):
        self._infos = infos
        self.Count = len(infos)

    def __call__(self, idx):
        return self._infos[idx - 1]


class FakeDeviceManager:
    def __init__(self, infos):
        self.DeviceInfos = FakeDeviceInfos(infos)


def _patch_wia(monkey, dm, dialog):
    monkey["dm"] = scanner_wia._device_manager
    monkey["dlg"] = scanner_wia._wia_dialog
    scanner_wia._device_manager = lambda: dm
    scanner_wia._wia_dialog = lambda: dialog


def _restore_wia(monkey):
    scanner_wia._device_manager = monkey["dm"]
    scanner_wia._wia_dialog = monkey["dlg"]


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


def test_wia_fluxo():
    """Fluxo novo (v1.10.0): DeviceManager -> Connect/ShowSelectDevice -> ShowTransfer."""
    png = _png_bytes((0, 0, 255))
    monkey = {}

    # 1) sem scanner -> erro amigavel
    _patch_wia(monkey, FakeDeviceManager([]), FakeDialog())
    try:
        try:
            scan_one_page()
            raise AssertionError("deveria falhar sem scanner")
        except ScanError as e:
            assert "Nenhum scanner encontrado" in str(e)
    finally:
        _restore_wia(monkey)

    # 2) um scanner -> conecta direto (sem picker) e digitaliza
    dev = FakeDevice(transfer_data=png)
    dlg = FakeDialog(transfer_data=png)
    _patch_wia(monkey, FakeDeviceManager([FakeDeviceInfo(1, dev)]), dlg)
    try:
        data = scan_one_page()
        assert data == png
        assert dlg.select_chamado is False, "nao deve abrir picker com 1 scanner so"
    finally:
        _restore_wia(monkey)

    # 3) dois scanners -> picker nativo (ShowSelectDevice) e digitaliza
    dlg2 = FakeDialog(device=FakeDevice(transfer_data=png), transfer_data=png)
    _patch_wia(monkey, FakeDeviceManager([FakeDeviceInfo(1, dev), FakeDeviceInfo(1, dev)]), dlg2)
    try:
        data = scan_one_page()
        assert data == png
        assert dlg2.select_chamado is True
    finally:
        _restore_wia(monkey)

    # 4) cancelamento no ShowTransfer -> None
    dlg3 = FakeDialog(transfer_exc=COMErr(0x80210064))
    _patch_wia(monkey, FakeDeviceManager([FakeDeviceInfo(1, FakeDevice())]), dlg3)
    try:
        assert scan_one_page() is None
    finally:
        _restore_wia(monkey)

    # 5) cancelamento no picker -> None
    dlg4 = FakeDialog(select_exc=COMErr(0x80210064))
    _patch_wia(monkey, FakeDeviceManager([FakeDeviceInfo(1, FakeDevice()), FakeDeviceInfo(1, FakeDevice())]), dlg4)
    try:
        assert scan_one_page() is None
    finally:
        _restore_wia(monkey)

    print("[OK] WIA: sem scanner / conexao direta / picker / cancelamentos")


if __name__ == "__main__":
    test_pdf_unico()
    test_wia_cancelamento()
    test_ajustes_imagem()
    test_wia_fluxo()
    print("\nTODOS OS TESTES PASSARAM")
