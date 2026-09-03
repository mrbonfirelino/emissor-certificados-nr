"""
Painel de indicadores da tela inicial (vencimentos, assinados, emissoes).

Sem dependencias de graficos: usa chips + CTkProgressBar (leve para CPU fraca).
"""
import customtkinter as ctk
from src.ui.styles import COLORS, get_fonts

_MESES = {"01": "jan", "02": "fev", "03": "mar", "04": "abr", "05": "mai", "06": "jun",
          "07": "jul", "08": "ago", "09": "set", "10": "out", "11": "nov", "12": "dez"}


class DashboardPanel(ctk.CTkFrame):

    def __init__(self, master, history_repo, **kwargs):
        super().__init__(master, fg_color=COLORS["surface"], corner_radius=12, **kwargs)
        self.history_repo = history_repo

        self.grid_columnconfigure((0, 1), weight=1)
        self._build_ui()

    # ── construcao ─────────────────────────────────────────────

    def _build_ui(self):
        fonts = get_fonts()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 2))
        ctk.CTkLabel(header, text="Indicadores", font=fonts["heading"],
                     text_color=COLORS["primary"]).pack(side="left")
        ctk.CTkButton(header, text="Atualizar", width=84, height=26,
                      font=fonts["small"], fg_color=COLORS["secondary"],
                      hover_color=COLORS["primary"],
                      command=self.refresh).pack(side="right")

        chips = ctk.CTkFrame(self, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 6))
        chips.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.lbl_vencidos = self._chip(chips, 0, "Vencidos", COLORS["error"])
        self.lbl_vencer7 = self._chip(chips, 1, "Vencem em 7d", COLORS["warning"])
        self.lbl_vencer30 = self._chip(chips, 2, "Vencem em 30d", COLORS["accent"])
        self.lbl_assinados = self._chip(chips, 3, "Assinados", COLORS["success"])

        self.nr_body = self._section("Emissões por NR (top 5)", 2, 0)
        self.mes_body = self._section("Emissões por mês (últimos 6)", 2, 1)

    def _section(self, title: str, row: int, col: int) -> ctk.CTkFrame:
        fonts = get_fonts()
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=row, column=col, sticky="nsew", padx=16, pady=(2, 12))
        ctk.CTkLabel(frame, text=title, font=fonts["small_bold"],
                     text_color=COLORS["text_secondary"], anchor="w"
                     ).pack(fill="x")
        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(fill="both", expand=True)
        return body

    def _chip(self, parent, col: int, label: str, color: str):
        fonts = get_fonts()
        card = ctk.CTkFrame(parent, fg_color=COLORS["background"], corner_radius=8)
        card.grid(row=0, column=col, sticky="ew", padx=4)
        lbl_value = ctk.CTkLabel(card, text="—", font=fonts["subtitle"],
                                 text_color=color)
        lbl_value.pack(pady=(6, 0))
        ctk.CTkLabel(card, text=label, font=fonts["tiny"],
                     text_color=COLORS["text_secondary"]).pack(pady=(0, 6))
        return lbl_value

    # ── atualizacao ────────────────────────────────────────────

    def refresh(self):
        try:
            stats = self.history_repo.get_dashboard_stats()
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("dashboard-refresh", e)
            stats = {"total": 0, "assinados": 0, "por_nr": [], "por_mes": [],
                     "vencidos": 0, "vencer_7": 0, "vencer_30": 0}

        self.lbl_vencidos.configure(text=str(stats["vencidos"]))
        self.lbl_vencer7.configure(text=str(stats["vencer_7"]))
        self.lbl_vencer30.configure(text=str(stats["vencer_30"]))
        total = stats["total"]
        pct = f"{stats['assinados'] * 100 // total}%" if total else "0%"
        self.lbl_assinados.configure(text=f"{stats['assinados']} ({pct})")

        self._render_bars(self.nr_body, stats["por_nr"], COLORS["primary"])
        meses = [(self._fmt_mes(m), n) for m, n in reversed(stats["por_mes"])]
        self._render_bars(self.mes_body, meses, COLORS["accent"])

    @staticmethod
    def _fmt_mes(mes_iso: str) -> str:
        try:
            ano, mes = mes_iso.split("-")
            return f"{_MESES.get(mes, mes)}/{ano[2:]}"
        except Exception:
            return mes_iso

    def _render_bars(self, parent, items, color):
        fonts = get_fonts()
        for widget in parent.winfo_children():
            widget.destroy()
        if not items:
            ctk.CTkLabel(parent, text="Sem dados", font=fonts["small"],
                         text_color=COLORS["muted"]).pack(anchor="w", pady=8)
            return
        max_n = max(n for _, n in items) or 1
        for label, n in items:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=1)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=label, font=fonts["small"],
                         text_color=COLORS["text"], width=9, anchor="w"
                         ).grid(row=0, column=0, padx=(0, 6))
            bar = ctk.CTkProgressBar(row, height=8, fg_color=COLORS["border"],
                                     progress_color=color)
            bar.grid(row=0, column=1, sticky="ew", padx=(0, 6))
            bar.set(n / max_n)
            ctk.CTkLabel(row, text=str(n), font=fonts["small"],
                         text_color=COLORS["text_secondary"], width=4, anchor="e"
                         ).grid(row=0, column=2)
