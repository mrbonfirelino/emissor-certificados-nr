import os
import sqlite3
from datetime import date
from types import SimpleNamespace
from tkinter import messagebox, filedialog

import customtkinter as ctk

from src.ui.styles import COLORS, get_fonts
from src.core.aso_repo import AsoRepository, ASO_TIPOS
from src.ui.components.pagination import PaginationBar
from src.ui.components.scroll_frame import ScrollListFrame


class AsoPage(ctk.CTkFrame):
    """Gestao de ASOs (Atestado de Saude Ocupacional) — roadmap 2.16."""

    def __init__(self, master, aso_repo: AsoRepository, employee_repo, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.aso_repo = aso_repo
        self.employee_repo = employee_repo

        self._build_ui()
        self._refresh_list()

    # ── UI ─────────────────────────────────────────────────────

    def _build_ui(self):
        fonts = get_fonts()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_propagate(False)

        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        self._header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self._header, text="ASOs — Atestado de Saude Ocupacional",
            font=fonts["title"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w")

        self.lbl_count = ctk.CTkLabel(
            self._header, text="Total: 0",
            font=fonts["body"], text_color=COLORS["text_secondary"]
        )
        self.lbl_count.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            self._header, text="+ Novo ASO", width=110, height=36,
            font=fonts["body_bold"], fg_color=COLORS["success"], hover_color="#256B28",
            command=self._novo_aso
        ).grid(row=0, column=2, sticky="e", padx=(10, 0))

        filter_frame = ctk.CTkFrame(self._header, fg_color="transparent")
        filter_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        filter_frame.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            filter_frame, textvariable=self.search_var,
            font=fonts["body"], height=36, corner_radius=6,
            placeholder_text="Buscar por funcionario, CPF, numero ou tipo..."
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda *args: self._on_search())

        ctk.CTkButton(
            filter_frame, text="Buscar", width=80, height=36,
            font=fonts["body_bold"], fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"], command=self._on_search
        ).grid(row=0, column=1, sticky="e", padx=(0, 8))

        ctk.CTkButton(
            filter_frame, text="Limpar", width=80, height=36,
            font=fonts["body"], fg_color=COLORS["muted"],
            hover_color=COLORS["text_secondary"],
            command=lambda: (self.search_var.set(""), self._on_search())
        ).grid(row=0, column=2, sticky="e")

        self.list_frame = ScrollListFrame(self, fg_color=COLORS["surface"], corner_radius=12, height=200)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 5))
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.pagination = PaginationBar(self, on_page_change=self._refresh_list)
        self.pagination.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 5))

    # ── Listagem ───────────────────────────────────────────────

    def _on_search(self):
        self.pagination.reset()
        self._refresh_list()

    def _refresh_list(self):
        fonts = get_fonts()
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        query = self.search_var.get().strip()
        if query:
            total = self.aso_repo.count_search(query)
            asos = self.aso_repo.search(query, limit=PaginationBar.ITEMS_PER_PAGE, offset=self.pagination.offset)
        else:
            total = self.aso_repo.count_all()
            asos = self.aso_repo.get_all(limit=PaginationBar.ITEMS_PER_PAGE, offset=self.pagination.offset)

        self.pagination.set_total(total)
        self.lbl_count.configure(text=f"Total: {total}")

        if not asos:
            ctk.CTkLabel(
                self.list_frame,
                text="Nenhum ASO registrado" if not query else "Nenhum resultado encontrado",
                font=fonts["body"], text_color=COLORS["muted"]
            ).grid(row=0, column=0, pady=40, padx=20)
            return

        self._create_table_header()
        for i, aso in enumerate(asos):
            self._create_row(aso, i + 1, i % 2 == 1)

    def _create_table_header(self):
        fonts = get_fonts()
        header = ctk.CTkFrame(self.list_frame, fg_color=COLORS["primary"], corner_radius=6, height=36)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        header.grid_propagate(False)
        for col, peso in enumerate([2, 3, 2, 2, 2, 1, 1, 2]):
            header.grid_columnconfigure(col, weight=peso)

        for text, col in [("Numero", 0), ("Funcionario", 1), ("Tipo", 2),
                          ("Exame", 3), ("Valido Ate", 4), ("Status", 5), ("Anexado", 6), ("Acoes", 7)]:
            ctk.CTkLabel(
                header, text=text, font=fonts["small_bold"], text_color=COLORS["surface"],
                anchor="center" if col < 7 else "e"
            ).grid(row=0, column=col, sticky="ew" if col < 7 else "e", padx=12, pady=6)

    def _status(self, aso: dict) -> str:
        # calcula status a partir da validade do exame mais recente listado
        try:
            dias = aso.get("dias_para_vencer")
            if dias is None:
                return ""
            if dias < 0:
                return "VENCIDO"
            return f"{dias}d"
        except Exception:
            return ""

    def _create_row(self, aso: dict, row_idx: int, alternate: bool):
        fonts = get_fonts()
        bg = COLORS["background"] if alternate else "transparent"
        row = ctk.CTkFrame(self.list_frame, fg_color=bg, corner_radius=0, height=36)
        row.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=0)
        row.grid_propagate(False)
        for col, peso in enumerate([2, 3, 2, 2, 2, 1, 1, 2]):
            row.grid_columnconfigure(col, weight=peso)

        ctk.CTkLabel(row, text=aso["aso_number"], font=fonts["small_bold"],
                     text_color=COLORS["primary"], anchor="center"
                     ).grid(row=0, column=0, sticky="ew", padx=12, pady=6)

        nome = aso.get("funcionario_nome") or "-"
        cpf = aso.get("funcionario_cpf")
        label = f"{nome} ({cpf})" if cpf else nome
        ctk.CTkLabel(row, text=label, font=fonts["small"],
                     text_color=COLORS["text"], anchor="center"
                     ).grid(row=0, column=1, sticky="ew", padx=12, pady=6)

        ctk.CTkLabel(row, text=aso["tipo_aso"], font=fonts["small"],
                     text_color=COLORS["text"], anchor="center"
                     ).grid(row=0, column=2, sticky="ew", padx=12, pady=6)

        ctk.CTkLabel(row, text=self._br(aso["data_exame"]), font=fonts["small"],
                     text_color=COLORS["text_secondary"], anchor="center"
                     ).grid(row=0, column=3, sticky="ew", padx=12, pady=6)

        # valido ate = exame + validade_meses
        valido = "-"
        try:
            d = date.fromisoformat(aso["data_exame"])
            from dateutil.relativedelta import relativedelta
            valido = (d + relativedelta(months=aso["validade_meses"] or 12)).strftime("%d/%m/%Y")
        except Exception:
            pass
        ctk.CTkLabel(row, text=valido, font=fonts["small"],
                     text_color=COLORS["text_secondary"], anchor="center"
                     ).grid(row=0, column=4, sticky="ew", padx=12, pady=6)

        dias = self._dias(aso)
        if dias is not None and dias < 0:
            cor, txt = COLORS["error"], "VENCIDO"
        elif dias is not None and dias <= 15:
            cor, txt = COLORS["warning"], f"{dias}d"
        else:
            cor, txt = COLORS["success"], "OK" if dias is not None else ""
        ctk.CTkLabel(row, text=txt, font=fonts["small_bold"], text_color=cor,
                     anchor="center").grid(row=0, column=5, sticky="ew", padx=12, pady=6)

        if aso.get("has_doc"):
            badge = ctk.CTkLabel(row, text="ANEXADO", font=fonts["tiny"],
                                 text_color=COLORS["success"], fg_color="#E6F2E6", corner_radius=4)
            badge.grid(row=0, column=6, padx=8, pady=4)
        else:
            ctk.CTkLabel(row, text="—", font=fonts["small"],
                         text_color=COLORS["muted"], anchor="center"
                         ).grid(row=0, column=6, sticky="ew", padx=12, pady=6)

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=7, sticky="e", padx=8, pady=4)

        ctk.CTkButton(btn_frame, text="PDF", width=40, height=26, font=fonts["small"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                      command=lambda a=aso: self._open_pdf(a)).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Anexar", width=52, height=26, font=fonts["small"],
                      fg_color=COLORS["warning"], hover_color="#BF5300",
                      command=lambda a=aso: self._attach(a)).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Digitalizar", width=72, height=26, font=fonts["small"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                      command=lambda a=aso: self._digitalizar(a)).pack(side="left", padx=2)
        btn_baixar = ctk.CTkButton(btn_frame, text="Baixar", width=52, height=26, font=fonts["small"],
                                   fg_color=COLORS["success"], hover_color="#256B28",
                                   command=lambda a=aso: self._download(a))
        if not aso.get("has_doc"):
            btn_baixar.configure(state="disabled")
        btn_baixar.pack(side="left", padx=2)

        sep = ctk.CTkFrame(self.list_frame, fg_color=COLORS["border"], height=1)
        sep.grid(row=row_idx + 1, column=0, sticky="ew", padx=12, pady=0)

    @staticmethod
    def _br(iso: str) -> str:
        return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}" if iso and len(iso) == 10 and iso[4] == "-" else (iso or "-")

    @staticmethod
    def _dias(aso: dict):
        try:
            d = date.fromisoformat(aso["data_exame"])
            from dateutil.relativedelta import relativedelta
            valido = d + relativedelta(months=aso["validade_meses"] or 12)
            return (valido - date.today()).days
        except Exception:
            return None

    # ── Novo ASO ───────────────────────────────────────────────

    def _novo_aso(self):
        fonts = get_fonts()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Novo ASO")
        dialog.geometry("520x430")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(dialog, text="Registrar Novo ASO", font=fonts["heading"],
                     text_color=COLORS["primary"]).grid(row=0, column=0, pady=(16, 4))
        ctk.CTkLabel(dialog, text="Gera o PDF modelo com espaco para anexar o ASO real.",
                     font=fonts["small"], text_color=COLORS["text_secondary"]).grid(row=1, column=0, pady=(0, 10))

        selecionado = {"emp": None}

        from src.ui.components.employee_autocomplete import EmployeeAutocomplete
        ctk.CTkLabel(dialog, text="Funcionario *", font=fonts["body_bold"],
                     text_color=COLORS["text"]).grid(row=2, column=0, sticky="w", padx=24, pady=(4, 2))
        autocomplete = EmployeeAutocomplete(
            dialog, self.employee_repo,
            on_select=lambda emp: selecionado.update(emp=emp),
            placeholder="Digite o nome do funcionario..."
        )
        autocomplete.grid(row=3, column=0, sticky="ew", padx=24)

        ctk.CTkLabel(dialog, text="Tipo de ASO *", font=fonts["body_bold"],
                     text_color=COLORS["text"]).grid(row=4, column=0, sticky="w", padx=24, pady=(10, 2))
        tipo_var = ctk.StringVar(value=ASO_TIPOS[0])
        ctk.CTkOptionMenu(dialog, variable=tipo_var, values=ASO_TIPOS, font=fonts["body"], height=34,
                          fg_color=COLORS["surface"], text_color=COLORS["text"],
                          button_color=COLORS["secondary"], button_hover_color=COLORS["primary"]
                          ).grid(row=5, column=0, sticky="ew", padx=24)

        hoje = date.today()
        ctk.CTkLabel(dialog, text="Data do Exame (dd/mm/aaaa) *", font=fonts["body_bold"],
                     text_color=COLORS["text"]).grid(row=6, column=0, sticky="w", padx=24, pady=(10, 2))
        data_var = ctk.StringVar(value=hoje.strftime("%d/%m/%Y"))
        ctk.CTkEntry(dialog, textvariable=data_var, font=fonts["body"], height=34,
                     corner_radius=6).grid(row=7, column=0, sticky="ew", padx=24)

        ctk.CTkLabel(dialog, text="Validade (meses) *", font=fonts["body_bold"],
                     text_color=COLORS["text"]).grid(row=8, column=0, sticky="w", padx=24, pady=(10, 2))
        val_var = ctk.StringVar(value="12")
        ctk.CTkEntry(dialog, textvariable=val_var, font=fonts["body"], height=34,
                     corner_radius=6).grid(row=9, column=0, sticky="ew", padx=24)

        def gerar():
            emp = selecionado.get("emp")
            if not emp:
                messagebox.showerror("Erro", "Selecione um funcionario.", parent=dialog)
                return
            try:
                dia, mes, ano = data_var.get().strip().split("/")
                d_exame = date(int(ano), int(mes), int(dia))
            except ValueError:
                messagebox.showerror("Erro", "Data do exame invalida (use dd/mm/aaaa).", parent=dialog)
                return
            try:
                meses = int(val_var.get().strip())
                if meses < 1 or meses > 120:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erro", "Validade deve ser um numero de meses entre 1 e 120.", parent=dialog)
                return

            from src.core.aso_pdf_generator import generate_aso_pdf
            from src.utils.paths import get_data_dir
            from src.utils.folder_utils import employee_folder_name
            try:
                aso_number = self.aso_repo.next_aso_number()
                pasta = employee_folder_name(emp, self.employee_repo.get_all(limit=1000000))
                destino = get_data_dir() / "asos" / pasta
                destino.mkdir(parents=True, exist_ok=True)
                pdf_path = str(destino / f"{aso_number}.pdf")
                generate_aso_pdf(pdf_path, aso_number, emp, tipo_var.get(),
                                 d_exame.isoformat(), meses)
                aso_id = self.aso_repo.save(aso_number, emp.id, tipo_var.get(),
                                            d_exame.isoformat(), meses, pdf_path)
            except Exception as e:
                from src.utils.error_log import log_error
                log_error("novo-aso", e)
                messagebox.showerror("Erro", f"Erro ao gerar ASO: {e}", parent=dialog)
                return

            try:
                from src.core.network_sync import run_async, sync_aso
                run_async(sync_aso, self.aso_repo.get_by_id(aso_id), emp)
            except Exception:
                pass

            messagebox.showinfo("Sucesso", f"ASO {aso_number} gerado em:\n{pdf_path}", parent=dialog)
            dialog.destroy()
            self._refresh_list()

        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.grid(row=10, column=0, sticky="ew", padx=24, pady=(16, 16))
        btns.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(btns, text="Cancelar", height=36, font=fonts["body_bold"],
                      fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
                      command=dialog.destroy).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(btns, text="Gerar ASO", height=36, font=fonts["body_bold"],
                      fg_color=COLORS["success"], hover_color="#256B28",
                      command=gerar).grid(row=0, column=1, sticky="e")

    # ── Acoes por linha ────────────────────────────────────────

    def _open_pdf(self, aso: dict):
        if aso.get("pdf_path") and os.path.exists(aso["pdf_path"]):
            try:
                os.startfile(aso["pdf_path"])
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao abrir PDF: {e}", parent=self)
        else:
            messagebox.showwarning("Aviso", "Arquivo PDF nao encontrado.", parent=self)

    def _attach(self, aso: dict):
        if aso.get("has_doc"):
            resp = messagebox.askyesnocancel(
                "Documento do ASO",
                "Este ASO ja possui documento anexado.\n\n"
                "Sim = substituir por novo arquivo\n"
                "Nao = remover o documento atual\n"
                "Cancelar = fechar",
                parent=self
            )
            if resp is None:
                return
            if resp is False:
                if self.aso_repo.remove_doc(aso["id"]):
                    messagebox.showinfo("Sucesso", "Documento removido.", parent=self)
                    self._refresh_list()
                return

        path = filedialog.askopenfilename(
            title=f"Anexar ASO ({aso['aso_number']})",
            filetypes=[("Documentos", "*.pdf *.jpg *.jpeg *.png"), ("Todos", "*.*")],
            parent=self
        )
        if not path:
            return
        try:
            ext = path.rsplit(".", 1)[-1].lower()
            with open(path, "rb") as f:
                data = f.read()
            self.aso_repo.attach_doc(aso["id"], data, ext)
            self._espelhar_rede(aso)
            messagebox.showinfo("Sucesso", "Documento anexado ao ASO.", parent=self)
            self._refresh_list()
        except ValueError as e:
            messagebox.showerror("Erro", str(e), parent=self)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("aso-anexar", e)
            messagebox.showerror("Erro", f"Erro ao anexar: {e}", parent=self)

    def _digitalizar(self, aso: dict):
        from src.ui.components.scan_dialog import ScanDialog
        shim = SimpleNamespace(cert_number=aso["aso_number"],
                               funcionario_nome=aso.get("funcionario_nome") or "")
        dlg = ScanDialog(self, shim)
        self.wait_window(dlg)
        if not dlg.resultado:
            return
        data, tipo = dlg.resultado
        try:
            self.aso_repo.attach_doc(aso["id"], data, tipo)
            self._espelhar_rede(aso)
            messagebox.showinfo("Sucesso", "Digitalizacao anexada ao ASO.", parent=self)
            self._refresh_list()
        except ValueError as e:
            messagebox.showerror("Erro", str(e), parent=self)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("aso-digitalizar", e)
            messagebox.showerror("Erro", f"Erro ao anexar digitalizacao: {e}", parent=self)

    def _download(self, aso: dict):
        result = self.aso_repo.get_doc(aso["id"])
        if not result:
            messagebox.showwarning("Aviso", "Nenhum documento anexado.", parent=self)
            return
        data, tipo = result
        ext = {"pdf": ".pdf", "jpg": ".jpg", "jpeg": ".jpg", "png": ".png"}.get(tipo, ".pdf")
        path = filedialog.asksaveasfilename(
            title="Salvar documento do ASO", defaultextension=ext,
            initialfile=f"{aso['aso_number']}_documento{ext}", parent=self
        )
        if not path:
            return
        try:
            with open(path, "wb") as f:
                f.write(data)
            if messagebox.askyesno("Sucesso", f"Documento salvo em:\n{path}\n\nAbrir agora?", parent=self):
                try:
                    os.startfile(path)
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}", parent=self)

    def _espelhar_rede(self, aso: dict):
        try:
            from src.core.network_sync import run_async, sync_aso_doc
            run_async(sync_aso_doc, aso["id"])
        except Exception:
            pass

    # ── API publica ────────────────────────────────────────────

    def refresh(self):
        self.pagination.reset()
        self._refresh_list()

    def preload_employee_by_id(self, employee_id: int):
        """Abre a busca pre-preenchida com o funcionario (acao 'Emitir' da tela de Vencimentos)."""
        emp = self.employee_repo.get_by_id(employee_id)
        if not emp:
            return
        self.search_var.set(emp.nome)
        self.pagination.reset()
        self._refresh_list()

    def search_for(self, term: str):
        self.search_var.set(term)
        self.pagination.reset()
        self._refresh_list()
