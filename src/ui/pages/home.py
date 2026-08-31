import customtkinter as ctk
from typing import Callable
from src.ui.styles import COLORS, get_fonts


class WelcomePage(ctk.CTkFrame):
    def __init__(
        self,
        master,
        employee_repo,
        history_repo,
        on_navigate: Callable[[str], None] = None,
        **kwargs
    ):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.employee_repo = employee_repo
        self.history_repo = history_repo
        self.on_navigate = on_navigate

        self._logo_image = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        fonts = get_fonts()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === AREA CENTRAL ===
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0, sticky="nsew")
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(0, weight=1)
        center.grid_rowconfigure(6, weight=1)

        card = ctk.CTkFrame(center, fg_color=COLORS["surface"], corner_radius=16, border_width=1, border_color=COLORS["border"])
        card.grid(row=1, column=0, sticky="nsew", padx=40, pady=24)
        card.grid_columnconfigure(0, weight=1)
        for r in range(7):
            card.grid_rowconfigure(r, weight=0)
        card.grid_rowconfigure(0, weight=1)
        card.grid_rowconfigure(6, weight=1)

        # Logo
        logo_label = self._build_logo(card)
        if logo_label:
            logo_label.grid(row=1, column=0, pady=(12, 4))
        else:
            ctk.CTkLabel(
                card, text="\U0001F4DC",
                font=("Segoe UI", 48), text_color=COLORS["primary"]
            ).grid(row=1, column=0, pady=(12, 4))

        # Titulo + subtitulo
        ctk.CTkLabel(
            card, text="Bem-vindo ao Certificados NR",
            font=fonts["title"], text_color=COLORS["primary"]
        ).grid(row=2, column=0, pady=(4, 2))

        ctk.CTkLabel(
            card, text="Sistema de emissao de certificados de treinamento - ALTEC",
            font=fonts["body"], text_color=COLORS["text_secondary"]
        ).grid(row=3, column=0, pady=(0, 8))

        # === CARDS DE RESUMO ===
        stats_frame = ctk.CTkFrame(card, fg_color="transparent")
        stats_frame.grid(row=4, column=0, sticky="ew", padx=24, pady=(4, 12))
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.lbl_cert_count = self._build_stat_card(stats_frame, 0, "\U0001F4C4", "0", "Certificados Emitidos")
        self.lbl_emp_count = self._build_stat_card(stats_frame, 1, "\U0001F465", "0", "Funcionarios Cadastrados")
        self.lbl_nr_count = self._build_stat_card(stats_frame, 2, "\U0001F4DA", "0", "NRs Disponiveis")

        # === ATALHOS ===
        shortcuts_frame = ctk.CTkFrame(card, fg_color="transparent")
        shortcuts_frame.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 16))

        def nav(key: str):
            if self.on_navigate:
                self.on_navigate(key)

        state = "normal" if self.on_navigate else "disabled"

        ctk.CTkButton(
            shortcuts_frame, text="\U0001F393  Emitir Certificado",
            font=fonts["body_bold"], height=40,
            fg_color=COLORS["success"], hover_color="#256B28",
            state=state, command=lambda: nav("certificates")
        ).pack(side="left", expand=True, fill="x", padx=6)

        ctk.CTkButton(
            shortcuts_frame, text="\U0001F465  Funcionarios",
            font=fonts["body_bold"], height=40,
            fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
            state=state, command=lambda: nav("employees")
        ).pack(side="left", expand=True, fill="x", padx=6)

        ctk.CTkButton(
            shortcuts_frame, text="\U0001F4CB  Historico",
            font=fonts["body_bold"], height=40,
            fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
            state=state, command=lambda: nav("history")
        ).pack(side="left", expand=True, fill="x", padx=6)

    def _build_logo(self, parent):
        try:
            from PIL import Image
            from src.utils.paths import get_logo_path
            logo_path = get_logo_path()
            if not logo_path.exists():
                return None
            img = Image.open(str(logo_path))
            max_h = 110
            if img.height > max_h:
                ratio = max_h / img.height
                size = (max(1, int(img.width * ratio)), max_h)
            else:
                size = (img.width, img.height)
            self._logo_image = ctk.CTkImage(light_image=img, size=size)
            return ctk.CTkLabel(parent, image=self._logo_image, text="")
        except Exception:
            return None

    def _build_stat_card(self, parent, col: int, icon: str, value: str, label: str):
        fonts = get_fonts()
        card = ctk.CTkFrame(
            parent, fg_color=COLORS["background"], corner_radius=12,
            border_width=1, border_color=COLORS["border"]
        )
        card.grid(row=0, column=col, sticky="nsew", padx=6)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(pady=(12, 2))
        ctk.CTkLabel(header, text=icon, font=("Segoe UI", 16)).pack(side="left", padx=(0, 6))

        lbl_value = ctk.CTkLabel(
            header, text=value,
            font=fonts["title"], text_color=COLORS["primary"]
        )
        lbl_value.pack(side="left")

        ctk.CTkLabel(
            card, text=label,
            font=fonts["small"], text_color=COLORS["text_secondary"]
        ).pack(pady=(0, 12))

        return lbl_value

    def refresh(self):
        certs = 0
        emps = 0
        nrs = 0

        try:
            certs = self.history_repo.count_all()
        except Exception:
            pass

        try:
            emps = self.employee_repo.count_all()
        except Exception:
            pass

        try:
            from src.core.template_loader import list_available_nrs
            nrs = len(list_available_nrs())
        except Exception:
            pass

        self.lbl_cert_count.configure(text=str(certs))
        self.lbl_emp_count.configure(text=str(emps))
        self.lbl_nr_count.configure(text=str(nrs))
