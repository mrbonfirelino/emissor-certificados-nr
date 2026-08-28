"""
Teste standalone do layout das paginas.
Simula o layout de uma pagina (header, cards, filtros, lista, paginacao)
usando grid_propagate(False) para validar o fix.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk

COLORS = {
    "background": "#F0F2F5",
    "surface": "#FFFFFF",
    "primary": "#1976D2",
    "secondary": "#1565C0",
    "accent": "#43A047",
    "text": "#212121",
    "text_secondary": "#757575",
    "muted": "#9E9E9E",
    "border": "#E0E0E0",
    "error": "#D32F2F",
    "warning": "#F57C00",
    "success": "#388E3C",
}


class TestPage(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_propagate(False)

        # Row 0 — Header
        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        self._header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self._header, text="Vencimentos",
                      font=("Segoe UI", 18, "bold"), text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(self._header, text="27/08/2026",
                      font=("Segoe UI", 11), text_color=COLORS["muted"]).grid(row=0, column=1, sticky="e")

        # Row 1 — Dashboard cards
        self._cards = ctk.CTkFrame(self, fg_color="transparent")
        self._cards.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        for i in range(6):
            self._cards.grid_columnconfigure(i, weight=1)
        for i, (label, color) in enumerate([
            ("118", COLORS["primary"]), ("5", COLORS["error"]),
            ("2", COLORS["error"]), ("3", "#E65100"),
            ("4", COLORS["warning"]), ("104", COLORS["success"]),
        ]):
            card = ctk.CTkFrame(self._cards, fg_color=COLORS["surface"],
                                corner_radius=10, border_width=1, border_color=COLORS["border"])
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(card, text=label, font=("Segoe UI", 22, "bold"), text_color=color).pack(pady=(8, 0))
            ctk.CTkLabel(card, text="Label", font=("Segoe UI", 11), text_color=COLORS["muted"]).pack(pady=(0, 8))

        # Row 2 — Filters
        self._filters = ctk.CTkFrame(self, fg_color="transparent")
        self._filters.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        self._filters.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(self._filters, placeholder_text="Buscar...",
                     font=("Segoe UI", 12), height=36, corner_radius=8,
                     border_color=COLORS["border"]).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(self._filters, text="Todos", width=60, height=28,
                      fg_color=COLORS["primary"], text_color="white").grid(row=0, column=1)

        # Row 3 — Lista (weight=1 preenche resto)
        self._list = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"],
                                            corner_radius=10, border_width=1,
                                            border_color=COLORS["border"], height=200)
        self._list.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 5))
        self._list.grid_columnconfigure(0, weight=1)

        # Adicionar itens de teste
        for i in range(15):
            row = ctk.CTkFrame(self._list, fg_color=COLORS["surface"],
                               corner_radius=8, border_width=1, border_color=COLORS["border"])
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkFrame(row, fg_color=COLORS["success"], width=4, height=36, corner_radius=2
                         ).grid(row=0, column=0, rowspan=2, padx=(8, 5), pady=8, sticky="ns")
            ctk.CTkLabel(row, text=f"Funcionario {i+1:03d}",
                         font=("Segoe UI", 13, "bold"), text_color=COLORS["text"], anchor="w"
                         ).grid(row=0, column=1, sticky="sw", padx=5, pady=(8, 0))
            ctk.CTkLabel(row, text="000.000.000-00 | Tecnico",
                         font=("Segoe UI", 11), text_color=COLORS["muted"], anchor="w"
                         ).grid(row=1, column=1, sticky="nw", padx=5, pady=(0, 5))
            ctk.CTkLabel(row, text="3 certificado(s)",
                         font=("Segoe UI", 11), text_color=COLORS["secondary"]
                         ).grid(row=0, column=2, rowspan=2, padx=10, pady=8, sticky="e")

        # Row 4 — Paginacao
        self._pag = ctk.CTkFrame(self, fg_color="transparent")
        self._pag.grid(row=4, column=0, sticky="w", padx=20, pady=(0, 5))
        ctk.CTkLabel(self._pag, text="Pagina 1/3 | 15 funcionarios",
                      font=("Segoe UI", 11), text_color=COLORS["muted"]).pack(side="left")

        # Ajustar altura da lista apos render
        self.after(200, self._fit_scroll_height)

    def _fit_scroll_height(self):
        self.update_idletasks()
        h = self.winfo_height()
        print(f"  [DEBUG] Page height: {h}")
        if h < 200:
            print("  [DEBUG] Height < 200, skipping fit")
            return
        header_h = self._header.winfo_reqheight()
        cards_h = self._cards.winfo_reqheight()
        filters_h = self._filters.winfo_reqheight()
        pag_h = self._pag.winfo_reqheight()
        margins = 30
        available = h - header_h - cards_h - filters_h - pag_h - margins
        print(f"  [DEBUG] header={header_h}, cards={cards_h}, filters={filters_h}, pag={pag_h}, margins={margins}")
        print(f"  [DEBUG] Available for list: {available}")
        self._list.configure(height=max(available, 150))
        self._list.update_idletasks()
        print(f"  [DEBUG] List height after configure: {self._list.winfo_height()}")

        # Debug: print all widget sizes
        print("\n  [DEBUG] Widget tree sizes:")
        for child in self.winfo_children():
            print(f"    {child.winfo_class()}: req={child.winfo_reqheight()}, actual={child.winfo_height()}, managed_by={child.winfo_manager()}")
            for grandchild in child.winfo_children():
                print(f"      {grandchild.winfo_class()}: req={grandchild.winfo_reqheight()}, actual={grandchild.winfo_height()}, managed_by={grandchild.winfo_manager()}")


def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Teste Layout - grid_propagate(False)")
    root.geometry("1280x720")
    root.minsize(1024, 600)

    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    page = TestPage(root)
    page.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    print("\n=== Teste Layout ===")
    print("Janela 1280x720, pagina griddada com sticky='nsew'")
    print("grid_propagate(False) ativado")
    print("Aguardando150ms para debug...\n")

    root.after(150, lambda: print("\n=== Fim do debug ===\n"))

    root.mainloop()


if __name__ == "__main__":
    main()
