#!/usr/bin/env python3
"""Script para preparar assets: fontes e ícone."""
import sys
import os
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.paths import get_assets_dir, get_fonts_dir


def create_ico_from_logo():
    """Cria o icone multi-resolucao a partir do 'ICONE RECORTADO.jpg' da raiz
    (quadrado com pad, fundo opaco). Substitui o gerador de icone desenhado."""
    try:
        from PIL import Image

        assets_dir = get_assets_dir()
        ico_path = assets_dir / "logo.ico"

        src = Path(__file__).parent / "ICONE RECORTADO.jpg"
        if not src.exists():
            print(f"AVISO: {src.name} nao encontrado na raiz — icone nao alterado")
            return False

        img = Image.open(src).convert("RGB")
        lado = max(img.size)
        quad = Image.new("RGB", (lado, lado), (255, 255, 255))
        quad.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2))
        quad = quad.convert("RGBA")

        quad.save(
            ico_path,
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        print(f"Icone criado a partir de {src.name}: {ico_path}")
        return True

    except Exception as e:
        print(f"Erro ao criar icone: {e}")
        return False


def copy_system_fonts():
    """Tenta copiar fontes DejaVu do sistema ou baixa se necessário."""
    fonts_dir = get_fonts_dir()
    fonts_dir.mkdir(parents=True, exist_ok=True)
    
    required_fonts = [
        'DejaVuSans.ttf',
        'DejaVuSans-Bold.ttf',
        'DejaVuSans-Oblique.ttf',
        'DejaVuSans-BoldOblique.ttf'
    ]
    
    # Verifica se já existem
    all_exist = all((fonts_dir / f).exists() for f in required_fonts)
    if all_exist:
        print("Fontes DejaVu já presentes")
        return True
    
    # Tenta copiar do sistema (Linux/WSL)
    system_font_dirs = [
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/local/share/fonts/dejavu"),
        Path("C:/Windows/Fonts"),  # Windows (pode não ter)
    ]
    
    for sys_dir in system_font_dirs:
        if sys_dir.exists():
            for font_name in required_fonts:
                src = sys_dir / font_name
                dst = fonts_dir / font_name
                if src.exists() and not dst.exists():
                    try:
                        import shutil
                        shutil.copy2(src, dst)
                        print(f"Copiado: {font_name}")
                    except Exception as e:
                        print(f"Erro copiando {font_name}: {e}")
    
    # Verifica novamente
    all_exist = all((fonts_dir / f).exists() for f in required_fonts)
    if all_exist:
        return True
    
    print("AVISO: Fontes DejaVu não encontradas. O reportlab usará fontes padrão.")
    print("Para melhor qualidade, instale: sudo apt install fonts-dejavu-core (Linux)")
    print("Ou baixe de: https://github.com/dejavu-fonts/dejavu-fonts/releases")
    return False


def main():
    print("=== Preparando Assets ===")
    create_ico_from_logo()
    copy_system_fonts()
    print("=== Concluído ===")


if __name__ == "__main__":
    main()