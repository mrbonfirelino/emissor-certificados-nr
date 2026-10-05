"""
Utilitario para traducao de erros COM do Office (Excel/PowerPoint) em
mensagens amigaveis, usado na conversao XLSX/PPTX -> PDF.

O erro classico "(-2147352567, 'Excecao.')" e DISP_E_EXCEPTION: o Office
recusou a operacao por motivo generico (arquivo aberto/bloqueado, modo
protegido, impressora/PDF indisponivel). Traduzimos os casos conhecidos e
mantemos o detalhe original para o log.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")

# HResults conhecidos
_HR_CO_INIT = -2147221008          # CoInitialize nao foi chamado
_HR_CLASS_NOT_REG = -2147221164    # Classe nao registrada (Office ausente)
_HR_DISP_EXCEPTION = -2147352567   # 'Excecao.' generica do Office


def _hresult(e: Exception):
    """Extrai o hresult de um com_error (comtypes/pywin32), se houver."""
    for attr in ("hresult", "winerror"):
        hr = getattr(e, attr, None)
        if isinstance(hr, int):
            return hr
    args = getattr(e, "args", ())
    if args and isinstance(args[0], int):
        return args[0]
    return None


def traduz_erro_com(e: Exception, app: str = "Office") -> str:
    """
    Converte um erro COM em mensagem amigavel em PT-BR.
    `app` = "Excel" ou "PowerPoint" conforme o contexto.
    """
    nome = e.__class__.__name__
    if isinstance(e, PermissionError) or nome == "PermissionError":
        return ("O arquivo PDF está aberto em outro programa. "
                "Feche-o e tente novamente.")
    if nome in ("ImportError", "ModuleNotFoundError"):
        return ("Biblioteca comtypes nao instalada. "
                "Instale com: pip install comtypes")
    hr = _hresult(e)
    if hr == _HR_CLASS_NOT_REG:
        return (f"Microsoft {app} nao encontrado neste computador. "
                f"As listas exigem o {app} instalado (Office).")
    if hr == _HR_CO_INIT:
        return (f"Falha ao iniciar o {app} (COM nao inicializado). "
                "Tente novamente; se persistir, reinicie o sistema.")
    if hr == _HR_DISP_EXCEPTION:
        return (f"O {app} recusou a exportacao para PDF. Causas comuns: "
                "arquivo aberto em outro programa, arquivo bloqueado "
                "(modo protegido) ou PDF de destino sem permissao de "
                "escrita. Feche o documento e tente novamente.")
    return f"Falha ao exportar PDF via {app}: {e}"


def com_retry(fn: Callable[[], T], tentativas: int = 3,
              delay: float = 1.5) -> T:
    """
    Executa `fn` com ate `tentativas` tentativas. Repete apenas em erros
    transitorios de COM (CoInitialize/Excecao generica); propaga o ultimo
    erro traduzido (RuntimeError) se todas falharem.
    """
    ultimo: Exception | None = None
    for i in range(tentativas):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — traduzido abaixo
            ultimo = e
            hr = _hresult(e)
            transitivo = hr in (_HR_CO_INIT, _HR_DISP_EXCEPTION)
            if not transitivo or i == tentativas - 1:
                break
            time.sleep(delay)
    raise RuntimeError(traduz_erro_com(ultimo or Exception("desconhecido")))


def garantir_pasta(destino: Path) -> None:
    destino = Path(destino)
    if not destino.parent.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
