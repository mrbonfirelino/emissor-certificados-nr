import customtkinter as ctk
from datetime import date
from src.ui.styles import COLORS, get_fonts
from src.core.history_repo import HistoryRepository
from src.core.employee_repo import EmployeeRepository


class VencimentosPage(ctk.CTkFrame):
    def __init__(self, master, history_repo: HistoryRepository, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.history_repo = history_repo
        self.employee_repo = EmployeeRepository()
        self.all_certs = []
        self.filtered_certs = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        fonts = get_fonts()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Row 0: Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Vencimentos",
            font=fonts["title"], text_color=COLORS["text"]
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header, text=date.today().strftime("%d/%m/%Y"),
            font=fonts["small"], text_color=COLORS["muted"]
        ).grid(row=0, column=1, sticky="e", padx=(10, 0))

        # Row 1: Dashboard cards (ACIMA da busca)
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        for i in range(5):
            self.cards_frame.grid_columnconfigure(i, weight=1)

        self.card_labels = {}
        card_configs = [
            ("total", "TOTAL DE DOCUMENTOS", COLORS["primary"]),
            ("meses_3", "3 Meses", COLORS["success"]),
            ("mes_1", "1 Mes", COLORS["warning"]),
            ("dias_15", "15 Dias", "#E65100"),
            ("dias_7", "7 Dias", COLORS["error"]),
        ]

        for i, (key, label, color) in enumerate(card_configs):
            card = ctk.CTkFrame(self.cards_frame, fg_color=COLORS["surface"], corner_radius=10,
                               border_width=1, border_color=COLORS["border"])
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")

            ctk.CTkLabel(
                card, text="0",
                font=("Segoe UI", 24, "bold"), text_color=color
            ).pack(pady=(10, 0))

            ctk.CTkLabel(
                card, text=label,
                font=fonts["small"], text_color=COLORS["muted"]
            ).pack(pady=(0, 10))

            self.card_labels[key] = card.winfo_children()[-2]

        # Row 2: Barra de pesquisa + filtros
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        self.search_entry = ctk.CTkEntry(
            search_frame, textvariable=self.search_var,
            placeholder_text="Buscar funcionario, CPF ou NR...",
            font=fonts["body"], height=36, corner_radius=8,
            border_color=COLORS["border"]
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 15))

        # Label + Filtro por NR
        ctk.CTkLabel(
            search_frame, text="NRs:",
            font=fonts["body_bold"], text_color=COLORS["text"]
        ).grid(row=0, column=1, padx=(0, 3))
        self.nr_filter_var = ctk.StringVar(value="TODAS")
        self.nr_filter = ctk.CTkOptionMenu(
            search_frame, variable=self.nr_filter_var,
            values=["TODAS", "NR-01", "NR-06", "NR-12", "NR-18", "NR-26", "NR-35"],
            command=self._on_filter_change,
            font=fonts["body"], width=110, height=36, corner_radius=8,
            fg_color=COLORS["primary"], button_color=COLORS["secondary"]
        )
        self.nr_filter.grid(row=0, column=2, padx=(0, 10))

        # Label + Filtro por Funcao
        ctk.CTkLabel(
            search_frame, text="Função:",
            font=fonts["body_bold"], text_color=COLORS["text"]
        ).grid(row=0, column=3, padx=(0, 3))
        funcoes_list = self.employee_repo.get_all_funcoes()
        self.funcao_filter_var = ctk.StringVar(value="TODAS")
        self.funcao_filter = ctk.CTkOptionMenu(
            search_frame, variable=self.funcao_filter_var,
            values=["TODAS"] + funcoes_list,
            command=self._on_filter_change,
            font=fonts["body"], width=140, height=36, corner_radius=8,
            fg_color=COLORS["primary"], button_color=COLORS["secondary"]
        )
        self.funcao_filter.grid(row=0, column=4)

        # Row 3: Lista de certificados (PREENCHE TODO O ESPAÇO)
        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["surface"], corner_radius=10,
            border_width=1, border_color=COLORS["border"]
        )
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.list_frame.bind("<MouseWheel>", lambda e: self.list_frame._parent_canvas.yview_scroll(int(-1 * (e.delta / 120) * 2.5), "units"))

    def _load_data(self):
        self.all_certs = self.history_repo.get_certificates_with_expiration()
        self._apply_filters()

    def _apply_filters(self):
        search = self.search_var.get().lower().strip()
        nr_filter = self.nr_filter_var.get()
        funcao_filter = self.funcao_filter_var.get()

        self.filtered_certs = []
        for cert in self.all_certs:
            if nr_filter != "TODAS" and cert["nr_code"] != nr_filter:
                continue
            if funcao_filter != "TODAS" and cert.get("funcionario_funcao", "") != funcao_filter:
                continue
            if search:
                if (search not in cert["funcionario_nome"].lower() and
                    search not in cert["funcionario_cpf"] and
                    search not in cert["nr_code"].lower()):
                    continue
            self.filtered_certs.append(cert)

        self._update_cards()
        self._render_list()

    def _update_cards(self):
        total = len(self.filtered_certs)
        meses_3 = sum(1 for c in self.filtered_certs if 30 < c["dias_para_vencer"] <= 90)
        mes_1 = sum(1 for c in self.filtered_certs if 7 < c["dias_para_vencer"] <= 30)
        dias_15 = sum(1 for c in self.filtered_certs if 0 < c["dias_para_vencer"] <= 15)
        dias_7 = sum(1 for c in self.filtered_certs if c["dias_para_vencer"] <= 7)

        self.card_labels["total"].configure(text=str(total))
        self.card_labels["meses_3"].configure(text=str(meses_3))
        self.card_labels["mes_1"].configure(text=str(mes_1))
        self.card_labels["dias_15"].configure(text=str(dias_15))
        self.card_labels["dias_7"].configure(text=str(dias_7))

    def _render_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.filtered_certs:
            ctk.CTkLabel(
                self.list_frame, text="Nenhum certificado encontrado",
                font=get_fonts()["body"], text_color=COLORS["muted"]
            ).grid(row=0, column=0, pady=30)
            return

        # Agrupar por funcionario
        employees = {}
        for cert in self.filtered_certs:
            key = (cert["employee_id"], cert["funcionario_nome"], cert["funcionario_cpf"],
                   cert.get("funcionario_funcao", ""))
            if key not in employees:
                employees[key] = []
            employees[key].append(cert)

        row_idx = 0
        for (emp_id, emp_name, emp_cpf, emp_funcao), certs in employees.items():
            row_idx = self._create_employee_section(row_idx, emp_name, emp_cpf, emp_funcao, certs)

    def _create_employee_section(self, row_idx, name, cpf, funcao, certs):
        fonts = get_fonts()

        # Header do funcionario
        emp_frame = ctk.CTkFrame(self.list_frame, fg_color=COLORS["surface"], corner_radius=8,
                                border_width=1, border_color=COLORS["border"])
        emp_frame.grid(row=row_idx, column=0, sticky="ew", pady=3)
        emp_frame.grid_columnconfigure(1, weight=1)

        # Status indicator - cor do pior vencimento
        worst_status = min(certs, key=lambda c: c["dias_para_vencer"])["status"]
        status_colors = {
            "vencido": COLORS["error"], "urgente": COLORS["error"],
            "critico": "#E65100", "atencao": COLORS["warning"],
            "proximo": COLORS["success"], "ok": COLORS["success"]
        }
        indicator = ctk.CTkFrame(emp_frame, fg_color=status_colors.get(worst_status, COLORS["muted"]),
                                width=4, height=40, corner_radius=2)
        indicator.grid(row=0, column=0, rowspan=2, padx=(8, 5), pady=8, sticky="ns")

        ctk.CTkLabel(
            emp_frame, text=name,
            font=fonts["body_bold"], text_color=COLORS["text"], anchor="w"
        ).grid(row=0, column=1, sticky="sw", padx=5, pady=(8, 0))

        cpf_funcao = f"{cpf}" if cpf else ""
        if funcao:
            cpf_funcao = f"{cpf} | {funcao}" if cpf else funcao
        ctk.CTkLabel(
            emp_frame, text=cpf_funcao,
            font=fonts["small"], text_color=COLORS["muted"], anchor="w"
        ).grid(row=1, column=1, sticky="nw", padx=5, pady=(0, 5))

        # Contador de certificados
        ctk.CTkLabel(
            emp_frame, text=f"{len(certs)} certificado(s)",
            font=fonts["small"], text_color=COLORS["secondary"]
        ).grid(row=0, column=2, rowspan=2, padx=10, pady=8, sticky="e")

        # Tabela de certificados
        table_frame = ctk.CTkFrame(self.list_frame, fg_color="#F8FAFC", corner_radius=6)
        table_frame.grid(row=row_idx + 1, column=0, sticky="ew", padx=10, pady=(0, 5))
        table_frame.grid_columnconfigure(1, weight=1)

        # Header da tabela
        headers = ["NR", "Treinamento", "Validade", "Dias", "Status"]
        header_frame = ctk.CTkFrame(table_frame, fg_color=COLORS["primary"], corner_radius=4, height=30)
        header_frame.grid(row=0, column=0, columnspan=5, sticky="ew", padx=0, pady=(0, 2))
        header_frame.pack_propagate(False)
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=2)
        header_frame.grid_columnconfigure(2, weight=1)
        header_frame.grid_columnconfigure(3, weight=1)
        header_frame.grid_columnconfigure(4, weight=1)

        for i, h in enumerate(headers):
            ctk.CTkLabel(
                header_frame, text=h,
                font=fonts["small_bold"], text_color=COLORS["surface"], anchor="w"
            ).grid(row=0, column=i, padx=8, pady=4, sticky="w")

        # Linha separadora
        sep = ctk.CTkFrame(table_frame, height=1, fg_color=COLORS["border"])
        sep.grid(row=1, column=0, columnspan=5, sticky="ew", padx=8)

        # Dados
        for idx, cert in enumerate(sorted(certs, key=lambda c: c["dias_para_vencer"])):
            r = idx + 2
            row_bg = "#F0F4F8" if idx % 2 == 1 else "#F8FAFC"

            row_frame = ctk.CTkFrame(table_frame, fg_color=row_bg, corner_radius=0, height=32)
            row_frame.grid(row=r, column=0, columnspan=5, sticky="ew", padx=0, pady=0)
            row_frame.pack_propagate(False)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=2)
            row_frame.grid_columnconfigure(2, weight=1)
            row_frame.grid_columnconfigure(3, weight=1)
            row_frame.grid_columnconfigure(4, weight=1)

            ctk.CTkLabel(
                row_frame, text=cert["nr_code"],
                font=fonts["body"], text_color=COLORS["text"], anchor="w"
            ).grid(row=0, column=0, padx=8, pady=4, sticky="w")

            ctk.CTkLabel(
                row_frame, text=cert["descricao_treinamento"][:40],
                font=fonts["body"], text_color=COLORS["text"], anchor="w"
            ).grid(row=0, column=1, padx=8, pady=4, sticky="w")

            validade = cert["data_validade"]
            if validade:
                from datetime import date as dt_date
                v = dt_date.fromisoformat(validade)
                validade_str = v.strftime("%d/%m/%Y")
            else:
                validade_str = "-"
            ctk.CTkLabel(
                row_frame, text=validade_str,
                font=fonts["body"], text_color=COLORS["text"], anchor="w"
            ).grid(row=0, column=2, padx=8, pady=4, sticky="w")

            dias = cert["dias_para_vencer"]
            if dias < 0:
                dias_text = f"Vencido ha {abs(dias)}d"
                dias_color = COLORS["error"]
            else:
                dias_text = f"{dias}d"
                if dias <= 7:
                    dias_color = COLORS["error"]
                elif dias <= 15:
                    dias_color = "#E65100"
                elif dias <= 30:
                    dias_color = COLORS["warning"]
                else:
                    dias_color = COLORS["success"]

            ctk.CTkLabel(
                row_frame, text=dias_text,
                font=fonts["body_bold"], text_color=dias_color, anchor="w"
            ).grid(row=0, column=3, padx=8, pady=4, sticky="w")

            status_text = cert["status"].upper().replace("_", " ")
            badge = ctk.CTkLabel(
                row_frame, text=status_text,
                font=fonts["small_bold"],
                text_color=COLORS["surface"],
                fg_color=status_colors.get(cert["status"], COLORS["muted"]),
                corner_radius=4, padx=6, pady=2
            )
            badge.grid(row=0, column=4, padx=8, pady=4, sticky="w")

        return row_idx + len(certs) + 2

    def _on_search(self, *args):
        self._apply_filters()

    def _on_filter_change(self, *args):
        self._apply_filters()

    def refresh(self):
        self._load_data()
