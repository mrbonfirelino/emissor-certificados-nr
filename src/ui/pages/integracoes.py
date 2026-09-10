"""Aba de Integrações (Fábricas de Clientes) — v1.22.0.

Cadastro de integrações por empresa vinculadas ao funcionário, com
controle de validade (marcador de validade, sem geração de certificado).
Os vencimentos aparecem na aba Vencimentos (nr_code 'INTEGRAÇÃO').
"""
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import customtkinter as ctk

from src.ui.styles import COLORS, get_fonts
from src.ui.components.scroll_frame import ScrollListFrame
from src.ui.components.pagination import PaginationBar
from src.core.integracao_repo import IntegracaoRepository
from src.core.employee_repo import EmployeeRepository
from src.utils.error_log import log_error
from src.utils.ctk_patches import enable_placeholder, search_query, fit_dialog, open_modal, release_modal


def _br(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)


def _iso(valor: str):
    """dd/mm/aaaa -> ISO. Levanta ValueError se inválida."""
    valor = (valor or "").strip()
    if not valor:
        return None
    d = datetime.strptime(valor, "%d/%m/%Y").date()
    return d.isoformat()


class IntegracoesPage(ctk.CTkFrame):
    def __init__(self, master, employee_repo: EmployeeRepository = None,
                 integracao_repo: IntegracaoRepository = None, **kwargs):
        super().__init__(master, **kwargs)
        self.employee_repo = employee_repo or EmployeeRepository()
        self.integ_repo = integracao_repo or IntegracaoRepository()
        self.fonts = get_fonts()
        self._search_var = ctk.StringVar()
        self._build_ui()
        self.after(250, self.refresh)

    # ── Layout ────────────────────────────────────────────────

    def _build_ui(self):
        fonts = self.fonts
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Row 0 — Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="Integrações — Fábricas de Clientes",
                     font=fonts["title"], text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
        self.lbl_count = ctk.CTkLabel(header, text="0 integração(ões)",
                                      font=fonts["small"], text_color=COLORS["muted"])
        self.lbl_count.grid(row=0, column=1, sticky="e")

        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.grid(row=0, column=2, sticky="e", padx=(10, 0))
        ctk.CTkButton(btns, text="Empresas", width=100, height=32, corner_radius=6,
                      font=fonts["body_bold"], fg_color=COLORS["accent"],
                      hover_color=COLORS["secondary"],
                      command=self._abrir_empresas).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="+ Nova Integração", width=150, height=32, corner_radius=6,
                      font=fonts["body_bold"], fg_color=COLORS["success"], hover_color="#256B28",
                      command=self._nova_integracao).pack(side="left", padx=4)

        # Row 1 — Busca + por página
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        filtros.grid_columnconfigure(0, weight=1)
        self._search_entry = ctk.CTkEntry(filtros, textvariable=self._search_var,
                                          placeholder_text="Buscar por funcionário, empresa ou tipo...",
                                          font=fonts["body"], height=36, corner_radius=8,
                                          border_color=COLORS["border"])
        self._search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        enable_placeholder(self._search_entry)
        self._search_entry.bind("<Return>", lambda *_: self._on_search())
        ctk.CTkButton(filtros, text="Buscar", width=80, height=36,
                      font=fonts["body_bold"], fg_color=COLORS["secondary"],
                      hover_color=COLORS["primary"],
                      command=self._on_search).grid(row=0, column=1, padx=(0, 15))
        ctk.CTkButton(filtros, text="Limpar", width=70, height=36, corner_radius=6,
                      font=fonts["body"], fg_color="transparent", border_width=1,
                      border_color=COLORS["border"], hover_color=COLORS["surface"],
                      text_color=COLORS["text"],
                      command=self._limpar).grid(row=0, column=2, padx=(0, 15))
        ctk.CTkLabel(filtros, text="Por página:", font=fonts["small_bold"],
                     text_color=COLORS["text"]).grid(row=0, column=3, padx=(0, 4))
        self._per_page_var = ctk.StringVar(value="10")
        ctk.CTkOptionMenu(filtros, variable=self._per_page_var,
                          values=["10", "20", "50", "100"],
                          command=lambda *_: self._change_per_page(),
                          font=fonts["small"], width=70, height=32, corner_radius=6,
                          fg_color=COLORS["primary"], button_color=COLORS["secondary"]
                          ).grid(row=0, column=4)

        # Row 2 — Lista
        self.list_frame = ScrollListFrame(self, fg_color=COLORS["surface"],
                                          corner_radius=12)
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 2))
        self.list_frame.grid_columnconfigure(0, weight=1)
        self._create_table_header()

        # Row 3 — Paginação
        self.pagination = PaginationBar(self, on_page_change=self._on_page)
        self.pagination.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))

    def _create_table_header(self):
        fonts = self.fonts
        hdr = ctk.CTkFrame(self.list_frame.body, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        weights = [3, 2, 2, 1, 1, 1, 2]
        for i, w in enumerate(weights):
            hdr.grid_columnconfigure(i, weight=w)
        for i, txt in enumerate(["Funcionário", "Empresa", "Tipo",
                                 "Início", "Validade", "Status", "Ações"]):
            ctk.CTkLabel(hdr, text=txt, font=fonts["small_bold"],
                         text_color=COLORS["muted"], anchor="w"
                         ).grid(row=0, column=i, sticky="ew", padx=5)
        sep = ctk.CTkFrame(self.list_frame.body, height=1, fg_color=COLORS["border"])
        sep.pack(fill="x", padx=10)

    # ── Dados ─────────────────────────────────────────────────

    def _change_per_page(self):
        try:
            n = int(self._per_page_var.get())
        except (TypeError, ValueError):
            n = 10
        self.pagination.items_per_page = n
        self.pagination.reset()
        self._refresh_list()

    def _on_search(self):
        self.pagination.reset()
        self._refresh_list()

    def _limpar(self):
        self._search_var.set("")
        self._search_entry._activate_placeholder()
        self.pagination.reset()
        self._refresh_list()

    def _on_page(self):
        self._refresh_list()

    def refresh(self):
        self._refresh_list()

    def _refresh_list(self):
        for w in self.list_frame.body.winfo_children():
            w.destroy()
        self._create_table_header()
        query = search_query(self._search_entry, self._search_var).strip()
        try:
            total = (self.integ_repo.count_search(query) if query
                     else self.integ_repo.count_all())
            if query:
                rows = self.integ_repo.search(query, limit=self.pagination.items_per_page,
                                              offset=self.pagination.offset)
            else:
                rows = self.integ_repo.get_all(limit=self.pagination.items_per_page,
                                               offset=self.pagination.offset)
        except Exception as e:
            log_error("integracoes-lista", e)
            rows, total = [], 0
        self.pagination.set_total(total)
        self.lbl_count.configure(text=f"{total} integração(ões)")
        if not rows:
            ctk.CTkLabel(self.list_frame.body,
                         text="Nenhuma integração encontrada.\nUse '+ Nova Integração' para vincular um funcionário a uma fábrica de clientes.",
                         font=self.fonts["body"], text_color=COLORS["muted"], justify="center"
                         ).pack(pady=40)
            return
        for idx, r in enumerate(rows):
            self._create_row(r, idx)

    def _create_row(self, integ, idx: int):
        fonts = self.fonts
        row = ctk.CTkFrame(self.list_frame.body, fg_color="transparent")
        row.pack(fill="x", padx=10)
        weights = [3, 2, 2, 1, 1, 1, 2]
        for i, w in enumerate(weights):
            row.grid_columnconfigure(i, weight=w)

        nome = integ.get("funcionario_nome") or "—"
        cpf = integ.get("funcionario_cpf") or ""
        ctk.CTkLabel(row, text=f"{nome} ({cpf})" if cpf else nome,
                     font=fonts["body_bold"], text_color=COLORS["text"], anchor="w"
                     ).grid(row=0, column=0, sticky="ew", padx=5, pady=8)
        ctk.CTkLabel(row, text=integ.get("empresa_nome") or "—",
                     font=fonts["body"], text_color=COLORS["text"], anchor="w"
                     ).grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkLabel(row, text=integ.get("tipo") or "—",
                     font=fonts["body"], text_color=COLORS["secondary"], anchor="w"
                     ).grid(row=0, column=2, sticky="ew", padx=5)
        ctk.CTkLabel(row, text=_br(integ.get("data_inicio")),
                     font=fonts["body"], text_color=COLORS["muted"], anchor="w"
                     ).grid(row=0, column=3, sticky="ew", padx=5)

        dias = integ.get("dias_para_vencer")
        if dias is None:
            try:
                dv = date.fromisoformat(str(integ["data_validade"])[:10])
                dias = (dv - date.today()).days
            except Exception:
                dias = 0
        cor = COLORS["error"] if dias < 0 else (COLORS["warning"] if dias <= 15 else COLORS["success"])
        ctk.CTkLabel(row, text=_br(integ.get("data_validade")),
                     font=fonts["body_bold"], text_color=cor, anchor="w"
                     ).grid(row=0, column=4, sticky="ew", padx=5)

        if dias < 0:
            st_txt, st_cor = "VENCIDA", COLORS["error"]
        elif dias <= 15:
            st_txt, st_cor = f"{dias}d", COLORS["warning"]
        else:
            st_txt, st_cor = "Em dia", COLORS["success"]
        badge = ctk.CTkLabel(row, text=st_txt, font=fonts["small_bold"], text_color=st_cor)
        badge.grid(row=0, column=5, sticky="w", padx=5)

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=6, sticky="e", padx=5)
        ctk.CTkButton(btns, text="Editar", width=52, height=26, corner_radius=4,
                      font=fonts["small"], fg_color=COLORS["accent"],
                      hover_color=COLORS["secondary"],
                      command=lambda r=integ: self._editar_integracao(r)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Excluir", width=52, height=26, corner_radius=4,
                      font=fonts["small"], fg_color=COLORS["error"], hover_color="#B71C1C",
                      command=lambda r=integ: self._excluir(r)).pack(side="left", padx=2)

        sep = ctk.CTkFrame(self.list_frame.body, height=1, fg_color=COLORS["border"])
        sep.pack(fill="x", padx=10)

    # ── Ações ─────────────────────────────────────────────────

    def _excluir(self, integ):
        from tkinter import messagebox
        nome = integ.get("funcionario_nome") or ""
        if not messagebox.askyesno("Excluir integração",
                                   f"Excluir a integração de {nome} na empresa {integ.get('empresa_nome')}?"):
            return
        try:
            self.integ_repo.delete_integracao(integ["id"])
        except Exception as e:
            log_error("integracoes-excluir", e)
            messagebox.showerror("Erro", "Não foi possível excluir a integração.")
        self._refresh_list()

    # ── Diálogo Nova/Editar ───────────────────────────────────

    def _nova_integracao(self):
        self._dialog_integracao(None)

    def _editar_integracao(self, integ):
        self._dialog_integracao(integ)

    def _dialog_integracao(self, integ):
        from tkinter import messagebox
        from src.ui.components.employee_autocomplete import EmployeeAutocomplete

        dlg = ctk.CTkToplevel(self)
        dlg.title("Integração")
        dlg.transient(self)
        fit_dialog(dlg, 440, 300)
        open_modal(dlg)

        fonts = self.fonts
        selecionado = {"emp": None}
        if integ:
            selecionado["emp"] = {"id": integ.get("employee_id"),
                                  "nome": integ.get("funcionario_nome"),
                                  "cpf": integ.get("funcionario_cpf")}

        ctk.CTkLabel(dlg, text="Editar integração" if integ else "Nova integração",
                     font=fonts["title"], text_color=COLORS["text"]).pack(anchor="w", padx=24, pady=(20, 4))

        # Rodapé ANTES do scroll (pack side=bottom): garante Salvar/Cancelar sempre visíveis
        rodape = ctk.CTkFrame(dlg, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=24, pady=(6, 20))

        # Formulário em frame rolável: nunca corta em telas com scaling alto
        scroll = ctk.CTkScrollableFrame(dlg, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 4))
        form = ctk.CTkFrame(scroll, fg_color="transparent")
        form.pack(fill="both", expand=True)
        for i in range(2):
            form.grid_columnconfigure(i, weight=1)

        # Funcionário
        ctk.CTkLabel(form, text="Funcionário", font=fonts["small_bold"],
                     text_color=COLORS["muted"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=(6, 2))
        if integ:
            ctk.CTkLabel(form, text=f"{integ.get('funcionario_nome')} ({integ.get('funcionario_cpf') or 'sem CPF'})",
                         font=fonts["body_bold"], text_color=COLORS["text"], anchor="w"
                         ).grid(row=1, column=0, columnspan=2, sticky="ew")
        else:
            emp_frame = ctk.CTkFrame(form, fg_color="transparent")
            emp_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

            def on_select(emp):
                # EmployeeAutocomplete passa o objeto Employee — normaliza para dict
                selecionado["emp"] = {"id": emp.id, "nome": emp.nome, "cpf": emp.cpf}

            EmployeeAutocomplete(emp_frame, self.employee_repo, on_select=on_select,
                                 placeholder="Digite o nome do funcionário...").pack(fill="x")

        # Empresa
        ctk.CTkLabel(form, text="Empresa (fábrica de clientes)", font=fonts["small_bold"],
                     text_color=COLORS["muted"]).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 2))
        empresas = [e["nome"] for e in self.integ_repo.list_empresas()]
        empresa_var = ctk.StringVar(
            value=integ["empresa_nome"] if integ else (empresas[0] if empresas else ""))
        if empresas:
            ctk.CTkOptionMenu(form, variable=empresa_var, values=empresas,
                              font=fonts["body"], height=32, corner_radius=6,
                              fg_color=COLORS["primary"], button_color=COLORS["secondary"]
                              ).grid(row=3, column=0, columnspan=2, sticky="ew")
        else:
            ctk.CTkLabel(form, text="Nenhuma empresa cadastrada — use o botão 'Empresas'.",
                         font=fonts["small"], text_color=COLORS["error"], anchor="w"
                         ).grid(row=3, column=0, columnspan=2, sticky="w")

        # Tipo
        ctk.CTkLabel(form, text="Tipo de integração", font=fonts["small_bold"],
                     text_color=COLORS["muted"]).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 2))
        tipo_var = ctk.StringVar(value=(integ.get("tipo") or "") if integ else "")
        ctk.CTkEntry(form, textvariable=tipo_var, placeholder_text="Ex.: Integração de máquinas, Assistência técnica...",
                     font=fonts["body"], height=34, corner_radius=6
                     ).grid(row=5, column=0, columnspan=2, sticky="ew")

        # Datas
        ctk.CTkLabel(form, text="Data de início (dd/mm/aaaa)", font=fonts["small_bold"],
                     text_color=COLORS["muted"]).grid(row=6, column=0, sticky="w", pady=(10, 2))
        ctk.CTkLabel(form, text="Data de validade (dd/mm/aaaa) *", font=fonts["small_bold"],
                     text_color=COLORS["muted"]).grid(row=6, column=1, sticky="w", pady=(10, 2), padx=(12, 0))
        ini_var = ctk.StringVar(value=_br(integ.get("data_inicio")) if integ and integ.get("data_inicio")
                               else date.today().strftime("%d/%m/%Y"))
        # Validade padrão: 1 ano a partir de hoje (editável)
        validade_padrao = (date.today() + relativedelta(years=1)).strftime("%d/%m/%Y")
        val_var = ctk.StringVar(value=_br(integ.get("data_validade")) if integ else validade_padrao)
        ctk.CTkEntry(form, textvariable=ini_var, font=fonts["body"], height=34, corner_radius=6
                     ).grid(row=7, column=0, sticky="ew")
        ctk.CTkEntry(form, textvariable=val_var, font=fonts["body"], height=34, corner_radius=6
                     ).grid(row=7, column=1, sticky="ew", padx=(12, 0))

        # Obs
        ctk.CTkLabel(form, text="Observações", font=fonts["small_bold"],
                     text_color=COLORS["muted"]).grid(row=8, column=0, columnspan=2, sticky="w", pady=(10, 2))
        obs_var = ctk.StringVar(value=(integ.get("obs") or "") if integ else "")
        ctk.CTkEntry(form, textvariable=obs_var, placeholder_text="Opcional",
                     font=fonts["body"], height=34, corner_radius=6
                     ).grid(row=9, column=0, columnspan=2, sticky="ew")

        def _salvar():
            try:
                if not integ and not selecionado["emp"]:
                    messagebox.showwarning("Funcionário", "Selecione o funcionário.", parent=dlg)
                    return
                nome_empresa = empresa_var.get()
                if not nome_empresa:
                    messagebox.showwarning("Empresa", "Cadastre uma empresa antes (botão 'Empresas').", parent=dlg)
                    return
                emp = self.integ_repo.get_empresa_por_nome(nome_empresa)
                if not emp:
                    messagebox.showerror("Empresa", "Empresa não encontrada.", parent=dlg)
                    return
                ini = _iso(ini_var.get()) if ini_var.get().strip() else None
                val = _iso(val_var.get())
                if not val:
                    messagebox.showwarning("Validade", "Informe a data de validade (dd/mm/aaaa).", parent=dlg)
                    return
                if integ:
                    self.integ_repo.update_integracao(integ["id"], empresa_id=emp["id"],
                                                      tipo=tipo_var.get().strip(),
                                                      data_inicio=ini, data_validade=val,
                                                      obs=obs_var.get().strip() or None)
                else:
                    self.integ_repo.add_integracao(employee_id=selecionado["emp"]["id"],
                                                   empresa_id=emp["id"],
                                                   tipo=tipo_var.get().strip(),
                                                   data_inicio=ini, data_validade=val,
                                                   obs=obs_var.get().strip() or None)
            except ValueError as e:
                messagebox.showerror("Dados inválidos", str(e), parent=dlg)
                return
            except Exception as e:
                log_error("integracoes-salvar", e)
                messagebox.showerror("Erro", "Não foi possível salvar a integração.", parent=dlg)
                return
            release_modal(dlg)
            dlg.destroy()
            self._refresh_list()

        ctk.CTkButton(rodape, text="Cancelar", width=90, fg_color="transparent",
                      border_width=1, border_color=COLORS["border"],
                      text_color=COLORS["text"], hover_color=COLORS["surface"],
                      command=lambda: (release_modal(dlg), dlg.destroy())).pack(side="right", padx=4)
        ctk.CTkButton(rodape, text="Salvar", width=110, fg_color=COLORS["success"],
                      hover_color="#256B28", command=_salvar).pack(side="right", padx=4)

    # ── Diálogo Empresas ──────────────────────────────────────

    def _abrir_empresas(self):
        from tkinter import messagebox

        dlg = ctk.CTkToplevel(self)
        dlg.title("Empresas — Fábricas de Clientes")
        dlg.transient(self)
        fit_dialog(dlg, 370, 240)
        open_modal(dlg)
        fonts = self.fonts

        ctk.CTkLabel(dlg, text="Empresas (fábricas de clientes)", font=fonts["title"],
                     text_color=COLORS["text"]).pack(anchor="w", padx=24, pady=(20, 2))
        ctk.CTkLabel(dlg, text="Empresas em que é possível fazer integração.",
                     font=fonts["small"], text_color=COLORS["muted"]).pack(anchor="w", padx=24)

        ctk.CTkButton(dlg, text="Fechar", width=90, fg_color="transparent",
                      border_width=1, border_color=COLORS["border"],
                      text_color=COLORS["text"], hover_color=COLORS["surface"],
                      command=dlg.destroy).pack(side="bottom", anchor="e", padx=24, pady=(0, 16))

        lista = ctk.CTkScrollableFrame(dlg, fg_color=COLORS["surface"], corner_radius=10)

        def _render_empresas():
            for w in lista.winfo_children():
                w.destroy()
            empresas = self.integ_repo.list_empresas()
            if not empresas:
                ctk.CTkLabel(lista, text="Nenhuma empresa cadastrada.",
                             font=fonts["body"], text_color=COLORS["muted"]).pack(pady=20)
                return
            for e in empresas:
                linha = ctk.CTkFrame(lista, fg_color="transparent")
                linha.pack(fill="x", padx=8, pady=3)
                linha.grid_columnconfigure(0, weight=1)
                uso = self.integ_repo.count_integracoes_empresa(e["id"])
                ctk.CTkLabel(linha, text=f"{e['nome']}  ({e.get('cnpj') or 'sem CNPJ'}) — {uso} integração(ões)",
                             font=fonts["body"], text_color=COLORS["text"], anchor="w"
                             ).grid(row=0, column=0, sticky="ew")

                def _renomear(emp=e):
                    from tkinter import simpledialog
                    novo = simpledialog.askstring("Renomear", "Novo nome da empresa:",
                                                  initialvalue=emp["nome"], parent=dlg)
                    if novo and novo.strip():
                        try:
                            self.integ_repo.update_empresa(emp["id"], nome=novo.strip())
                        except ValueError as err:
                            messagebox.showwarning("Empresa", str(err), parent=dlg)
                        _render_empresas()

                def _excluir(emp=e):
                    try:
                        self.integ_repo.delete_empresa(emp["id"])
                    except ValueError as err:
                        messagebox.showwarning("Empresa em uso", str(err), parent=dlg)
                        return
                    _render_empresas()

                ctk.CTkButton(linha, text="Renomear", width=76, height=26, corner_radius=4,
                              font=fonts["small"], fg_color=COLORS["accent"],
                              hover_color=COLORS["secondary"], command=_renomear
                              ).grid(row=0, column=1, padx=3)
                ctk.CTkButton(linha, text="Excluir", width=64, height=26, corner_radius=4,
                              font=fonts["small"], fg_color=COLORS["error"], hover_color="#B71C1C",
                              command=_excluir).grid(row=0, column=2, padx=3)

        _render_empresas()

        nova = ctk.CTkFrame(dlg, fg_color="transparent")
        nova.pack(side="bottom", fill="x", padx=24, pady=(0, 4))
        lista.pack(fill="both", expand=True, padx=24, pady=10)
        nova.grid_columnconfigure(0, weight=2)
        nova.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(nova, text="Nome da empresa", font=fonts["small_bold"],
                     text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", pady=(4, 2))
        ctk.CTkLabel(nova, text="CNPJ (opcional)", font=fonts["small_bold"],
                     text_color=COLORS["text"]).grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(4, 2))
        nome_var = ctk.StringVar()
        cnpj_var = ctk.StringVar()
        ctk.CTkEntry(nova, textvariable=nome_var, placeholder_text="Nome da empresa",
                     font=fonts["body"], height=34, corner_radius=6
                     ).grid(row=1, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkEntry(nova, textvariable=cnpj_var, placeholder_text="CNPJ (opcional)",
                     font=fonts["body"], height=34, corner_radius=6
                     ).grid(row=1, column=1, sticky="ew", padx=(0, 6))

        def _adicionar():
            try:
                self.integ_repo.add_empresa(nome_var.get(), cnpj_var.get().strip() or None)
            except ValueError as err:
                messagebox.showwarning("Empresa", str(err), parent=dlg)
                return
            nome_var.set("")
            cnpj_var.set("")
            _render_empresas()

        ctk.CTkButton(nova, text="+ Adicionar", width=100, height=34, corner_radius=6,
                      font=fonts["body_bold"], fg_color=COLORS["success"], hover_color="#256B28",
                      command=_adicionar).grid(row=1, column=2, sticky="e")
