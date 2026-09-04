import time
import customtkinter as ctk
from datetime import date
from src.ui.styles import COLORS, get_fonts
from src.core.history_repo import HistoryRepository
from src.core.employee_repo import EmployeeRepository
from src.ui.components.pagination import PaginationBar

STATUS_COLORS = {
    "vencido": COLORS["error"],
    "urgente": COLORS["error"],
    "critico": "#E65100",
    "atencao": COLORS["warning"],
    "proximo": COLORS["success"],
    "ok": COLORS["success"],
}

# limites dos filtros por periodo (dias para vencer); vencidos (d < 0) so
# aparecem nos filtros "Todos" e "Vencidos"
PERIOD_RANGES = {
    "dias_7": (0, 7),
    "dias_15": (0, 15),
    "mes_1": (0, 30),
    "meses_3": (0, 90),
}


def filter_certs(certs: list, nr: str, search: str, period: str) -> list:
    """Filtra certificados por NR, busca textual e periodo de vencimento."""
    out = []
    for c in certs:
        if nr != "TODAS" and c["nr_code"] != nr:
            continue
        if search:
            if (search not in c["funcionario_nome"].lower()
                    and search not in c["funcionario_cpf"]
                    and search not in c["nr_code"].lower()):
                continue
        d = c["dias_para_vencer"]
        if period == "vencidos":
            if d >= 0:
                continue
        elif period in PERIOD_RANGES:
            lo, hi = PERIOD_RANGES[period]
            if not (lo <= d <= hi):
                continue
        out.append(c)
    return out


