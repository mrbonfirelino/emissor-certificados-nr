from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageOps = None

MAX_SIZE_MB = 2
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
TARGET_3X4 = (300, 400)  # 3:4 portrait, good quality for print and preview
THUMB_3X4 = (90, 120)    # thumbnail for lists
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_MIME = {"image/jpeg", "image/png", "image/bmp", "image/webp"}


def is_pil_available() -> bool:
    return PIL_AVAILABLE


def validate_image_file(path: str) -> Tuple[bool, str]:
    p = Path(path)
    if not p.exists():
        return False, "Arquivo nao encontrado"
    if p.suffix.lower() not in ALLOWED_EXT:
        return False, f"Formato nao suportado ({p.suffix}). Use JPG ou PNG"
    size = p.stat().st_size
    if size > MAX_SIZE_BYTES:
        return False, f"Arquivo muito grande ({size/1024/1024:.1f} MB). Max {MAX_SIZE_MB} MB"
    if not PIL_AVAILABLE:
        return False, "Pillow nao instalado (pip install pillow)"
    return True, ""


def process_photo_3x4(file_path: str, target_size: Tuple[int, int] = TARGET_3X4) -> Optional[bytes]:
    """
    Abre imagem, converte para 3x4 com crop central e retorna bytes PNG.
    Sempre retorna PNG para preservar qualidade.
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow nao disponivel")
    ok, msg = validate_image_file(file_path)
    if not ok:
        raise ValueError(msg)
    img = Image.open(file_path)
    # corrige orientacao EXIF
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    # fit 3x4 com crop central
    fitted = ImageOps.fit(img, target_size, method=Image.LANCZOS, bleed=0.0, centering=(0.5, 0.5))
    buf = BytesIO()
    # PNG sem perda, mas tambem pode ser JPEG; PNG ok para BLOB
    fitted.save(buf, format="PNG")
    data = buf.getvalue()
    if len(data) > MAX_SIZE_BYTES:
        # tenta JPEG comprimido se PNG ficou grande
        buf2 = BytesIO()
        fitted.save(buf2, format="JPEG", quality=85, optimize=True)
        data = buf2.getvalue()
    return data


def bytes_to_pil_image(data: bytes):
    if not data or not PIL_AVAILABLE:
        return None
    try:
        buf = BytesIO(data)
        img = Image.open(buf)
        return img
    except Exception:
        return None


def make_thumbnail_bytes(data: bytes, size: Tuple[int, int] = THUMB_3X4) -> Optional[bytes]:
    img = bytes_to_pil_image(data)
    if img is None:
        return None
    try:
        thumb = ImageOps.fit(img, size, method=Image.LANCZOS)
        buf = BytesIO()
        thumb.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def get_image_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    img = bytes_to_pil_image(data)
    if img is None:
        return None
    return img.size
