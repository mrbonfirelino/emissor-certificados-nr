import customtkinter as ctk
from typing import Callable, Optional, List
from src.core.template_loader import list_available_nrs, get_template_description, load_nr_template
from src.ui.styles import COLORS, FONTS


class NRSelector(ctk.CTkFrame):
    """Seletor de NRs em grid de cards."""
    
    def __init__(
        self,
        master,
        on_select: Callable[[str], None] = None,
        columns: int = 5,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_select = on_select
        self.columns = columns
        self.nr_codes = list_available_nrs()
        self.selected_nr: Optional[str] = None
        self.card_frames: List[ctk.CTkFrame] = []
        self._build_grid()

    def _build_grid(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.card_frames.clear()
        
        for i, nr_code in enumerate(self.nr_codes):
            row = i // self.columns
            col = i % self.columns
            
            template = load_nr_template(nr_code)
            nr_name = template.nr_name if template else nr_code
            carga = template.carga_horaria_minima if template else 0
            
            card = self._create_card(nr_code, nr_name, carga)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.card_frames.append(card)
            
            self.grid_columnconfigure(col, weight=1)

    def _create_card(self, nr_code: str, nr_name: str, carga: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            border_width=2,
            border_color=COLORS["border"],
            corner_radius=10,
            height=120
        )
        card.grid_propagate(False)
        card.nr_code = nr_code
        
        # Bind click
        def on_click(e, code=nr_code):
            self.select_nr(code)
        card.bind("<Button-1>", on_click)
        for child in card.winfo_children():
            child.bind("<Button-1>", on_click)
        
        # Conteúdo do card
        label_nr = ctk.CTkLabel(
            card,
            text=nr_code,
            font=("Segoe UI", 20, "bold"),
            text_color=COLORS["primary"]
        )
        label_nr.pack(pady=(16, 4))
        label_nr.bind("<Button-1>", on_click)
        
        label_name = ctk.CTkLabel(
            card,
            text=nr_name,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            wraplength=140,
            justify="center"
        )
        label_name.pack(pady=(0, 8), padx=12)
        label_name.bind("<Button-1>", on_click)
        
        label_carga = ctk.CTkLabel(
            card,
            text=f"{carga}h mín.",
            font=FONTS["tiny"],
            text_color=COLORS["muted"]
        )
        label_carga.pack(pady=(0, 12))
        label_carga.bind("<Button-1>", on_click)
        
        return card

    def select_nr(self, nr_code: str):
        """Seleciona NR visualmente."""
        self.selected_nr = nr_code
        for card in self.card_frames:
            if getattr(card, 'nr_code', None) == nr_code:
                card.configure(border_color=COLORS["primary"], border_width=3)
            else:
                card.configure(border_color=COLORS["border"], border_width=2)
        if self.on_select:
            self.on_select(nr_code)

    def get_selected(self) -> Optional[str]:
        return self.selected_nr

    def refresh(self):
        """Atualiza lista de NRs (após adicionar templates)."""
        self.nr_codes = list_available_nrs()
        self._build_grid()
        self.selected_nr = None