class VencimentosPage(ctk.CTkFrame):
    def __init__(self, master, history_repo: HistoryRepository,
                 on_navigate=None, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.history_repo = history_repo
        self.employee_repo = EmployeeRepository()
        self._on_navigate = on_navigate
        self.all_certs = []
        self.filtered_certs = []
        self._employees_list = []
        self._expanded = set()
        self._last_toggle = {}
        self._active_period = "all"
        self._build_ui()

    # ── Acoes rapidas dos cards ───────────────────────────────

    def _action_emit(self, emp_id: int):
        """Abre a aba Certificados com o funcionario pre-selecionado."""
        if self._on_navigate:
            self._on_navigate("certificates", {"employee_id": emp_id})

    def _action_history(self, emp_id: int, nome: str):
        """Abre a aba Historico com a busca pre-preenchida pelo nome."""
        if self._on_navigate:
            self._on_navigate("history", {"busca": nome})
        self._load_data()

    def _action_aso(self, emp_id: int):
        """Abre a aba ASO com o funcionario pre-carregado."""
        if self._on_navigate:
            self._on_navigate("aso", {"employee_id": emp_id})

    # ── Layout ───────────────────────────────────────────────

    def _build_ui(self):
        fonts = get_fonts()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        #self.grid_propagate(False)

        # Row 0 — Header
        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        self._header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self._header, text="Controle de Vencimentos",
                      font=fonts["title"], text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(self._header, text=date.today().strftime("%d/%m/%Y"),
                      font=fonts["small"], text_color=COLORS["muted"]).grid(row=0, column=1, sticky="e", padx=(10, 0))

        # Row 1 — Dashboard cards
        self._cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._cards_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        for i in range(6):
            self._cards_frame.grid_columnconfigure(i, weight=1)
        self._card_labels = {}
        for i, (key, label, color) in enumerate([
            ("total", "TOTAL de certificados ativos", COLORS["primary"]),
            ("vencidos", "Total de VENCIDOS", COLORS["error"]),
            ("dias_7", "Vencem em 7 Dias", COLORS["error"]),
            ("dias_15", "Vencem em 15 Dias", "#E65100"),
            ("mes_1", "Vencem em 1 Mes", COLORS["warning"]),
            ("meses_3", "Vencem em 3 Meses", COLORS["success"]),
        ]):
            card = ctk.CTkFrame(self._cards_frame, fg_color=COLORS["surface"],
                                corner_radius=10, border_width=1, border_color=COLORS["border"])
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(card, text="0", font=("Segoe UI", 22, "bold"),
                         text_color=color).pack(pady=(8, 0))
            ctk.CTkLabel(card, text=label, font=fonts["small"],
                         text_color=COLORS["muted"]).pack(pady=(0, 8))
            self._card_labels[key] = card.winfo_children()[-2]

        # Row 2 — Filtros
        self._filters = ctk.CTkFrame(self, fg_color="transparent")
        self._filters.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        self._filters.grid_columnconfigure(0, weight=1)

        self._search_var = ctk.StringVar()
        self._search_entry = ctk.CTkEntry(self._filters, textvariable=self._search_var,
                     placeholder_text="Buscar funcionario, CPF ou NR...",
                     font=fonts["body"], height=36, corner_radius=8,
                     border_color=COLORS["border"])
        self._search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._search_entry.bind("<Return>", lambda *_: self._on_search())

        ctk.CTkButton(self._filters, text="Buscar", width=80, height=36,
                      font=fonts["body_bold"], fg_color=COLORS["secondary"],
                      hover_color=COLORS["primary"],
                      command=self._on_search).grid(row=0, column=1, padx=(0, 15))

        ctk.CTkLabel(self._filters, text="NR:", font=fonts["small_bold"],
                     text_color=COLORS["text"]).grid(row=0, column=2, padx=(0, 3))
        self._nr_var = ctk.StringVar(value="TODAS")
        ctk.CTkOptionMenu(self._filters, variable=self._nr_var,
                          values=["TODAS", "ASO", "NR-01", "NR-06", "NR-10", "NR-12", "NR-18",
                                   "NR-26", "NR-33", "NR-34", "NR-35", "FDS", "PTA",
                                   "MOTOSERRA", "MUNCK", "PONTE-ROLANTE", "DIR-DEFENSIVA",
                                   "CIPAA", "BRIGADISTA-NR23"],
                          command=lambda *_: self._on_filter(),
                          font=fonts["small"], width=100, height=32, corner_radius=6,
                          fg_color=COLORS["primary"], button_color=COLORS["secondary"]
                          ).grid(row=0, column=3, padx=(0, 10))

        periods = ctk.CTkFrame(self._filters, fg_color="transparent")
        periods.grid(row=0, column=4, sticky="e")
        self._period_btns = {}
        for key, label in [("all", "Todos"), ("vencidos", "Vencidos"),
                           ("dias_7", "7d"), ("dias_15", "15d"),
                           ("mes_1", "30d"), ("meses_3", "90d")]:
            b = ctk.CTkButton(periods, text=label, width=50, height=28,
                              font=fonts["small"], corner_radius=4,
                              fg_color=COLORS["primary"] if key == "all" else COLORS["muted"],
                              text_color=COLORS["surface"], hover_color=COLORS["accent"],
                              command=lambda k=key: self._set_period(k))
            b.pack(side="left", padx=2)
            self._period_btns[key] = b

        # Row 3 — Lista (wrapper branco, weight1) — paginacao fora para nao sobrepor tabela
        self._list = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"],
                                            corner_radius=10, border_width=1,
                                            border_color=COLORS["border"], height=200)
        self._list.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 2))
        self._list.grid_columnconfigure(0, weight=1)

        # Row 4 — Paginacao fora do branco (sem sobreposicao, gap minimo 2px na altura)
        self._pagination = PaginationBar(self, on_page_change=self._render_list)
        self._pagination.grid(row=4, column=0, sticky="w", padx=20, pady=(2, 8))

        #self.after(200, lambda: self._fit_scroll_height(0))
        #self.after(600, lambda: self._fit_scroll_height(0))

