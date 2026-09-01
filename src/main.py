#!/usr/bin/env python3
"""
NormaTech - Gerador de Certificados de Treinamento
===================================================
Aplicação desktop para emissão de certificados NR com templates configuráveis.

Uso:
    python -m src.main          # Modo desenvolvimento
    ./NormaTech.exe             # Executável compilado
"""

from src.ui.app import main

if __name__ == "__main__":
    main()