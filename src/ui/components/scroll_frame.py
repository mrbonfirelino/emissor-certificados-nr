import customtkinter as ctk

from src.ui.styles import COLORS


def _style_scrollbar(sb):
    """Trilho + thumb nas cores corporativas (visible em ambos os temas)."""
    try:
        sb.configure(
            fg_color=COLORS["border"],
            button_color=COLORS["secondary"],
            button_hover_color=COLORS["primary"],
        )
    except Exception:
        # internos do CTk mudaram entre versoes: mantem padrao
        pass


class ScrollListFrame(ctk.CTkFrame):
    """Lista com scroll VERTICAL + HORIZONTAL.

    Conteudo (cabecalho/linhas) deve ser criado dentro de ``self.body``
    (use ``clear()`` para limpar). A barra horizontal existe sempre —
    mesmo que fique cinza/sem uso — evitando conteudo cortado em janelas
    estreitas (itens de tabelas com muitos botoes/colunas).
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.vscroll = ctk.CTkScrollableFrame(self, **kwargs)
        self.vscroll.grid(row=0, column=0, sticky="nsew")
        _style_scrollbar(self.vscroll._scrollbar)

        self.body = ctk.CTkScrollableFrame(
            self.vscroll, orientation="horizontal", fg_color="transparent"
        )
        self.body.grid(row=0, column=0, sticky="nsew")
        _style_scrollbar(self.body._scrollbar)

    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()