#    def _fit_scroll_height(self, _retry=0):
#        self.update_idletasks()
#        h = self.winfo_height()
#        if h < 200:
#            try:
#                ph = self.master.winfo_height()
#                if ph >= 200:
#                    h = ph
#            except Exception:
#               pass
#        if h < 200:
#            if _retry < 5:
#                self.after(300, lambda r=_retry + 1: self._fit_scroll_height(r))
#            return
#        header_h = self._header.winfo_reqheight()
#        cards_h = self._cards_frame.winfo_reqheight()
#        filters_h = self._filters.winfo_reqheight()
#        pag_h = self._pagination.winfo_reqheight()
#        # filhos ainda nao renderizados — tenta novamente
#        if min(header_h, cards_h, filters_h, pag_h) < 5 and _retry < 5:
#            self.after(300, lambda r=_retry + 1: self._fit_scroll_height(r))
#            return
#        margins = 10
#        available = h - header_h - cards_h - filters_h - pag_h - margins
#        # altura do conteudo (bbox) — se menor que available, encolhe Canvas e cola paginacao (alternativa A)
#       self.update_idletasks()
#        try:
#            bbox = self._list._parent_canvas.bbox("all")
#            content_h = (bbox[3] - bbox[1] if bbox and bbox[3] else self._list.winfo_reqheight()) + 6
#        except Exception:
#            content_h = self._list.winfo_reqheight() + 6
#        needed = content_h + 4 if content_h else available
#        # usa o menor entre available e needed para eliminar vao branco interno mantendo scroll quando necessario
#        target = max(150, min(available, needed)) if needed and needed > 50 else max(150, available)
#        self._list.configure(height=target)

    # ── Dados ────────────────────────────────────────────────

    def _load_data(self):
        self.all_certs = self.history_repo.get_certificates_with_expiration()
        try:
            from src.core.aso_repo import AsoRepository
            self.all_certs += AsoRepository().get_asos_with_expiration()
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("vencimentos-aso", e)
        self._apply_filters()

    def _apply_filters(self):
        search = self._search_var.get().strip().lower()
        nr = self._nr_var.get()
        period = self._active_period

        self.filtered_certs = filter_certs(self.all_certs, nr, search, period)

        self._update_cards()

        groups = {}
        for c in self.filtered_certs:
            # agrupa SOMENTE por funcionario (snapshots de CPF/nome variam
            # entre emissoes e duplicavam o card)
            groups.setdefault(c["employee_id"], []).append(c)
        self._employees_list = []
        for emp_id, certs in groups.items():
            # exibicao usa o snapshot mais completo (prefere o que tem CPF)
            ref = next((c for c in certs if c["funcionario_cpf"]), certs[0])
            key = (emp_id, ref["funcionario_nome"], ref["funcionario_cpf"],
                   ref.get("funcionario_funcao", ""))
            self._employees_list.append((key, certs))
        self._pagination.set_total(len(self._employees_list))
        self._render_list()

    def _update_cards(self):
        total = len(self.all_certs)
        vencidos = sum(1 for c in self.all_certs if c["dias_para_vencer"] < 0)
        d7 = sum(1 for c in self.all_certs if 0 <= c["dias_para_vencer"] <= 7)
        d15 = sum(1 for c in self.all_certs if 0 < c["dias_para_vencer"] <= 15)
        m1 = sum(1 for c in self.all_certs if 7 < c["dias_para_vencer"] <= 30)
        m3 = sum(1 for c in self.all_certs if 30 < c["dias_para_vencer"] <= 90)
        for k, v in [("total", total), ("vencidos", vencidos), ("dias_7", d7),
                     ("dias_15", d15), ("mes_1", m1), ("meses_3", m3)]:
            self._card_labels[k].configure(text=str(v))

    # ── Acoes ────────────────────────────────────────────────

    def _set_period(self, period):
        self._active_period = period
        for k, b in self._period_btns.items():
            b.configure(fg_color=COLORS["primary"] if k == period else COLORS["muted"])
        self._pagination.reset()
        self._apply_filters()

    def _on_search(self):
        self._pagination.reset()
        self._apply_filters()

    def _on_filter(self):
        self._pagination.reset()
        self._apply_filters()

    # ── Renderizacao da lista ─────────────────────────────────

    def _render_list(self):
        for w in self._list.winfo_children():
            w.destroy()

        fonts = get_fonts()
        start = self._pagination.offset
        page = self._employees_list[start:start + PaginationBar.ITEMS_PER_PAGE]

        if not page:
            ctk.CTkLabel(self._list, text="Nenhum certificado encontrado",
                         font=fonts["body"], text_color=COLORS["muted"]).grid(row=0, column=0, pady=30)
            self.update_idletasks()
            try:
                self._list._parent_canvas.configure(scrollregion=self._list._parent_canvas.bbox("all"))
            except Exception:
                pass
            return

        for i, (emp_key, certs) in enumerate(page):
            emp_id, emp_name, emp_cpf, emp_funcao = emp_key
            self._make_employee_card(i, emp_id, emp_name, emp_cpf, emp_funcao, certs)

        self.update_idletasks()
        try:
            self._list._parent_canvas.configure(scrollregion=self._list._parent_canvas.bbox("all"))
        except Exception:
            pass
        #self.after(50, lambda: self._fit_scroll_height(0))

    def _make_employee_card(self, row, emp_id, name, cpf, funcao, certs):
        fonts = get_fonts()
        worst = min(certs, key=lambda c: c["dias_para_vencer"])["status"]

        card = ctk.CTkFrame(self._list, fg_color=COLORS["surface"], corner_radius=8,
                            border_width=1, border_color=COLORS["border"], cursor="hand2")
        card.grid(row=row, column=0, sticky="ew", pady=3)
        card.grid_columnconfigure(1, weight=1)

        # Indicador lateral
        ctk.CTkFrame(card, fg_color=STATUS_COLORS.get(worst, COLORS["muted"]),
                     width=4, height=40, corner_radius=2
                     ).grid(row=0, column=0, rowspan=2, padx=(8, 5), pady=8, sticky="ns")

        # Nome
        ctk.CTkLabel(card, text=name, font=fonts["body_bold"],
                     text_color=COLORS["text"], anchor="w"
                     ).grid(row=0, column=1, sticky="sw", padx=5, pady=(8, 0))

        # CPF | Funcao
        info = ""
        if cpf:
            info = cpf
        if funcao:
            info = f"{info} | {funcao}" if info else funcao
        ctk.CTkLabel(card, text=info, font=fonts["small"],
                     text_color=COLORS["muted"], anchor="w"
                     ).grid(row=1, column=1, sticky="nw", padx=5, pady=(0, 5))

        # Contagem
        n_asos = sum(1 for c in certs if c.get("nr_code") == "ASO")
        n_certs = len(certs) - n_asos
        ctk.CTkLabel(card, text=f"{n_certs} cert. | {n_asos} ASO(s)",
                     font=fonts["small"], text_color=COLORS["secondary"]
                     ).grid(row=0, column=2, rowspan=2, padx=(10, 4), pady=8, sticky="e")

        # Acoes rapidas: emitir novamente / ver historico
        if self._on_navigate:
            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.grid(row=0, column=3, rowspan=2, padx=(4, 8), pady=6, sticky="e")
            ctk.CTkButton(
                btns, text="Emitir", width=58, height=26, corner_radius=4,
                font=fonts["small"], fg_color=COLORS["success"], hover_color="#256B28",
                command=lambda eid=emp_id: self._action_emit(eid)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                btns, text="ASO", width=48, height=26, corner_radius=4,
                font=fonts["small"], fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
                command=lambda eid=emp_id: self._action_aso(eid)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                btns, text="Historico", width=72, height=26, corner_radius=4,
                font=fonts["small"], fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                command=lambda eid=emp_id, n=name: self._action_history(eid, n)
            ).pack(side="left", padx=2)

        # Tabela (filha do card, nao do list_frame)
        tbl = self._make_table(certs, parent=card)
        if emp_id in self._expanded:
            tbl.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 5))

        # Toggle via bind recursivo — debounce global para o card todo (evita duplo disparo canvas+label)
        def toggle(e=None, _id=emp_id, _tbl=tbl):
            # clique em botao de acao nao expande/colapsa o card
            if e is not None and "ctkbutton" in str(getattr(e, "widget", "")):
                return "break"
            now = time.time()
            last = self._last_toggle.get(_id, 0)
            if now - last < 0.3:
                return "break"
            self._last_toggle[_id] = now
            if _id in self._expanded:
                self._expanded.discard(_id)
                _tbl.grid_remove()
            else:
                self._expanded.add(_id)
                _tbl.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 5))
            self.update_idletasks()
            try:
                self._list._parent_canvas.configure(scrollregion=self._list._parent_canvas.bbox("all"))
            except Exception:
                pass
            return "break"

        self._bind_clicks(card, toggle)

    def _make_table(self, certs, parent):
        fonts = get_fonts()
        tbl = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=6)
        tbl.grid_columnconfigure(1, weight=1)

        # Cabecalho
        hdr = ctk.CTkFrame(tbl, fg_color=COLORS["primary"], corner_radius=4, height=30)
        hdr.grid(row=0, column=0, columnspan=5, sticky="ew", padx=0, pady=(0, 2))
        hdr.pack_propagate(False)
        for c in range(5):
            hdr.grid_columnconfigure(c, weight=[1, 2, 1, 1, 1][c])
        for i, txt in enumerate(["NR", "Treinamento", "Validade", "Dias", "Status"]):
            ctk.CTkLabel(hdr, text=txt, font=fonts["small_bold"],
                         text_color=COLORS["surface"], anchor="center"
                         ).grid(row=0, column=i, padx=8, pady=4, sticky="ew")

        # Linhas
        for idx, cert in enumerate(sorted(certs, key=lambda c: c["dias_para_vencer"])):
            bg = "#F0F4F8" if idx % 2 else "#F8FAFC"
            rf = ctk.CTkFrame(tbl, fg_color=bg, corner_radius=0, height=32)
            rf.grid(row=idx + 1, column=0, columnspan=5, sticky="ew", padx=0, pady=0)
            rf.pack_propagate(False)
            for c in range(5):
                rf.grid_columnconfigure(c, weight=[1, 2, 1, 1, 1][c])

            ctk.CTkLabel(rf, text=cert["nr_code"], font=fonts["body"],
                         text_color=COLORS["text"], anchor="center"
                         ).grid(row=0, column=0, padx=8, pady=4, sticky="ew")

            ctk.CTkLabel(rf, text=cert["descricao_treinamento"][:40], font=fonts["body"],
                         text_color=COLORS["text"], anchor="center"
                         ).grid(row=0, column=1, padx=8, pady=4, sticky="ew")

            val = cert["data_validade"]
            val_str = date.fromisoformat(val).strftime("%d/%m/%Y") if val else "-"
            ctk.CTkLabel(rf, text=val_str, font=fonts["body"],
                         text_color=COLORS["text"], anchor="center"
                         ).grid(row=0, column=2, padx=8, pady=4, sticky="ew")

            d = cert["dias_para_vencer"]
            if d < 0:
                d_txt, d_col = f"Vencido {abs(d)}d", COLORS["error"]
            elif d <= 7:
                d_txt, d_col = f"{d}d", COLORS["error"]
            elif d <= 15:
                d_txt, d_col = f"{d}d", "#E65100"
            elif d <= 30:
                d_txt, d_col = f"{d}d", COLORS["warning"]
            else:
                d_txt, d_col = f"{d}d", COLORS["success"]
            ctk.CTkLabel(rf, text=d_txt, font=fonts["body_bold"],
                         text_color=d_col, anchor="center"
                         ).grid(row=0, column=3, padx=8, pady=4, sticky="ew")

            ctk.CTkLabel(rf, text=cert["status"].upper(), font=fonts["small_bold"],
                         text_color=COLORS["surface"], corner_radius=4,
                         fg_color=STATUS_COLORS.get(cert["status"], COLORS["muted"]),
                         padx=6, pady=2
                         ).grid(row=0, column=4, padx=8, pady=4)

        return tbl

    @staticmethod
    def _bind_clicks(widget, handler):
        # hotfix: bindar SO no _canvas quando existir, senao no widget — evita duplo disparo (canvas + widget)
        if hasattr(widget, "_canvas") and widget._canvas is not None:
            try:
                widget._canvas.bind("<ButtonRelease-1>", handler, add="+")
            except Exception:
                pass
        else:
            try:
                widget.bind("<ButtonRelease-1>", handler, add="+")
            except Exception:
                try:
                    widget.bind("<ButtonRelease-1>", handler)
                except Exception:
                    pass
        for child in widget.winfo_children():
            VencimentosPage._bind_clicks(child, handler)

    def refresh(self):
        self._load_data()
