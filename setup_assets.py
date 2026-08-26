#!/usr/bin/env python3
"""Script para preparar assets: fontes e ícone."""
import sys
import os
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.paths import get_assets_dir, get_fonts_dir


def create_ico_from_logo():
    """Cria icone moderno azul arredondado com simbolo de certificado."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        assets_dir = get_assets_dir()
        ico_path = assets_dir / "logo.ico"

        sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icons = []

        for size in sizes:
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Fundo azul arredondado
            pad = max(1, size[0] // 16)
            radius = max(2, size[0] // 5)
            draw.rounded_rectangle(
                [pad, pad, size[0] - pad, size[1] - pad],
                radius=radius,
                fill=(27, 58, 92, 255)
            )

            # Simbolo de certificado (documento branco com linhas)
            cx, cy = size[0] // 2, size[1] // 2
            doc_w = int(size[0] * 0.50)
            doc_h = int(size[1] * 0.60)
            doc_x1 = cx - doc_w // 2
            doc_y1 = cy - doc_h // 2
            doc_x2 = cx + doc_w // 2
            doc_y2 = cy + doc_h // 2
            doc_r = max(1, size[0] // 20)

            # Documento branco
            draw.rounded_rectangle(
                [doc_x1, doc_y1, doc_x2, doc_y2],
                radius=doc_r,
                fill=(255, 255, 255, 240)
            )

            # Linhas de texto no documento
            line_color = (27, 58, 92, 180)
            if size[0] >= 32:
                margin = max(2, size[0] // 12)
                line_h = max(1, size[0] // 40)
                line_gap = max(2, size[0] // 16)
                start_y = doc_y1 + int(doc_h * 0.30)
                for i in range(3):
                    ly = start_y + i * line_gap
                    if ly + line_h < doc_y2 - margin:
                        lw = doc_w - 2 * margin if i < 2 else int(doc_w * 0.6)
                        draw.rectangle(
                            [doc_x1 + margin, ly, doc_x1 + margin + lw, ly + line_h],
                            fill=line_color
                        )

            # Selo de aprovacao (circulo dourado)
            if size[0] >= 48:
                seal_r = max(2, size[0] // 8)
                seal_cx = doc_x2 - int(doc_w * 0.25)
                seal_cy = doc_y2 - int(doc_h * 0.25)
                draw.ellipse(
                    [seal_cx - seal_r, seal_cy - seal_r,
                     seal_cx + seal_r, seal_cy + seal_r],
                    fill=(218, 165, 32, 220)
                )
                if size[0] >= 64:
                    inner_r = max(1, seal_r - max(1, size[0] // 32))
                    draw.ellipse(
                        [seal_cx - inner_r, seal_cy - inner_r,
                         seal_cx + inner_r, seal_cy + inner_r],
                        fill=(255, 215, 0, 200)
                    )

            icons.append(img)

        icons[0].save(
            ico_path,
            format='ICO',
            sizes=[(icon.width, icon.height) for icon in icons],
            append_images=icons[1:]
        )
        print(f"Icone criado: {ico_path}")
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