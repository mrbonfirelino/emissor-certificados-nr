"""
Digitalizacao via WIA (Windows Image Acquisition) usando comtypes.

Isola todo o acesso COM ao scanner em funcoes testaveis (o dialogo WIA nativo
cuida da escolha do dispositivo e do preview). Falhas comuns (sem scanner,
usuario cancelou) viram excecoes claras com mensagem amigavel.

Fluxo real da API WIA Automation (validado via GetIDsOfNames):
  WIA.DeviceManager.DeviceInfos -> lista de scanners (Type == 1)
  DeviceInfos(i).Connect()      -> Device (conexao direta quando ha 1 so)
  CommonDialog.ShowSelectDevice -> Device (picker nativo quando ha varios)
  CommonDialog.ShowTransfer     -> ImageFile (dialogo de digitalizacao)
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


def _device_manager():
    try:
        import comtypes.client
    except ImportError as e:
        raise ScanError("comtypes nao instalado") from e
    return comtypes.client.CreateObject("WIA.DeviceManager", dynamic=True)


def _list_scanners() -> list:
    """Lista os dispositivos WIA do tipo scanner (DeviceType == 1)."""
    dm = _device_manager()
    scanners = []
    count = int(dm.DeviceInfos.Count)
    for i in range(1, count + 1):
        info = dm.DeviceInfos(i)
        try:
            dev_type = int(info.Type)
        except Exception:
            dev_type = 0
        if dev_type == 1:  # ScannerDeviceType
            scanners.append(info)
    return scanners


def _select_device(dialog):
    """Escolhe o scanner: conexao direta se houver um so; picker se houver varios.

    Retorna o Device conectado ou None se o usuario cancelar.
    """
    try:
        scanners = _list_scanners()
    except ScanError:
        raise
    except Exception as e:
        raise ScanError(f"Servico de digitalizacao (WIA) indisponivel: {_msg(e)}") from e

    if not scanners:
        raise ScanError(
            "Nenhum scanner encontrado. Conecte um scanner ou use 'Escolher arquivo / foto'."
        )

    if len(scanners) == 1:
        try:
            return scanners[0].Connect()
        except Exception as e:
            if _eh_cancelamento(e):
                return None
            raise ScanError(f"Nao foi possivel conectar ao scanner: {_msg(e)}") from e

    try:
        return dialog.ShowSelectDevice()
    except Exception as e:
        if _eh_cancelamento(e):
            return None
        raise ScanError(f"Nao foi possivel selecionar o scanner: {_msg(e)}") from e


def scan_one_page() -> Optional[bytes]:
    """
    Digitaliza uma pagina: conexao/picker do scanner + dialogo de digitalizacao.
    Retorna os bytes PNG da pagina, ou None se o usuario cancelar.
    """
    dialog = _wia_dialog()
    device = _select_device(dialog)
    if device is None:
        return None

    try:
        item = device.Items(1)
    except Exception as e:
        raise ScanError(f"Scanner sem item de digitalizacao: {_msg(e)}") from e

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
