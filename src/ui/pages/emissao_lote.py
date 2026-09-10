"""Emissão em Lote de Certificados NR (item 2.26).

Fluxo: escolher o NR -> selecionar funcionarios (somente com CPF) ->
"Revisar e emitir" (dados globais + ajustes individuais + preview) ->
gerar os PDFs na pasta de cada funcionario (o proprio
CertificateService grava o registro e espelha na rede).

A validade pode ser definida por lote ou por funcionario (meses);
vazio/no dialogo = usa a validade do template.
"""

from datetime import date, datetime
import threading
import os

import customtkinter as ctk
from PIL import Image

from src.ui.styles import COLORS, get_fonts
from src.ui.components.pagination import PaginationBar
from src.ui.components.scroll_frame import ScrollListFrame
from src.utils.ctk_patches import fit_dialog, open_modal, release_modal, enable_placeholder, search_query
from src.utils.text_utils import normalize_text
from src.utils.paths import get_data_dir
from src.utils.error_log import log_error
from src.core.template_loader import load_all_templates
from src.core.models import Employee


def _validar_data_br(valor: str):
    """dd/mm/aaaa -> date, ou None se invalida."""
    try:
        return datetime.strptime((valor or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


class EmissaoLotePage(ctk.CTkFrame):
    def __init__(self, master, employee_repo, certificate_service):
        super().__init__(master, fg_color="transparent")
        self.employee_repo = employee_repo
        self.certificate_service = certificate_service
        self.fonts = get_fonts()

        self._templates = load_all_templates()
        self._nr_codes = sorted(self._templates.keys())
        self._nr_code = None
        self._template = None

        self._all: list[Employee] = []
        self._filtered: list[Employee] = []
        self._selected: set = set()  # ids (persiste entre paginas)
        self._gerando = False

        self._build_ui()
        self.refresh()

    # ── UI ────────────────────────────────────────────────────
    def _build_ui(self):
        fonts = self.fonts
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_propagate(False)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Emissão em Lote",
                     font=fonts["title"], text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
        self.lbl_nr_info = ctk.CTkLabel(header, text="", font=fonts["small"],
                                        text_color=COLORS["muted"])
        self.lbl_nr_info.grid(row=0, column=1, sticky="e")

        # NR
        nr_frame = ctk.CTkFrame(self, fg_color="transparent")
        nr_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))
        ctk.CTkLabel(nr_frame, text="NR:", font=fonts["body_bold"],
                     text_color=COLORS["text"]).pack(side="left", padx=(0, 8))
        self._nr_var = ctk.StringVar(value=self._nr_codes[0] if self._nr_codes else "")
        self.nr_menu = ctk.CTkOptionMenu(
            nr_frame, values=self._nr_codes, variable=self._nr_var,
            width=200, font=fonts["body"], command=self._on_nr,
            fg_color=COLORS["primary"], button_color=COLORS["secondary"])
        self.nr_menu.pack(side="left")

        # Controles de busca/selecao
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=20, pady=(2, 6))
        self._search_var = ctk.StringVar()
        self._search_entry = ctk.CTkEntry(
            controls, textvariable=self._search_var, width=280,
            placeholder_text="Buscar por nome ou CPF...", font=fonts["body"], height=32)
        self._search_entry.pack(side="left", padx=(0, 8))
        enable_placeholder(self._search_entry)
        self._search_entry.bind("<Return>", lambda *_: self._apply_filters())
        ctk.CTkButton(controls, text="Buscar", width=80, height=32,
                      font=fonts["body_bold"], command=self._apply_filters).pack(side="left", padx=(0, 8))
        ctk.CTkButton(controls, text="Limpar", width=70, height=32, fg_color="transparent",
                      border_width=1, border_color=COLORS["border"], text_color=COLORS["text"],
                      hover_color=COLORS["surface"],
                      command=self._limpar).pack(side="left", padx=(0, 16))
        ctk.CTkLabel(controls, text="Por página:", font=fonts["small"],
                     text_color=COLORS["muted"]).pack(side="left", padx=(0, 4))
        self._per_page_var = ctk.StringVar(value="10")
        ctk.CTkOptionMenu(controls, values=["10", "20", "50", "100"],
                          variable=self._per_page_var, width=80, height=30,
                          font=fonts["small"], command=self._change_per_page).pack(side="left")
        self.lbl_selecionados = ctk.CTkLabel(controls, text="Selecionados: 0",
                                             font=fonts["body_bold"], text_color=COLORS["primary"])
        self.lbl_selecionados.pack(side="right")

        # Lista de funcionarios
        self.list_frame = ScrollListFrame(self, fg_color=COLORS["surface"], corner_radius=12)
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(4, 2))

        # Paginacao
        self.pagination = PaginationBar(self, on_page_change=self._render_list)
        self.pagination.grid(row=4, column=0, pady=(4, 2))

        # Rodape de acoes
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=20, pady=(4, 14))
        self.btn_gerar = ctk.CTkButton(footer, text="Revisar e emitir", width=150, height=34,
                                       font=fonts["body_bold"], fg_color=COLORS["success"],
                                       hover_color="#256B28", command=self._revisar)
        self.btn_gerar.pack(side="right")
        ctk.CTkButton(footer, text="Limpar seleção", width=120, height=34, fg_color="transparent",
                      border_width=1, border_color=COLORS["border"], text_color=COLORS["text"],
                      hover_color=COLORS["surface"], command=self._limpar_selecao).pack(side="right", padx=(0, 8))

        self._on_nr(self._nr_var.get())

    # ── Dados ─────────────────────────────────────────────────
    def refresh(self):
        try:
            self._all = self.employee_repo.get_all(limit=1000000)
        except Exception as e:
            log_error("emissao-lote-refresh", e)
            self._all = []
        self._apply_filters()

    def _on_nr(self, nr_code: str):
        self._nr_code = nr_code or None
        self._template = self._templates.get(nr_code) if nr_code else None
        if self._template:
            self.lbl_nr_info.configure(
                text=f"Carga mínima: {self._template.carga_horaria_minima}h  |  "
                     f"Validade: {self._template.validade_meses} meses")

    def _elegivel(self, emp: Employee) -> bool:
        return bool(emp.cpf and emp.cpf.strip())

    def _apply_filters(self):
        query = search_query(self._search_entry, self._search_var).strip()
        q = normalize_text(query)
        if q:
            self._filtered = [
                e for e in self._all
                if q in normalize_text(e.nome) or q in (e.cpf or "")
            ]
        else:
            self._filtered = list(self._all)
        self.pagination.reset()
        self.pagination.set_total(len(self._filtered))
        self._render_list()

    def _limpar(self):
        self._search_var.set("")
        self._search_entry._activate_placeholder()
        self._apply_filters()

    def _limpar_selecao(self):
        self._selected.clear()
        self._atualizar_contagem()
        self._render_list()

    def _change_per_page(self, valor: str):
        try:
            self.pagination.items_per_page = int(valor)
        except ValueError:
            self.pagination.items_per_page = 10
        self.pagination.reset()
        self._render_list()

    def _atualizar_contagem(self):
        self.lbl_selecionados.configure(text=f"Selecionados: {len(self._selected)}")

    # ── Lista ─────────────────────────────────────────────────
    def _render_list(self):
        fonts = self.fonts
        self.list_frame.clear()
        body = self.list_frame.body
        body.grid_columnconfigure(1, weight=1)

        head = ctk.CTkFrame(body, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(10, 2))
        for col, (txt, w) in enumerate([("", 60), ("Funcionário", 0), ("CPF", 150),
                                        ("Função", 180), ("Emitir", 70)]):
            head.grid_columnconfigure(col, weight=(1 if col == 1 else 0), minsize=w or 0)
            ctk.CTkLabel(head, text=txt, font=fonts["small_bold"],
                         text_color=COLORS["muted"], anchor="w").grid(row=0, column=col, sticky="w")

        start = self.pagination.offset
        page = self._filtered[start:start + self.pagination.items_per_page]

        if not page:
            ctk.CTkLabel(body, text="Nenhum funcionário encontrado.",
                         font=fonts["body"], text_color=COLORS["muted"]
                         ).pack(anchor="w", padx=14, pady=14)
            return

        for idx, emp in enumerate(page):
            row = ctk.CTkFrame(body, fg_color="transparent", height=44)
            row.pack(fill="x", padx=14)
            for col, w in [(0, 60), (2, 150), (3, 180), (4, 70)]:
                row.grid_columnconfigure(col, weight=0, minsize=w)
            row.grid_columnconfigure(1, weight=1)

            # thumb
            img = self._thumb(emp)
            if img:
                ctk.CTkLabel(row, image=img, width=28, text="").grid(row=0, column=0, rowspan=2, padx=(0, 8))
                row._norma_img = img  # mantem referencia
            else:
                ctk.CTkLabel(row, text="", width=28).grid(row=0, column=0, rowspan=2)

            elegivel = self._elegivel(emp)
            nome_color = COLORS["text"] if elegivel else COLORS["muted"]
            ctk.CTkLabel(row, text=emp.nome, font=fonts["body_bold"],
                         text_color=nome_color, anchor="w").grid(row=0, column=1, rowspan=2, sticky="ew")

            ctk.CTkLabel(row, text=emp.cpf or "—", font=fonts["small"],
                         text_color=COLORS["text"] if elegivel else COLORS["error"],
                         anchor="w").grid(row=0, column=2, rowspan=2, sticky="w")
            if elegivel:
                ctk.CTkLabel(row, text=emp.funcao or "—", font=fonts["small"],
                             text_color=COLORS["muted"], anchor="w").grid(
                    row=0, column=3, rowspan=2, sticky="w")
            else:
                ctk.CTkLabel(row, text="sem CPF", font=fonts["small_bold"],
                             text_color=COLORS["error"], anchor="w").grid(
                    row=0, column=3, rowspan=2, sticky="w")

            var = ctk.BooleanVar(value=emp.id in self._selected and elegivel)
            cb = ctk.CTkCheckBox(row, text="", variable=var, width=26,
                                 command=lambda e=emp, v=var: self._toggle(e, v))
            if not elegivel:
                cb.configure(state="disabled")
            cb.grid(row=0, column=4, rowspan=2, sticky="e")

            sep = ctk.CTkFrame(body, fg_color=COLORS["border"], height=1)
            sep.pack(fill="x", padx=14, pady=(0, 2))

        self._atualizar_contagem()

    def _thumb(self, emp: Employee):
        if not emp.foto:
            return None
        try:
            from src.utils.photo_utils import bytes_to_pil_image
            pil = bytes_to_pil_image(emp.foto)
            if pil is None:
                return None
            pil = pil.copy()
            pil.thumbnail((28, 36), Image.LANCZOS)
            return ctk.CTkImage(light_image=pil, dark_image=pil, size=(28, 36))
        except Exception:
            return None

    def _toggle(self, emp: Employee, var):
        if var.get():
            self._selected.add(emp.id)
        else:
            self._selected.discard(emp.id)
        self._atualizar_contagem()

    # ── Revisao / emissao ─────────────────────────────────────
    def _selecionados(self) -> list:
        by_id = {e.id: e for e in self._all}
        return [by_id[i] for i in sorted(
            (i for i in self._selected if i in by_id),
            key=lambda i: by_id[i].nome.lower())]

    def _revisar(self):
        from tkinter import messagebox
        if not self._nr_code or not self._template:
            messagebox.showwarning("NR", "Selecione o NR do lote.")
            return
        selecionados = self._selecionados()
        if not selecionados:
            messagebox.showwarning("Seleção", "Selecione ao menos um funcionário.")
            return
        self._dialog_revisao(selecionados)

    def _dialog_revisao(self, selecionados):
        from tkinter import messagebox
        fonts = self.fonts
        t = self._template

        dlg = ctk.CTkToplevel(self)
        dlg.title("Revisar e emitir")
        dlg.transient(self)
        fit_dialog(dlg, 560, 430)
        open_modal(dlg)

        rodape = ctk.CTkFrame(dlg, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=16, pady=(4, 14))

        # globais
        glob = ctk.CTkFrame(dlg, fg_color="transparent")
        glob.pack(fill="x", padx=16, pady=(10, 2))
        glob.grid_columnconfigure(1, weight=1)
        glob.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(glob, text=f"{self._nr_code} — {len(selecionados)} funcionário(s)",
                     font=fonts["heading"], text_color=COLORS["primary"]
                     ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        def _campo(parent, r, c, titulo, default, w=120):
            ctk.CTkLabel(parent, text=titulo, font=fonts["small_bold"],
                         text_color=COLORS["muted"], anchor="w").grid(row=r, column=c, sticky="w")
            var = ctk.StringVar(value=str(default))
            e = ctk.CTkEntry(parent, textvariable=var, width=w, font=fonts["body"], height=30)
            e.grid(row=r, column=c + 1, sticky="ew", pady=(0, 4))
            return var

        data_var = _campo(glob, 1, 0, "Data (dd/mm/aaaa)", date.today().strftime("%d/%m/%Y"), 120)
        carga_var = _campo(glob, 1, 2, "Carga (h)", t.carga_horaria_minima, 80)
        val_var = _campo(glob, 2, 0, "Validade (meses)", t.validade_meses, 80)
        ctk.CTkLabel(glob, text="Descrição:", font=fonts["small_bold"],
                     text_color=COLORS["muted"], anchor="w").grid(row=3, column=0, sticky="w")
        desc_var = ctk.StringVar(value=t.descricao_padrao)
        ctk.CTkEntry(glob, textvariable=desc_var, font=fonts["body"], height=30
                     ).grid(row=3, column=1, columnspan=3, sticky="ew", pady=(0, 4))

        # campos extras do template
        extras_vars = {}
        linha = 4
        for f in (t.campos_extra or []):
            rotulo = f.label + (" *" if f.obrigatorio else "")
            ctk.CTkLabel(glob, text=rotulo, font=fonts["small_bold"],
                         text_color=COLORS["muted"], anchor="w").grid(row=linha, column=0, sticky="w")
            var = ctk.StringVar(value=(f.opcoes[0] if f.tipo == "select" and f.opcoes else ""))
            if f.tipo == "select" and f.opcoes:
                ctk.CTkOptionMenu(glob, values=list(f.opcoes), variable=var,
                                  height=28, font=fonts["body"]
                                  ).grid(row=linha, column=1, columnspan=3, sticky="w", pady=(0, 4))
            else:
                ctk.CTkEntry(glob, textvariable=var, font=fonts["body"], height=30,
                             placeholder_text=f.placeholder
                             ).grid(row=linha, column=1, columnspan=3, sticky="ew", pady=(0, 4))
            extras_vars[f.id] = (f, var)
            linha += 1

        # individuais
        ctk.CTkLabel(dlg, text="Individual (opcional — vazio usa o valor de cima):",
                     font=fonts["small_bold"], text_color=COLORS["muted"], anchor="w"
                     ).pack(fill="x", padx=16, pady=(6, 2))
        scroll = ctk.CTkScrollableFrame(dlg, fg_color="transparent", height=110)
        scroll.pack(fill="both", expand=True, padx=16)
        ind_vars = {}
        for emp in selecionados:
            r = ctk.CTkFrame(scroll, fg_color="transparent")
            r.pack(fill="x", pady=1)
            ctk.CTkLabel(r, text=emp.nome, font=fonts["body_bold"], anchor="w", width=170
                         ).pack(side="left")
            dv = ctk.StringVar()
            de = ctk.CTkEntry(r, textvariable=dv, width=95, height=26, font=fonts["small"],
                              placeholder_text="data")
            de.pack(side="left", padx=2)
            cv = ctk.StringVar()
            ctk.CTkEntry(r, textvariable=cv, width=60, height=26, font=fonts["small"],
                         placeholder_text="carga").pack(side="left", padx=2)
            vv = ctk.StringVar()
            ctk.CTkEntry(r, textvariable=vv, width=60, height=26, font=fonts["small"],
                         placeholder_text="validade").pack(side="left", padx=2)
            ind_vars[emp.id] = (dv, cv, vv)

        def _coletar():
            data = _validar_data_br(data_var.get())
            if not data:
                messagebox.showwarning("Data", "Data inválida (use dd/mm/aaaa).", parent=dlg)
                return None
            try:
                carga = int(carga_var.get())
            except ValueError:
                messagebox.showwarning("Carga", "Carga horária inválida.", parent=dlg)
                return None
            if carga < t.carga_horaria_minima:
                messagebox.showwarning(
                    "Carga", f"Carga mínima para {self._nr_code} é {t.carga_horaria_minima}h.", parent=dlg)
                return None
            try:
                validade = int(val_var.get())
                if not (1 <= validade <= 120):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Validade", "Validade deve ser de 1 a 120 meses.", parent=dlg)
                return None
            descricao = desc_var.get().strip()
            if not descricao:
                messagebox.showwarning("Descrição", "Informe a descrição do treinamento.", parent=dlg)
                return None
            campos = {}
            for fid, (f, var) in extras_vars.items():
                valor = var.get().strip()
                if f.obrigatorio and not valor:
                    messagebox.showwarning("Campo obrigatório", f"Preencha: {f.label}", parent=dlg)
                    return None
                campos[fid] = valor

            itens = []
            for emp in selecionados:
                dv, cv, vv = ind_vars.get(emp.id, (None, None, None))
                e_data = _validar_data_br(dv.get()) if dv and dv.get().strip() else data
                if dv and dv.get().strip() and e_data is None:
                    messagebox.showwarning("Data", f"Data inválida para {emp.nome}.", parent=dlg)
                    return None
                if cv and cv.get().strip():
                    try:
                        e_carga = int(cv.get())
                        if e_carga < t.carga_horaria_minima:
                            raise ValueError
                    except ValueError:
                        messagebox.showwarning(
                            "Carga", f"Carga inválida para {emp.nome} (mínimo {t.carga_horaria_minima}h).", parent=dlg)
                        return None
                else:
                    e_carga = carga
                if vv and vv.get().strip():
                    try:
                        e_val = int(vv.get())
                        if not (1 <= e_val <= 120):
                            raise ValueError
                    except ValueError:
                        messagebox.showwarning("Validade", f"Validade inválida para {emp.nome}.", parent=dlg)
                        return None
                else:
                    e_val = validade
                itens.append((emp, e_data, e_carga, e_val))
            return itens, descricao, campos

        def _preview():
            coletado = _coletar()
            if not coletado:
                return
            itens, descricao, campos = coletado
            self._abrir_preview(itens[0][0], itens[0][1], itens[0][2], descricao, campos)

        def _emitir():
            coletado = _coletar()
            if not coletado:
                return
            itens, descricao, campos = coletado
            release_modal(dlg)
            dlg.destroy()
            self._gerar(itens, descricao, campos)

        ctk.CTkButton(rodape, text="Visualizar exemplo", width=140, height=32,
                      fg_color=COLORS["accent"], command=_preview).pack(side="left")
        ctk.CTkButton(rodape, text="Cancelar", width=90, height=32, fg_color="transparent",
                      border_width=1, border_color=COLORS["border"], text_color=COLORS["text"],
                      hover_color=COLORS["surface"],
                      command=lambda: (release_modal(dlg), dlg.destroy())).pack(side="right", padx=4)
        ctk.CTkButton(rodape, text=f"Emitir {len(selecionados)}", width=110, height=32,
                      fg_color=COLORS["success"], hover_color="#256B28",
                      command=_emitir).pack(side="right")

    # ── Preview ───────────────────────────────────────────────
    def _abrir_preview(self, emp, data, carga, descricao, campos):
        from src.ui.components.pdf_preview import PDFPreview
        try:
            preview_dir = get_data_dir() / "_previews"
            preview_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = preview_dir / f"lote_preview_{emp.nome.replace(' ', '_')}.pdf"
            self.certificate_service.generate_preview_pdf(
                nr_code=self._nr_code, employee=emp, data_treinamento=data,
                carga_horaria=carga, descricao_treinamento=descricao,
                campos_extra=campos, output_path=pdf_path)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Preview", f"Erro ao gerar preview: {e}")
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("Preview do certificado")
        dlg.transient(self)
        fit_dialog(dlg, 760, 560)
        open_modal(dlg)

        rodape = ctk.CTkFrame(dlg, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(rodape, text="Fechar", width=90,
                      command=lambda: (release_modal(dlg), dlg.destroy())).pack(side="right")

        preview = PDFPreview(dlg)
        preview.show_pdf_image(str(pdf_path))
        preview.pack(fill="both", expand=True, padx=12, pady=(12, 8))

    # ── Geracao ───────────────────────────────────────────────
    def _gerar(self, itens, descricao, campos):
        self._gerando = True
        self.btn_gerar.configure(state="disabled", text="Gerando...")
        total = len(itens)
        resultado = {"gerados": [], "erros": []}

        def trabalho():
            for i, (emp, data, carga, validade) in enumerate(itens, 1):
                self.after(0, lambda e=emp, i=i: self.lbl_selecionados.configure(
                    text=f"Gerando {i}/{total} — {e.nome}..."))
                try:
                    path = self.certificate_service.generate_certificate(
                        nr_code=self._nr_code, employee=emp, data_treinamento=data,
                        carga_horaria=carga, descricao_treinamento=descricao,
                        campos_extra=campos, validade_meses=validade)
                    resultado["gerados"].append((emp.nome, str(path)))
                except Exception as e:
                    log_error("emissao-lote-gerar", e)
                    resultado["erros"].append(f"{emp.nome}: {e}")

            def fim():
                self._gerando = False
                self.btn_gerar.configure(state="normal", text="Revisar e emitir")
                self._selected.clear()
                self.refresh()
                self._dialog_resultado(resultado)
            self.after(0, fim)

        threading.Thread(target=trabalho, daemon=True).start()

    def _dialog_resultado(self, resultado):
        from tkinter import messagebox
        fonts = self.fonts
        dlg = ctk.CTkToplevel(self)
        dlg.title("Emissão em lote")
        dlg.transient(self)
        fit_dialog(dlg, 420, 240)
        open_modal(dlg)

        n_ger = len(resultado["gerados"])
        n_err = len(resultado["erros"])
        texto = f"{n_ger} certificado(s) gerado(s)."
        if n_err:
            texto += f"\n{n_err} erro(s):"
            texto += "\n".join("• " + e for e in resultado["erros"][:10])
        ctk.CTkLabel(dlg, text=texto, font=fonts["body"], justify="left",
                     wraplength=380, anchor="w").pack(anchor="w", padx=20, pady=(18, 8))

        rodape = ctk.CTkFrame(dlg, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=20, pady=(4, 14))
        if resultado["gerados"]:
            def _abrir_pasta():
                primeiro = resultado["gerados"][0][1]
                try:
                    os.startfile(os.path.dirname(primeiro))
                except Exception as e:
                    log_error("emissao-lote-abrir-pasta", e)
            ctk.CTkButton(rodape, text="Abrir pasta", width=110,
                          command=_abrir_pasta).pack(side="left")
        ctk.CTkButton(rodape, text="Fechar", width=90,
                      command=lambda: (release_modal(dlg), dlg.destroy())).pack(side="right")
