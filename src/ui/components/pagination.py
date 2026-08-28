import customtkinter as ctk
from src.ui.styles import COLORS, get_fonts


class PaginationBar(ctk.CTkFrame):
    """Barra de paginação reutilizável. Largura fixa."""

    ITEMS_PER_PAGE = 10
    FIXED_WIDTH = 520

    def __init__(self, master, on_page_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", width=self.FIXED_WIDTH, height=34, **kwargs)
        self.on_page_change = on_page_change
        self.current_page = 1
        self.total_items = 0
        self.items_per_page = self.ITEMS_PER_PAGE  # copia por instancia (outras paginas podem alterar)
        self._build_ui()

    def _build_ui(self):
        fonts = get_fonts()

        self.lbl_info = ctk.CTkLabel(
            self, text="0-0 de 0", font=fonts["small"], text_color=COLORS["muted"],
            width=100, anchor="w"
        )
        self.lbl_info.pack(side="left", padx=(0, 8))

        self.btn_first = ctk.CTkButton(
            self, text="|<", width=28, height=22, font=fonts["small"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            command=lambda: self._go_to(1)
        )
        self.btn_first.pack(side="left", padx=1)

        self.btn_prev = ctk.CTkButton(
            self, text="<", width=26, height=22, font=fonts["small"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            command=lambda: self._go_to(self.current_page - 1)
        )
        self.btn_prev.pack(side="left", padx=1)

        # Container fixo para botões de página (sempre 5 slots)
        self.pages_frame = ctk.CTkFrame(self, fg_color="transparent", width=200)
        self.pages_frame.pack(side="left", padx=4)
        self.pages_frame.pack_propagate(False)
        self._page_buttons = []

        for i in range(5):
            btn = ctk.CTkButton(
                self.pages_frame, text="", width=32, height=22,
                font=fonts["small"], fg_color=COLORS["primary"],
                hover_color=COLORS["secondary"],
                command=lambda pg=0: self._go_to(pg)
            )
            btn.pack(side="left", padx=1)
            self._page_buttons.append(btn)

        self.btn_next = ctk.CTkButton(
            self, text=">", width=26, height=22, font=fonts["small"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            command=lambda: self._go_to(self.current_page + 1)
        )
        self.btn_next.pack(side="left", padx=1)

        self.btn_last = ctk.CTkButton(
            self, text=">|", width=28, height=22, font=fonts["small"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            command=lambda: self._go_to(self.total_pages)
        )
        self.btn_last.pack(side="left", padx=1)

    @property
    def total_pages(self) -> int:
        if self.total_items <= 0:
            return 1
        return (self.total_items + self.items_per_page - 1) // self.items_per_page

    @property
    def offset(self) -> int:
        return (self.current_page - 1) * self.items_per_page

    def set_total(self, total: int):
        self.total_items = total
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        self._render()

    def reset(self):
        self.current_page = 1
        self._render()

    def _go_to(self, page: int):
        page = max(1, min(page, self.total_pages))
        if page == self.current_page:
            return
        self.current_page = page
        self._render()
        if self.on_page_change:
            self.on_page_change()

    def _render(self):
        fonts = get_fonts()
        start = (self.current_page - 1) * self.items_per_page + 1
        end = min(self.current_page * self.items_per_page, self.total_items)
        if self.total_items == 0:
            start = 0
            end = 0

        self.lbl_info.configure(text=f"{start}-{end} de {self.total_items}")

        self.btn_first.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_prev.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.current_page < self.total_pages else "disabled")
        self.btn_last.configure(state="normal" if self.current_page < self.total_pages else "disabled")

        total = self.total_pages
        current = self.current_page

        # Sempre mostrar 5 slots com paginas validas
        if total <= 5:
            pages = list(range(1, total + 1))
        else:
            pages = []
            if current <= 3:
                pages = [1, 2, 3, 4, 5]
            elif current >= total - 2:
                pages = [total - 4, total - 3, total - 2, total - 1, total]
            else:
                pages = [current - 2, current - 1, current, current + 1, current + 2]

        for i, btn in enumerate(self._page_buttons):
            if i < len(pages):
                p = pages[i]
                is_current = p == current
                btn.configure(
                    text=str(p), state="normal",
                    fg_color=COLORS["secondary"] if is_current else COLORS["primary"],
                    command=lambda pg=p: self._go_to(pg)
                )
                btn.pack(side="left", padx=1)
            else:
                btn.configure(text="", state="disabled", fg_color=COLORS["primary"])
                btn.pack(side="left", padx=1)
