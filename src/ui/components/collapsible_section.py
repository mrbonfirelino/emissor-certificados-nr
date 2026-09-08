"""Secao recolhivel (dropdown/hide) para a tela de Configuracoes (v1.16.0)."""
import customtkinter as ctk
from src.ui.styles import COLORS, get_fonts


class CollapsibleSection(ctk.CTkFrame):
    """Frame com header clicavel (seta + titulo) e conteudo que abre/fecha.

    O conteudo e criado pelo chamador dentro de `self.content` (grid col 0).
    """

    def __init__(self, master, titulo: str, aberta: bool = False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._aberta = bool(aberta)
        self._titulo = titulo

        fonts = get_fonts()
        self._header = ctk.CTkButton(
            self, text=self._texto(), anchor="w",
            font=fonts["body_bold"], height=36, corner_radius=6,
            fg_color=COLORS["surface"], hover_color=COLORS["border"],
            text_color=COLORS["primary"], command=self.toggle
        )
        self._header.grid(row=0, column=0, sticky="ew")

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid_columnconfigure(0, weight=1)
        if self._aberta:
            self._mostrar()

    def _texto(self) -> str:
        seta = "\u25be" if self._aberta else "\u25b8"  # ▾ / ▸
        return f"  {seta}  {self._titulo}"

    def _mostrar(self):
        self.content.grid(row=1, column=0, sticky="ew", padx=(14, 0), pady=(6, 10))

    def toggle(self):
        if self._aberta:
            self.content.grid_remove()
            self._aberta = False
        else:
            self._mostrar()
            self._aberta = True
        self._header.configure(text=self._texto())

    @property
    def aberta(self) -> bool:
        return self._aberta
