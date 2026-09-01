import os
import sys
import subprocess
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox, filedialog

from src.ui.styles import COLORS, get_fonts
from src.core.employee_repo import EmployeeRepository
from src.core.blocking_card_service import (
    load_card_templates,
    compute_grid,
    generate_cards,
)
from src.ui.components.pagination import PaginationBar
from src.ui.components.generation_options_dialog import EmissionReviewDialog

PER_PAGE_OPTIONS = [10, 25, 40]


class BlockingCardsPage(ctk.CTkFrame):

    def __init__(self, master, employee_repo: EmployeeRepository, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.employee_repo = employee_repo
        self._selected = set()          # ids selecionados (persiste entre paginas)
        self._page_employees = []       # funcionarios da pagina atual
        self._per_page = 10
        self._total = 0
        self._last_setor = ""           # ultimo setor usado em lote PPTX (conveniencia)
        self._build_ui()
        self._refresh_list()

    # ── Template corrente ────────────────────────────────────

    def _current_template(self) -> Optional[dict]:
        return self._templates.get(self._template_var.get())

    def _is_pptx(self) -> bool:
        tpl = self._current_template()
        return bool(tpl and tpl.get("template_type") == "pptx")

    def _requirements(self):
        """(exige_telefone, exige_foto) conforme campos usados pelo template atual."""
        tpl = self._current_template()
        if tpl and tpl.get("template_type") == "pptx":
            used = set(tpl.get("used_fields") or [])
            return ("TELEFONE" in used, bool(tpl.get("uses_photo")))
        return (True, True)

    def _missing_fields(self, emp):
        """Campos obrigatorios ausentes para o template atual."""
        needs_tel, needs_photo = self._requirements()
        faltas = []
        if needs_tel and not emp.telefone:
            faltas.append("telefone")
        if needs_photo and not emp.foto:
            faltas.append("foto 3x4")
        return faltas

    # ── Layout ───────────────────────────────────────────────

    def _build_ui(self):
        fonts = get_fonts()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_propagate(False)

        # Row 0 — Header
        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        self._header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self._header, text="Emissao de Cartoes de Bloqueio",
            font=fonts["title"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w")

        self.lbl_count = ctk.CTkLabel(
            self._header, text="0 selecionado(s)",
            font=fonts["body"], text_color=COLORS["text_secondary"]
        )
        self.lbl_count.grid(row=0, column=1, sticky="e")

        # Row 1 — Config (template + busca ampliada + por pagina)
        cfg = ctk.CTkFrame(self._header, fg_color="transparent")
        cfg.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        cfg.grid_columnconfigure(3, weight=1)

        # Template do cartao (cliente)
        ctk.CTkLabel(cfg, text="Modelo:", font=fonts["body_bold"],
                     text_color=COLORS["text"]).grid(row=0, column=0, padx=(0, 6), sticky="w")
        self._templates = load_card_templates()
        template_names = list(self._templates.keys()) if self._templates else ["ALTEC"]
        self._template_var = ctk.StringVar(value=template_names[0])
        self._template_menu = ctk.CTkOptionMenu(
            cfg, variable=self._template_var, values=template_names,
            font=fonts["body"], height=34, width=150,
            fg_color=COLORS["surface"], text_color=COLORS["text"],
            button_color=COLORS["secondary"], button_hover_color=COLORS["primary"],
            command=lambda *_: self._update_grid_info()
        )
        self._template_menu.grid(row=0, column=1, padx=(0, 12), sticky="w")

        # info do grid (cartoes por folha)
        self._grid_info = ctk.CTkLabel(cfg, text="", font=fonts["small"], text_color=COLORS["muted"])
        self._grid_info.grid(row=0, column=2, padx=(0, 12), sticky="w")

        # busca (ampliada, expande)
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search())
        ctk.CTkEntry(
            cfg, textvariable=self._search_var, font=fonts["body"],
            height=34, corner_radius=6,
            placeholder_text="Buscar funcionario, CPF ou telefone..."
        ).grid(row=0, column=3, sticky="ew", padx=(0, 8))

        # seletor de itens por pagina (ao lado da busca)
        ctk.CTkLabel(cfg, text="Por pagina:", font=fonts["small"],
                     text_color=COLORS["muted"]).grid(row=0, column=4, padx=(4, 4), sticky="e")
        self._per_page_var = ctk.StringVar(value=str(self._per_page))
        self._per_page_menu = ctk.CTkOptionMenu(
            cfg, variable=self._per_page_var,
            values=[str(v) for v in PER_PAGE_OPTIONS],
            font=fonts["small"], height=30, width=64,
            fg_color=COLORS["surface"], text_color=COLORS["text"],
            button_color=COLORS["secondary"], button_hover_color=COLORS["primary"],
            command=lambda *_: self._change_per_page()
        )
        self._per_page_menu.grid(row=0, column=5, sticky="e")

        # Row 2 — Lista de funcionarios com checkboxes
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"], corner_radius=12, height=200)
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(8, 2))
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Row 3 — Paginacao (colada na lista)
        self.pagination = PaginationBar(self, on_page_change=self._refresh_list)
        self.pagination.grid(row=3, column=0, sticky="w", padx=20, pady=(2, 2))

        # Row 4 — Acoes (rodape)
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=20, pady=(2, 8))
        actions.grid_columnconfigure(5, weight=1)
        self._actions = actions

        ctk.CTkButton(
            actions, text="Importar Excel", font=fonts["body_bold"], height=34,
            fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
            command=self._import_excel
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            actions, text="Selecionar Todos (pagina)", font=fonts["body_bold"], height=34,
            fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
            command=self._select_page
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            actions, text="Limpar Selecao", font=fonts["body_bold"], height=34,
            fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
            command=self._clear_selection
        ).grid(row=0, column=2, padx=(0, 16))

        self._single_pdf_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            actions, text="PDF unico (varios cartoes por folha)",
            variable=self._single_pdf_var,
            font=fonts["body"], text_color=COLORS["text"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            checkbox_height=20, checkbox_width=20
        ).grid(row=0, column=3, padx=(0, 16))

        self._one_page_var = ctk.BooleanVar(value=False)
        self._one_page_cb = ctk.CTkCheckBox(
            actions, text="1 cartao por pagina",
            variable=self._one_page_var,
            font=fonts["body"], text_color=COLORS["text"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            checkbox_height=20, checkbox_width=20,
            state="disabled"
        )
        self._one_page_cb.grid(row=0, column=4, padx=(0, 16))

        self.btn_preview = ctk.CTkButton(
            actions, text="Preview", font=fonts["body_bold"], height=36,
            fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
            command=self._preview
        )
        self.btn_preview.grid(row=0, column=6, padx=(0, 8))

        self.btn_generate = ctk.CTkButton(
            actions, text="Gerar Cartoes", font=fonts["body_bold"], height=36,
            fg_color=COLORS["success"], hover_color="#256B28",
            command=self._generate
        )
        self.btn_generate.grid(row=0, column=7)

        self.after(200, lambda: self._fit_scroll_height(0))
        self._update_grid_info()

    def _update_grid_info(self):
        tpl = self._current_template()
        if not tpl:
            return
        if tpl.get("template_type") == "pptx":
            k = int(tpl.get("cards_per_slide", 1))
            s = int(tpl.get("_slides", 1))
            extra = f" x {s} folhas" if s > 1 else ""
            self._grid_info.configure(text=f"PPTX — {k} cartao(oes)/folha{extra}")
            self._one_page_cb.configure(state="normal")
        else:
            cols, rows = compute_grid(tpl)
            self._grid_info.configure(
                text=f"{tpl.get('card_width_mm', 85.6)}x{tpl.get('card_height_mm', 54)}mm — {cols*rows}/folha"
            )
            self._one_page_var.set(False)
            self._one_page_cb.configure(state="disabled")
        # requisitos mudam conforme template -> revalida a lista
        self._prune_selection()
        self._refresh_list()

    def _prune_selection(self):
        """Remove da selecao funcionarios da pagina atual que ficaram invalidos."""
        for emp in self._page_employees:
            if self._missing_fields(emp):
                self._selected.discard(emp.id)

    def _fit_scroll_height(self, _retry=0):
        self.update_idletasks()
        h = self.winfo_height()
        if h < 200:
            try:
                ph = self.master.winfo_height()
                if ph >= 200:
                    h = ph
            except Exception:
                pass
        if h < 200:
            if _retry < 5:
                self.after(300, lambda r=_retry + 1: self._fit_scroll_height(r))
            return
        header_h = self._header.winfo_reqheight()
        pag_h = self.pagination.winfo_reqheight()
        actions_h = self._actions.winfo_reqheight() if hasattr(self, "_actions") else 40
        # margens reais: pady da lista (8+2) + paginacao (2+2) + acoes (2+8) = 24
        margins = 24
        available = h - header_h - pag_h - actions_h - margins
        self.list_frame.configure(height=max(available, 150))

    # ── Paginacao ────────────────────────────────────────────

    @property
    def _offset(self) -> int:
        return (self.pagination.current_page - 1) * self._per_page

    def _change_per_page(self):
        try:
            self._per_page = int(self._per_page_var.get())
        except ValueError:
            self._per_page = 10
        self.pagination.items_per_page = self._per_page
        self.pagination.reset()
        self._refresh_list()

    def _on_search(self):
        self.pagination.reset()
        self._refresh_list()

    # ── Lista ────────────────────────────────────────────────

    def _refresh_list(self):
        fonts = get_fonts()
        for w in self.list_frame.winfo_children():
            w.destroy()

        query = self._search_var.get().strip()
        if query:
            self._total = self.employee_repo.count_search(query)
        else:
            self._total = self.employee_repo.count_all()

        self.pagination.set_total(self._total)

        if query:
            employees = self.employee_repo.search(query, limit=self._per_page + self._offset)[self._offset:]
        else:
            employees = self.employee_repo.get_all(limit=self._per_page, offset=self._offset)

        self._page_employees = employees

        if not employees:
            ctk.CTkLabel(
                self.list_frame,
                text="Nenhum funcionario encontrado",
                font=fonts["body"], text_color=COLORS["muted"]
            ).grid(row=0, column=0, pady=40, padx=20)
            self._update_count()
            return

        header = ctk.CTkFrame(self.list_frame, fg_color=COLORS["primary"], corner_radius=6, height=30)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=3)
        header.grid_columnconfigure(2, weight=2)
        header.grid_columnconfigure(3, weight=2)
        header.grid_columnconfigure(4, weight=3)
        for col, text in enumerate(["", "Nome", "Funcao", "CPF", "Telefone"]):
            ctk.CTkLabel(
                header, text=text, font=fonts["body_bold"],
                text_color="#FFFFFF", anchor="w"
            ).grid(row=0, column=col, sticky="ew", padx=8, pady=4)

        for i, emp in enumerate(employees):
            self._create_row(emp, i + 1, i % 2 == 1)

        self._update_count()

    def _create_row(self, emp, row_idx: int, alternate: bool):
        fonts = get_fonts()
        bg = COLORS["background"] if alternate else "transparent"
        row = ctk.CTkFrame(self.list_frame, fg_color=bg, corner_radius=0)
        row.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=0)
        row.grid_columnconfigure(1, weight=3)
        row.grid_columnconfigure(2, weight=2)
        row.grid_columnconfigure(3, weight=2)
        row.grid_columnconfigure(4, weight=3)

        ready = not self._missing_fields(emp)
        status_tip = "" if ready else " e ".join(self._missing_fields(emp))

        var = ctk.BooleanVar(value=(emp.id in self._selected and ready))
        cb = ctk.CTkCheckBox(
            row, text="", variable=var, width=24,
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            checkbox_height=18, checkbox_width=18,
            command=lambda e=emp, v=var: self._toggle(e, v)
        )
        if not ready:
            cb.configure(state="disabled")
        cb.grid(row=0, column=0, padx=(8, 4), pady=4)

        nome_txt = emp.nome if ready else f"{emp.nome}  (sem {status_tip})"
        ctk.CTkLabel(row, text=nome_txt, font=fonts["body"],
                     text_color=COLORS["text"] if ready else COLORS["muted"],
                     anchor="w").grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        ctk.CTkLabel(row, text=emp.funcao or "-", font=fonts["body"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=2, sticky="ew", padx=8, pady=4)
        ctk.CTkLabel(row, text=emp.cpf or "-", font=fonts["body"],
                     text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=3, sticky="ew", padx=8, pady=4)
        tel_txt = emp.telefone_formatado() if emp.telefone else "-"
        ctk.CTkLabel(row, text=tel_txt, font=fonts["body"],
                     text_color=COLORS["text_secondary"] if emp.telefone else COLORS["muted"],
                     anchor="w").grid(row=0, column=4, sticky="ew", padx=8, pady=4)

        sep = ctk.CTkFrame(self.list_frame, fg_color=COLORS["border"], height=1)
        sep.grid(row=row_idx + 1, column=0, sticky="ew", padx=12, pady=0)

    def _toggle(self, emp, var):
        if var.get():
            self._selected.add(emp.id)
        else:
            self._selected.discard(emp.id)
        self._update_count()

    def _select_page(self):
        for emp in self._page_employees:
            if not self._missing_fields(emp):
                self._selected.add(emp.id)
        self._refresh_list()

    def _clear_selection(self):
        self._selected.clear()
        self._refresh_list()

    def _update_count(self):
        ready_ids = [e.id for e in self._page_employees if e.id in self._selected and not self._missing_fields(e)]
        total_sel = len(self._selected)
        txt = f"{total_sel} selecionado(s)"
        if total_sel != len(ready_ids):
            txt += f" ({total_sel - len(ready_ids)} em outras paginas)"
        self.lbl_count.configure(text=txt)

    # ── Geracao ──────────────────────────────────────────────

    def _collect(self, action_label: str = "emitir"):
        """
        Abre a Revisao da Emissao (sempre) sobre COPIAS transitorias dos
        funcionarios — edicoes (nome/funcao/telefone/foto + setor/papel/
        matricula) valem somente para esta emissao, nada e gravado no banco.
        Retorna (valid, template, options, is_pptx, missing) ou None se abortado.
        """
        selected_ids = list(self._selected)
        selected = []
        for eid in selected_ids:
            emp = self.employee_repo.get_by_id(eid)
            if emp:
                selected.append(emp)

        if not selected:
            messagebox.showwarning("Aviso", "Selecione pelo menos um funcionario.", parent=self)
            return None

        template = self._current_template()
        if not template:
            messagebox.showerror("Erro", f"Template '{self._template_var.get()}' nao encontrado.", parent=self)
            return None

        # copias transitórias — o banco nao e afetado
        copies = [e.model_copy() for e in selected]
        dlg = EmissionReviewDialog(self, copies, template, initial_setor=self._last_setor)
        self.wait_window(dlg)
        if not dlg.selected:
            return None
        options = dlg.selected
        self._last_setor = options.get("setor", "")

        # validacao dinamica sobre as copias EDITADAS
        valid, missing = [], []
        for emp in options["employees"]:
            faltas = self._missing_fields(emp)
            if faltas:
                missing.append(f"{emp.nome}: sem {' e '.join(faltas)}")
            else:
                valid.append(emp)

        if missing:
            msg = "Cartao NAO incluido para:\n\n" + "\n".join(missing)
            if not valid:
                messagebox.showerror(
                    "Cartao de Bloqueio",
                    "Nenhum cartao pode ser gerado.\n\n" + msg,
                    parent=self
                )
                return None
            resp = messagebox.askyesno(
                "Funcionarios sem dados obrigatorios",
                msg + f"\n\nDeseja {action_label} os cartoes dos outros {len(valid)} funcionario(s)?",
                parent=self
            )
            if not resp:
                return None

        is_pptx = template.get("template_type") == "pptx"
        return valid, template, options, is_pptx, missing

    def _run_generation(self, valid, template, options, is_pptx, output_dir=None):
        """Executa generate_cards e trata erros. Retorna paths ou None."""
        self.btn_generate.configure(state="disabled", text="Gerando...")
        self.btn_preview.configure(state="disabled")
        self.update_idletasks()
        try:
            paths, _ = generate_cards(
                valid, template,
                single_pdf=self._single_pdf_var.get(),
                options=options,
                one_per_page=(is_pptx and self._one_page_var.get()),
                output_dir=output_dir,
            )
            return paths or None
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar cartoes: {e}", parent=self)
            return None
        finally:
            self.btn_generate.configure(state="normal", text="Gerar Cartoes")
            self.btn_preview.configure(state="normal")

    def _generate(self):
        ctx = self._collect("emitir")
        if not ctx:
            return
        valid, template, options, is_pptx, missing = ctx

        paths = self._run_generation(valid, template, options, is_pptx)
        if not paths:
            messagebox.showerror("Erro", "Nenhum PDF foi gerado.", parent=self)
            return

        try:
            from src.utils.notifications import notify
            notify("Cartoes de Bloqueio",
                   f"{len(valid)} cartao(oes) gerado(s) em {len(paths)} PDF(s).")
        except Exception:
            pass
        self._show_result_dialog(valid, paths, missing)

    def _show_result_dialog(self, valid, paths, missing):
        """Dialogo de sucesso com Imprimir / Abrir Pasta / Fechar."""
        fonts = get_fonts()
        resumo = (f"{len(valid)} cartao(oes) gerado(s) em {len(paths)} PDF(s).\n"
                  f"{paths[0].parent}")
        if missing:
            resumo += "\n\nPulados (dados faltando):\n" + "\n".join(missing)

        dlg = ctk.CTkToplevel(self)
        dlg.title("Cartoes Gerados")
        dlg.geometry("480x220")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 240
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 110
        dlg.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dlg, text="Sucesso!", font=fonts["heading"],
                     text_color=COLORS["success"]).pack(pady=(16, 4))
        ctk.CTkLabel(dlg, text=resumo, font=fonts["small"],
                     text_color=COLORS["text_secondary"], justify="left", wraplength=430).pack(padx=20)

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="Imprimir", width=90, height=32, font=fonts["body_bold"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                      command=lambda: self._print_pdf(paths[0])).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Abrir Pasta", width=100, height=32, font=fonts["body_bold"],
                      fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
                      command=lambda: (self._open_folder(paths[0].parent), dlg.destroy())
                      ).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Fechar", width=80, height=32, font=fonts["body_bold"],
                      fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
                      command=dlg.destroy).pack(side="left", padx=4)

    # ── Preview ──────────────────────────────────────────────

    def _preview(self):
        ctx = self._collect("prever")
        if not ctx:
            return
        valid, template, options, is_pptx, missing = ctx

        import tempfile
        from pathlib import Path

        tmp_dir = Path(tempfile.mkdtemp(prefix="preview_cartoes_"))
        while True:
            paths = self._run_generation(valid, template, options, is_pptx, output_dir=tmp_dir)
            if not paths:
                messagebox.showerror("Erro", "Nenhum PDF foi gerado para o preview.", parent=self)
                return

            action = self._show_preview_dialog(template, paths[0], len(valid))
            if action == "edit":
                # reabre a revisao com as MESMAS copias (edicoes anteriores preservadas)
                dlg = EmissionReviewDialog(self, options["employees"], template,
                                           initial_setor=options.get("setor", ""))
                self.wait_window(dlg)
                if not dlg.selected:
                    continue  # cancelou a edicao — mostra o preview atual de novo
                options = dlg.selected
                self._last_setor = options.get("setor", "")
                valid, missing = [], []
                for emp in options["employees"]:
                    faltas = self._missing_fields(emp)
                    if faltas:
                        missing.append(f"{emp.nome}: sem {' e '.join(faltas)}")
                    else:
                        valid.append(emp)
                if not valid:
                    messagebox.showerror("Cartao de Bloqueio",
                                         "Nenhum cartao valido apos a edicao.", parent=self)
                    return
                continue  # regenera o preview com os dados editados

            if action == "final":
                final_paths = self._run_generation(valid, template, options, is_pptx)
                if final_paths:
                    try:
                        from src.utils.notifications import notify
                        notify("Cartoes de Bloqueio", f"{len(valid)} cartao(oes) gerado(s).")
                    except Exception:
                        pass
                    self._show_result_dialog(valid, final_paths, missing)
            return

    def _show_preview_dialog(self, template, pdf_path, n_cards: int) -> str:
        """Dialogo de preview. Retorna 'edit' | 'final' | 'close'."""
        fonts = get_fonts()
        result = {"action": "close"}

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Preview — {template.get('card_code', '')}")
        dlg.geometry("900x780")
        dlg.transient(self)
        dlg.grab_set()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 450
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 390
        dlg.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        from src.ui.components.pdf_preview import PDFPreview
        preview = PDFPreview(dlg)
        preview.pack(fill="both", expand=True, padx=12, pady=(12, 8))
        preview.show_pdf_image(str(pdf_path))

        def set_action(a):
            result["action"] = a
            dlg.destroy()

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(btns, text=f"{n_cards} cartao(oes) — preview temporario; edicoes nao afetam o cadastro",
                     font=fonts["small"], text_color=COLORS["muted"]).pack(side="left")

        ctk.CTkButton(btns, text="Fechar", width=80, height=32, font=fonts["body_bold"],
                      fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
                      command=lambda: set_action("close")).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="Gerar PDF Definitivo", width=150, height=32, font=fonts["body_bold"],
                      fg_color=COLORS["success"], hover_color="#256B28",
                      command=lambda: set_action("final")).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="Imprimir", width=90, height=32, font=fonts["body_bold"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                      command=lambda: self._print_pdf(pdf_path)).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="Voltar e Editar", width=120, height=32, font=fonts["body_bold"],
                      fg_color=COLORS["warning"], hover_color="#BF5300",
                      command=lambda: set_action("edit")).pack(side="right", padx=4)

        self.wait_window(dlg)
        return result["action"]

    # ── Impressao / importacao ───────────────────────────────

    @staticmethod
    def _print_pdf(path):
        """Envia o PDF para a impressora padrao do Windows."""
        try:
            if sys.platform == "win32":
                os.startfile(str(path), "print")
            elif sys.platform == "darwin":
                subprocess.run(["lp", str(path)])
            else:
                subprocess.run(["lp", str(path)])
        except Exception as e:
            messagebox.showerror("Impressao", f"Erro ao imprimir: {e}")

    def _import_excel(self):
        """Importa lista de bloqueios de planilha (A=Nome, B=CPF) e marca a selecao."""
        path = filedialog.askopenfilename(
            title="Importar lista de bloqueios",
            filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")],
            parent=self
        )
        if not path:
            return
        try:
            from src.utils.blocking_importer import import_blocking_list
            encontrados, nao_encontrados = import_blocking_list(path, self.employee_repo)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao importar planilha: {e}", parent=self)
            return

        adicionados = 0
        for emp in encontrados:
            if not self._missing_fields(emp) and emp.id not in self._selected:
                self._selected.add(emp.id)
                adicionados += 1
        self._refresh_list()

        msg = (f"Planilha processada.\n\n"
               f"{len(encontrados)} funcionario(s) encontrado(s) no cadastro — "
               f"{adicionados} novo(s) na selecao.")
        if nao_encontrados:
            msg += ("\n\nNAO encontrados no cadastro:\n" + "\n".join(nao_encontrados[:15]) +
                    (f"\n... e mais {len(nao_encontrados) - 15}" if len(nao_encontrados) > 15 else ""))
        messagebox.showinfo("Importar Bloqueios", msg, parent=self)

    @staticmethod
    def _open_folder(folder):
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception:
            pass

    def refresh(self):
        self._refresh_list()
