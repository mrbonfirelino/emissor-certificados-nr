"""Reinicio do aplicativo (usado apos restauracao de backup)."""

import os
import sys


def restart_app() -> None:
    """
    Substitui o processo atual por uma nova instancia do app.
    - frozen (exe): reabre o executavel
    - dev: python -m src.main
    """
    python = sys.executable
    if getattr(sys, "frozen", False):
        os.execv(python, [python])
    else:
        os.execv(python, [python, "-m", "src.main"])
