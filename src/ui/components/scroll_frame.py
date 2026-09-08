import tkinter as tk

import customtkinter as ctk

from src.ui.styles import COLORS


def _style_scrollbar(sb):
    """Trilho + thumb nas cores corporativas (visível em ambos os temas)."""
    try:
        sb.configure(
            fg_color=COLORS["border"],
            button_color=COLORS["secondary"],
            button_hover_color=COLORS["primary"],
        )
    except Exception:
        # internos do CTk mudaram entre versoes: mantem padrao
        pass


class ScrollListFrame(ctk.CTkScrollableFrame):
    """Lista com scroll VERTICAL + HORIZONTAL no MESMO canvas.

    Nao se pode aninhar um CTkScrollableFrame horizontal dentro de outro
    vertical: o CTk fora a largura do conteudo = largura do canvas e nao
    tem pesos de grid internos, colapsando o widget aninhado (bug v1.19).
    Aqui a barra horizontal e adicionada manualmente ao canvas interno.

    O conteudo (cabecalho/linhas) deve ser criado dentro de ``self.body``
    (que aponta para o proprio widget) e a lista limpa com ``clear()``.
    A barra horizontal existe sempre — mesmo que fique cinza/sem uso.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.body = self

        # Barra horizontal manual no mesmo canvas (row 2 do grid interno;
        # canvas fica no row 1 com weight, yscrollbar na coluna 1)
        self._xsb = ctk.CTkScrollbar(
            self._parent_frame,
            orientation="horizontal",
            command=self._parent_canvas.xview,
        )
        self._parent_canvas.configure(xscrollcommand=self._xsb.set)
        self._xsb.grid(row=2, column=0, sticky="ew")
        _style_scrollbar(self._scrollbar)
        _style_scrollbar(self._xsb)

        # O handler padrao do CTk forc a largura da janela interna = canvas
        # (mata o x-scroll). Substitui por versao que preserva o conteudo:
        self._parent_canvas.unbind("<Configure>")
        self._parent_canvas.bind("<Configure>", self._fit_window_width)
        self.bind(
            "<Configure>",
            lambda e: self.after_idle(self._fit_window_width),
            add="+",
        )

    def _fit_window_width(self, event=None):
        """Largura da janela interna = max(canvas, conteudo natural)."""
        try:
            w = max(self._parent_canvas.winfo_width(), self.winfo_reqwidth())
            self._parent_canvas.itemconfigure(self._create_window_id, width=w)
            self._parent_canvas.configure(scrollregion=self._parent_canvas.bbox("all"))
        except Exception:
            pass

    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()
        self.after_idle(self._fit_window_width)
