import customtkinter as ctk
from src.ui.styles import COLORS, FONTS


class PreviewPage(ctk.CTkFrame):
    """Página de preview (placeholder)."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        
        ctk.CTkLabel(
            self,
            text="👁 Preview do Certificado",
            font=FONTS["title"],
            text_color=COLORS["primary"]
        ).pack(expand=True)
        
        ctk.CTkLabel(
            self,
            text="Use a página inicial para visualizar certificados",
            font=FONTS["body"],
            text_color=COLORS["muted"]
        ).pack()