"""
Log de erros central (data/error.log).

Captura excecoes que antes simplesmente desapareciam no exe windowed:
- callbacks do tkinter (report_callback_exception)
- threads de trabalho (threading.excepthook)
- chamadas manuais em pontos criticos (log_error)

O arquivo e truncado para os ultimos ~256KB quando passa de 1MB, evitando
crescimento infinito.
"""

import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.paths import get_data_dir

ERROR_LOG = get_data_dir() / "error.log"

_MAX_BYTES = 1024 * 1024        # 1MB -> trunca
_KEEP_BYTES = 256 * 1024        # mantem os ultimos 256KB


def log_error(contexto: str, exc: Optional[BaseException] = None):
    """Registra erro com timestamp, contexto e traceback (se houver excecao)."""
    try:
        linhas = [f"{datetime.now().isoformat(timespec='seconds')} | {contexto}"]
        if exc is not None:
            linhas.append(f"  {type(exc).__name__}: {exc}")
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            for l in tb.strip().splitlines():
                linhas.append(f"  {l}")
        linhas.append("")
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")
        _truncate_if_needed()
    except Exception:
        pass  # log nunca pode derrubar o app


def _truncate_if_needed():
    try:
        if ERROR_LOG.exists() and ERROR_LOG.stat().st_size > _MAX_BYTES:
            data = ERROR_LOG.read_bytes()
            with open(ERROR_LOG, "wb") as f:
                f.write(data[-_KEEP_BYTES:])
    except Exception:
        pass


def read_log_tail(max_lines: int = 200, max_bytes: int = 64 * 1024) -> str:
    """Le as ultimas linhas do error.log (para exibir no visualizador)."""
    try:
        if not ERROR_LOG.exists():
            return ""
        with open(ERROR_LOG, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            data = f.read()
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()
        if size > max_bytes and lines:
            lines = lines[1:]  # descarta linha parcial do corte
        return "\n".join(lines[-max_lines:])
    except Exception:
        return ""


def clear_log() -> bool:
    """Apaga o conteudo do error.log."""
    try:
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ERROR_LOG, "w", encoding="utf-8") as f:
            f.write("")
        return True
    except Exception:
        return False


def install_error_hooks(root_window):
    """
    Instala captura global de erros:
    - tkinter: excecoes dentro de callbacks de eventos (somem no exe windowed)
    - threading: excecoes em threads de trabalho (ex.: import em lote)
    """
    def _tk_callback(exc, val, tb):
        log_error("tkinter-callback", val)
        # mantem comportamento anterior (stderr) para dev
        try:
            import sys
            traceback.print_exception(exc, val, tb, file=sys.stderr)
        except Exception:
            pass

    def _thread_excepthook(args):
        log_error(f"thread ({args.thread.name if args.thread else '?'})", args.value)

    try:
        root_window.report_callback_exception = _tk_callback
    except Exception:
        pass
    try:
        threading.excepthook = _thread_excepthook
    except Exception:
        pass
