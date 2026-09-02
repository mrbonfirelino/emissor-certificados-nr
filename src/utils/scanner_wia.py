"""
Digitalizacao via WIA (Windows Image Acquisition) usando comtypes.

Isola todo o acesso COM ao scanner em funcoes testaveis (o dialogo WIA nativo
cuida da escolha do dispositivo e do preview). Falhas comuns (sem scanner,
usuario cancelou) viram excecoes claras com mensagem amigavel.
"""

from typing import List, Optional

# FormatID WIA para PNG sem perdas
WIA_FORMAT_PNG = "{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}"


class ScanError(RuntimeError):
    """Erro de digitalizacao com mensagem amigavel."""


class ScanCancelado(ScanError):
    """Usuario fechou/cancelou o dialogo do scanner."""


def _wia_dialog():
    try:
        import comtypes.client
    except ImportError as e:
        raise ScanError("comtypes nao instalado") from e
    try:
        return comtypes.client.CreateObject("WIA.CommonDialog", dynamic=True)
    except Exception as e:
        raise ScanError("Servico de digitalizacao (WIA) indisponivel neste Windows.") from e


def scan_one_page() -> Optional[bytes]:
    """
    Abre o dialogo nativo do scanner (escolha de dispositivo + digitalizacao)
    e retorna os bytes PNG da pagina, ou None se o usuario cancelar.
    """
    dialog = _wia_dialog()
    try:
        item = dialog.ShowSelectItem()
    except Exception as e:
        # cancelamento no WIA costuma vir como COMError 0x8021006E/0x80210064
        if _eh_cancelamento(e):
            return None
        raise ScanError(f"Nao foi possivel selecionar o scanner: {_msg(e)}") from e
    if item is None:
        return None
    try:
        image_file = dialog.ShowTransfer(item, WIA_FORMAT_PNG, False)
    except Exception as e:
        if _eh_cancelamento(e):
            return None
        raise ScanError(f"Falha ao digitalizar: {_msg(e)}") from e
    if image_file is None:
        return None
    try:
        data = image_file.FileData.BinaryData
        return bytes(data)
    except Exception as e:
        raise ScanError(f"Falha ao ler a pagina digitalizada: {_msg(e)}") from e


def _eh_cancelamento(e: BaseException) -> bool:
    hresult = getattr(e, "hresult", None) or getattr(e, "args", [None])[0]
    if isinstance(hresult, int):
        # 0x80210064: operacao cancelada pelo usuario; 0x8021006E: nenhum dispositivo
        return hresult in (0x80210064, 0x8021006E)
    txt = str(e).lower()
    return "cancel" in txt or "0x80210064" in txt


def _msg(e: BaseException) -> str:
    return str(e) or type(e).__name__


def pages_to_pdf_bytes(pages: List[bytes]) -> bytes:
    """Combina paginas PNG/JPG (bytes) em um unico PDF (bytes)."""
    import io

    from PIL import Image

    if not pages:
        raise ScanError("Nenhuma pagina para combinar")
    imgs = []
    try:
        for p in pages:
            imgs.append(Image.open(io.BytesIO(p)).convert("RGB"))
        out = io.BytesIO()
        imgs[0].save(out, format="PDF", save_all=True, append_images=imgs[1:])
        return out.getvalue()
    finally:
        for im in imgs:
            try:
                im.close()
            except Exception:
                pass
