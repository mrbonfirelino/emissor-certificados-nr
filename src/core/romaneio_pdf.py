"""Gerador de documento de Romaneio (FASE: Romaneios).

Preenche uma copia do modelo xlsx (MODELO ROMANEIO) com openpyxl e exporta
PDF via Excel COM (quando disponivel). Sem COM, o .xlsx preenchido continua
disponivel para download.

Mapa de celulas do modelo (aba 'Romaneio'):
  AA2  -> No do romaneio (serial, exibido em cinza)
  P2   -> Descricao do servico (OS / cliente)
  B8   -> No ordem de compra      P8 -> Transportadora (CNPJ / CPF)
  B9   -> No ordem de servico     P9 -> Veiculo (modelo / placa)
  B10  -> Resp. elaboracao        P10 -> Motorista (nome)
  B11  -> Data elaboracao         P11 -> Data do embarque
  B13/P13/Y13 -> assinaturas (Resp. ALTEC / transportadora / data)
  Itens: bloco 1 linhas 18-34, bloco 2 linhas 39-64, bloco 3 linhas 66-81.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from openpyxl import load_workbook

from src.utils.paths import get_project_root

_LINHA_INI = {1: 18, 2: 39, 3: 66}
_LINHA_FIM = {1: 34, 2: 64, 3: 81}
# Colunas por campo (mesmas nos 3 blocos do modelo)
_COL = {"descricao": "D", "codigo": "R", "unidade": "S", "qtd": "U",
        "dimensoes": "W", "peso": "AA", "tipo": "S", "observacoes": "W"}


def _modelo_path() -> Optional[Path]:
    pasta = get_project_root() / "MODELO ROMANEIO"
    if not pasta.is_dir():
        return None
    for arq in sorted(pasta.glob("*.xlsx")):
        return arq
    return None


def gerar_romaneio_xlsx(destino: Path, dados: Dict[str, Any],
                        itens: List[Dict[str, Any]],
                        assinatura_altec: Optional[bytes] = None,
                        assinatura_transp: Optional[bytes] = None) -> Path:
    """Preenche o modelo e salva em `destino` (.xlsx). Retorna o caminho."""
    modelo = _modelo_path()
    if modelo is None:
        raise FileNotFoundError(
            "Modelo de romaneio nao encontrado (MODELO ROMANEIO/*.xlsx).")
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(modelo, destino)

    wb = load_workbook(destino)
    ws = wb["Romaneio"] if "Romaneio" in wb.sheetnames else wb.active

    def rotulo(coord: str, valor: str) -> None:
        atual = str(ws[coord].value or "")
        ws[coord] = f"{atual} {valor}".rstrip() if atual else str(valor)

    # Cabecalho
    cel_serial = ws["AA2"]
    cel_serial.value = dados.get("serial", "")
    from openpyxl.styles import Font
    cinza = Font(color="FF808080")
    for cel in cel_serial.parent[cel_serial.row]:
        pass  # mantem formatacao; aplica cinza so no serial
    cel_serial.font = cinza
    rotulo("P2", dados.get("os", "") or "")
    rotulo("B8", dados.get("ordem_compra", ""))
    rotulo("B9", dados.get("os", ""))
    rotulo("B10", dados.get("responsavel", ""))
    rotulo("B11", dados.get("data_elaboracao", ""))
    rotulo("P8", dados.get("transportadora", ""))
    rotulo("P9", f"{dados.get('veiculo', '')} / {dados.get('placa', '')}".strip(" /"))
    rotulo("P10", dados.get("motorista", ""))
    rotulo("P11", dados.get("data_embarque", ""))
    rotulo("P13", dados.get("responsavel", ""))          # ass. ALTEC
    rotulo("Y13", dados.get("data_embarque", ""))        # data

    # Assinaturas capturadas no navegador (PNG) — v1.62.0
    tmpdir = None
    if assinatura_altec or assinatura_transp:
        from openpyxl.drawing.image import Image as XLImage
        import tempfile
        tmpdir = Path(tempfile.mkdtemp(prefix="romaneio_ass_"))
        for _blob, _coord in ((assinatura_altec, "P12"),
                              (assinatura_transp, "Y12")):
            if not _blob:
                continue
            _tmp = tmpdir / f"ass_{_coord}.png"
            _tmp.write_bytes(_blob)
            try:
                from PIL import Image as PILImage
                _w, _h = PILImage.open(io.BytesIO(_blob)).size
            except Exception:
                _w, _h = 300, 110
            _img = XLImage(str(_tmp))
            _img.width = 150
            _img.height = max(10, int(_h * 150.0 / max(1, _w)))
            ws.add_image(_img, _coord)

    # Itens por bloco (1=Equipamentos, 2=Parafusos, 3=Componentes, 4+=Outros)
    por_bloco: Dict[int, List[Dict[str, Any]]] = {}
    for it in itens:
        try:
            b = int(it.get("bloco", 1) or 1)
        except Exception:
            b = 1
        por_bloco.setdefault(b, []).append(it)

    linha = _LINHA_INI[1]
    for bloco in sorted(por_bloco):
        limite = _LINHA_FIM.get(bloco)
        if limite is None:
            # bloco dinamico "Outros": escreve no bloco 3 ( ultima area livre)
            limite = _LINHA_FIM[3]
            bloco_destino = 3
        else:
            bloco_destino = bloco
        linha = _LINHA_INI[bloco_destino]
        for it in por_bloco[bloco]:
            if linha > limite:
                break
            ws[f"{_COL['codigo']}{linha}"] = it.get("codigo", "")
            ws[f"{_COL['descricao']}{linha}"] = it.get("descricao", "")
            ws[f"{_COL['unidade']}{linha}"] = it.get("unidade", "")
            ws[f"{_COL['qtd']}{linha}"] = it.get("qtd", "")
            ws[f"{_COL['dimensoes']}{linha}"] = it.get("dimensoes", "")
            ws[f"{_COL['peso']}{linha}"] = it.get("peso", "")
            ws[f"{_COL['tipo']}{linha}"] = it.get("tipo", "")
            ws[f"{_COL['observacoes']}{linha}"] = it.get("observacoes", "")
            linha += 1

    wb.save(destino)
    if tmpdir is not None:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return destino


def xlsx_para_pdf(xlsx_path: Path) -> Optional[Path]:
    """Exporta o xlsx para PDF via Excel COM. None se COM indisponivel/falhou."""
    from src.utils.com_pdf_errors import com_retry, garantir_pasta, traduz_erro_com
    from src.utils.error_log import log_error

    xlsx_path = Path(xlsx_path)
    pdf = xlsx_path.with_suffix(".pdf")
    garantir_pasta(pdf)

    def _uma_tentativa():
        import comtypes.client
        from src.utils.com_pdf_errors import remover_motw

        remover_motw(xlsx_path)
        excel = comtypes.client.CreateObject("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        try:
            wb = excel.Workbooks.Open(str(xlsx_path))
            try:
                wb.ExportAsFixedFormat(0, str(pdf))  # 0 = xlTypePDF
            finally:
                wb.Close(False)
        finally:
            excel.Quit()

    try:
        com_retry(_uma_tentativa)
    except Exception as e:  # noqa: BLE001
        log_error("romaneio-pdf-com", e)
        return None
    return pdf if pdf.exists() else None
