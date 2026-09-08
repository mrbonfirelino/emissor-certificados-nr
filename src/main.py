#!/usr/bin/env python3
"""
NormaTech - Gerador de Certificados de Treinamento
===================================================
Aplicação desktop para emissão de certificados NR com templates configuráveis.

Uso:
    python -m src.main          # Modo desenvolvimento
    ./NormaTech.exe             # Executável compilado
    <exe|python src/main.py> --backup   # Backup headless (tarefa agendada)
"""

import sys


def _run_backup_headless() -> int:
    """Backup automatico sem UI (chamado pela tarefa agendada do Windows)."""
    from src.core.backup_manager import BackupManager

    try:
        manager = BackupManager(start_jobs=False)
        result = manager.create_backup(auto=True)
        return 0 if result else 1
    except Exception:
        return 1


if __name__ == "__main__":
    if "--backup" in sys.argv:
        if __package__ in (None, ""):
            # rodando como script (python src\main.py): garante raiz no sys.path
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.exit(_run_backup_headless())

    from src.ui.app import main
    main()
