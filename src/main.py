#!/usr/bin/env python3
"""
Certificados NR - Gerador de Certificados de Treinamento
========================================================
Aplicação desktop para emissão de certificados NR com templates configuráveis.

Uso:
    python -m src.main          # Modo desenvolvimento
    ./CertificadosNR.exe        # Executável compilado
"""

from src.ui.app import main

if __name__ == "__main__":
    main()