import json
import customtkinter as ctk
from src.utils.paths import get_data_dir


# --- Font Scale ---
_FONT_SCALE = 1.0
_FONT_SCALE_FILE = get_data_dir() / "font_scale.json"


def load_font_scale():
    """Carrega escala de fonte salva."""
    global _FONT_SCALE
    try:
        if _FONT_SCALE_FILE.exists():
            data = json.loads(_FONT_SCALE_FILE.read_text(encoding="utf-8"))
            _FONT_SCALE = float(data.get("scale", 1.0))
            _FONT_SCALE = max(0.7, min(1.6, _FONT_SCALE))
    except Exception:
        _FONT_SCALE = 1.0


def save_font_scale(scale: float):
    """Salva escala de fonte."""
    global _FONT_SCALE
    _FONT_SCALE = max(0.7, min(1.6, scale))
    try:
        _FONT_SCALE_FILE.write_text(
            json.dumps({"scale": _FONT_SCALE}), encoding="utf-8"
        )
    except Exception:
        pass


def get_font_scale() -> float:
    return _FONT_SCALE


def _s(size: int) -> int:
    """Aplica escala a um tamanho de fonte."""
    return max(6, int(size * _FONT_SCALE))


# Tema de cores azul corporativo
COLORS = {
    "primary": "#1B3A5C",
    "primary_hover": "#152D4A",
    "secondary": "#2C5F8A",
    "accent": "#3A7BC8",
    "background": "#F0F4F8",
    "surface": "#FFFFFF",
    "text": "#1A1A2E",
    "text_secondary": "#4A4A6A",
    "muted": "#999999",
    "border": "#D0D8E8",
    "success": "#2E7D32",
    "error": "#C62828",
    "warning": "#EF6C00",
}


def setup_theme():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    ctk.ThemeManager.theme["CTkFrame"]["fg_color"] = COLORS["surface"]
    ctk.ThemeManager.theme["CTkButton"]["fg_color"] = COLORS["primary"]
    ctk.ThemeManager.theme["CTkButton"]["hover_color"] = COLORS["primary_hover"]
    ctk.ThemeManager.theme["CTkButton"]["text_color"] = COLORS["surface"]
    ctk.ThemeManager.theme["CTkEntry"]["fg_color"] = COLORS["surface"]
    ctk.ThemeManager.theme["CTkEntry"]["border_color"] = COLORS["border"]
    ctk.ThemeManager.theme["CTkEntry"]["text_color"] = COLORS["text"]
    ctk.ThemeManager.theme["CTkLabel"]["text_color"] = COLORS["text"]
    ctk.ThemeManager.theme["CTkComboBox"]["fg_color"] = COLORS["surface"]
    ctk.ThemeManager.theme["CTkComboBox"]["border_color"] = COLORS["border"]
    ctk.ThemeManager.theme["CTkComboBox"]["button_color"] = COLORS["primary"]
    ctk.ThemeManager.theme["CTkComboBox"]["button_hover_color"] = COLORS["primary_hover"]
    ctk.ThemeManager.theme["CTkScrollableFrame"]["fg_color"] = COLORS["surface"]
    ctk.ThemeManager.theme["CTkScrollbar"]["button_color"] = COLORS["primary"]


def get_fonts() -> dict:
    """Retorna dict de fontes com escala aplicada."""
    return {
        "title": ("Segoe UI", _s(28), "bold"),
        "subtitle": ("Segoe UI", _s(16), "bold"),
        "heading": ("Segoe UI", _s(14), "bold"),
        "body": ("Segoe UI", _s(12), "normal"),
        "body_bold": ("Segoe UI", _s(12), "bold"),
        "small": ("Segoe UI", _s(10), "normal"),
        "small_bold": ("Segoe UI", _s(10), "bold"),
        "tiny": ("Segoe UI", _s(8), "normal"),
        "mono": ("Consolas", _s(10), "normal"),
        "sidebar_title": ("Segoe UI", _s(16), "bold"),
        "sidebar_sub": ("Segoe UI", _s(16), "bold"),
        "sidebar_nav": ("Segoe UI", _s(11), "normal"),
        "sidebar_version": ("Segoe UI", _s(8), "normal"),
    }


# Compat: FONTS como property que sempre retorna valores atualizados
class _FontsProxy:
    """Dict-like proxy que sempre aplica a escala atual."""
    def __getitem__(self, key):
        return get_fonts()[key]
    def get(self, key, default=None):
        return get_fonts().get(key, default)

FONTS = _FontsProxy()
