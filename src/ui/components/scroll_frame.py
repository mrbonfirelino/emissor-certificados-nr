import customtkinter as ctk

from src.ui.styles import COLORS


class ScrollListFrame(ctk.CTkScrollableFrame):
    """CTkScrollableFrame com scrollbar destacada (trilho + thumb azul).

    A scrollbar do CTk sempre existe, mas no tema padrao e um cinca flat
    que se confunde com a superficie da lista. Aqui ela recebe trilho e
    thumb nas cores corporativas para ficar visivel em ambos os temas.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._style_scrollbar()

    def _style_scrollbar(self):
        try:
            self._scrollbar.configure(
                fg_color=COLORS["border"],
                button_color=COLORS["secondary"],
                button_hover_color=COLORS["primary"],
            )
        except Exception:
            # internos do CTk mudaram entre versoes: mantem padrao
            pass
