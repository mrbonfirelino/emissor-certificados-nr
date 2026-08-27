import customtkinter as ctk
import threading
from tkinter import filedialog, messagebox
from src.ui.styles import COLORS, get_fonts
from src.core.employee_repo import EmployeeRepository
from src.core.certificate_service import CertificateService


class BatchImportPage(ctk.CTkFrame):
    """Pagina de importacao em lote de certificados."""

    def __init__(self, master, employee_repo: EmployeeRepository,
                 certificate_service: CertificateService, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.employee_repo = employee_repo
        self.certificate_service = certificate_service
        self._rows = []
        self._cancelled = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_ui()

    def _build_ui(self):
        fonts = get_fonts()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Importacao em Lote",
            font=fonts["title"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Gere certificados a partir de uma planilha Excel",
            font=fonts["small"], text_color=COLORS["muted"]
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        file_frame = ctk.CTkFrame(self, fg_color="transparent")
        file_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        file_frame.grid_columnconfigure(0, weight=1)

        self._file_var = ctk.StringVar()
        ctk.CTkEntry(
            file_frame, textvariable=self._file_var,
            font=fonts["body"], height=36, corner_radius=6,
            placeholder_text="Selecione um arquivo .xlsx...",
            state="readonly"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            file_frame, text="Procurar...", width=100, height=36,
            font=fonts["body"], fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"], command=self._browse_file
        ).grid(row=0, column=1)

        ctk.CTkLabel(
            self,
            text="Formato: Coluna A = Nome, Coluna B = NR (ex: NR-12), Coluna C = Data (dd/mm/aaaa)\n"
                 "A primeira linha (cabecalho) sera ignorada.",
            font=fonts["small"], text_color=COLORS["text_secondary"], justify="left"
        ).grid(row=2, column=0, sticky="nw", padx=20, pady=(0, 5))

        self._preview_frame = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["surface"], corner_radius=12
        )
        self._preview_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 10))
        self._preview_frame.grid_columnconfigure(0, weight=3)
        self._preview_frame.grid_columnconfigure(1, weight=1)
        self._preview_frame.grid_columnconfigure(2, weight=2)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 5))

        self._btn_cancel = ctk.CTkButton(
            btn_frame, text="Cancelar", font=fonts["body"],
            height=36, fg_color=COLORS["error"], hover_color="#C0392B",
            command=self._cancel_import, state="disabled"
        )
        self._btn_cancel.pack(side="left")

        self._btn_import = ctk.CTkButton(
            btn_frame, text="Gerar Todos", font=fonts["body_bold"],
            height=36, fg_color=COLORS["success"], hover_color="#256B28",
            command=self._do_import, state="disabled"
        )
        self._btn_import.pack(side="right")

        self._status_label = ctk.CTkLabel(
            self, text="", font=fonts["body"], text_color=COLORS["text"]
        )
        self._status_label.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 5))

        self._terminal = ctk.CTkTextbox(
            self, font=ctk.CTkFont(family="Consolas", size=11),
            height=150,
            fg_color="#1a1a2e", text_color="#00ff41",
            state="disabled", corner_radius=6
        )
        self._terminal.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 10))

        self._result_box = ctk.CTkTextbox(
            self, font=fonts["mono"], height=80,
            fg_color=COLORS["background"], text_color=COLORS["text"],
            state="disabled", corner_radius=6
        )
        self._result_box.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 15))

    def _log(self, msg: str):
        self._terminal.configure(state="normal")
        self._terminal.insert("end", msg + "\n")
        self._terminal.see("end")
        self._terminal.configure(state="disabled")
        self.update_idletasks()

    def _clear_terminal(self):
        self._terminal.configure(state="normal")
        self._terminal.delete("1.0", "end")
        self._terminal.configure(state="disabled")

    def _cancel_import(self):
        self._cancelled = True

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Selecionar planilha",
            filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")]
        )
        if path:
            self._file_var.set(path)
            self._load_preview(path)

    def _load_preview(self, filepath: str):
        from src.utils.batch_importer import read_batch_spreadsheet

        rows, errors = read_batch_spreadsheet(filepath)
        self._rows = rows

        for w in self._preview_frame.winfo_children():
            w.destroy()

        fonts = get_fonts()

        if errors:
            for err in errors[:5]:
                ctk.CTkLabel(
                    self._preview_frame, text=err,
                    font=fonts["small"], text_color=COLORS["error"]
                ).pack(anchor="w", padx=8, pady=2)

        if not rows:
            ctk.CTkLabel(
                self._preview_frame, text="Nenhum dado valido encontrado",
                font=fonts["body"], text_color=COLORS["muted"]
            ).pack(pady=20)
            self._btn_import.configure(state="disabled")
            return

        header = ctk.CTkFrame(self._preview_frame, fg_color=COLORS["primary"], corner_radius=6, height=32)
        header.pack(fill="x", padx=8, pady=(4, 2))
        header.pack_propagate(False)
        header.grid_columnconfigure(0, weight=3)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=2)

        for col, text in enumerate(["Nome", "NR", "Data"]):
            ctk.CTkLabel(
                header, text=text, font=fonts["small_bold"],
                text_color=COLORS["surface"]
            ).grid(row=0, column=col, sticky="w", padx=12, pady=4)

        for i, row in enumerate(rows[:50]):
            bg = COLORS["background"] if i % 2 == 1 else "transparent"
            r = ctk.CTkFrame(self._preview_frame, fg_color=bg, corner_radius=0, height=30)
            r.pack(fill="x", padx=8)
            r.pack_propagate(False)
            r.grid_columnconfigure(0, weight=3)
            r.grid_columnconfigure(1, weight=1)
            r.grid_columnconfigure(2, weight=2)

            ctk.CTkLabel(r, text=row["nome"], font=fonts["body"], text_color=COLORS["text"], anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=4)
            ctk.CTkLabel(r, text=row["nr_code"], font=fonts["body"], text_color=COLORS["primary"], anchor="w").grid(row=0, column=1, sticky="w", padx=12, pady=4)
            ctk.CTkLabel(r, text=row["data"].strftime("%d/%m/%Y"), font=fonts["body"], text_color=COLORS["text_secondary"], anchor="w").grid(row=0, column=2, sticky="w", padx=12, pady=4)

        if len(rows) > 50:
            ctk.CTkLabel(
                self._preview_frame, text=f"... e mais {len(rows) - 50} linhas",
                font=fonts["small"], text_color=COLORS["muted"]
            ).pack(pady=8)

        self._status_label.configure(text=f"{len(rows)} registros encontrados")
        self._btn_import.configure(state="normal")

    def _pre_validate(self):
        from src.utils.batch_importer import check_missing_employees

        missing = check_missing_employees(self._rows, self.employee_repo)
        if not missing:
            return True

        dialog = ctk.CTkToplevel(self)
        dialog.title("Funcionarios nao cadastrados")
        dialog.geometry("500x450")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(fg_color=COLORS["background"])

        fonts = get_fonts()

        ctk.CTkLabel(
            dialog, text=f"{len(missing)} funcionario(s) nao encontrado(s) no sistema:",
            font=fonts["body_bold"], text_color=COLORS["warning"]
        ).pack(padx=20, pady=(20, 10), anchor="w")

        list_frame = ctk.CTkScrollableFrame(
            dialog, fg_color=COLORS["surface"], corner_radius=8, height=200
        )
        list_frame.pack(fill="x", padx=20, pady=(0, 10))

        for name in missing:
            ctk.CTkLabel(
                list_frame, text=f"  - {name}",
                font=fonts["body"], text_color=COLORS["text"], anchor="w"
            ).pack(anchor="w", padx=8, pady=2)

        ctk.CTkLabel(
            dialog,
            text="Esses funcionarios serao cadastrados automaticamente\n"
                 "sem CPF. Deseja continuar?",
            font=fonts["body"], text_color=COLORS["text_secondary"], justify="center"
        ).pack(padx=20, pady=(0, 15))

        result = {"action": None}

        def on_confirm():
            result["action"] = "confirm"
            dialog.destroy()

        def on_cancel():
            result["action"] = "cancel"
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            btn_frame, text="Cancelar", font=fonts["body"],
            height=36, fg_color=COLORS["error"], hover_color="#C0392B",
            command=on_cancel
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Cadastrar e Continuar", font=fonts["body_bold"],
            height=36, fg_color=COLORS["success"], hover_color="#256B28",
            command=on_confirm
        ).pack(side="right")

        dialog.wait_window()
        return result["action"] == "confirm"

    def _do_import(self):
        if not self._rows:
            return

        if not self._pre_validate():
            self._status_label.configure(text="Importacao cancelada pelo usuario", text_color=COLORS["warning"])
            return

        self._cancelled = False
        self._btn_import.configure(state="disabled", text="Gerando...")
        self._btn_cancel.configure(state="normal")
        self._clear_terminal()
        self._log(f"Iniciando importacao de {len(self._rows)} registros...")
        self._log(f"Processando com 2 threads paralelas...")
        self._log("-" * 50)
        self.update()

        def on_progress(current, total, name):
            self.after(0, lambda c=current, t=total: self._status_label.configure(
                text=f"Processando {c}/{t} - {c*100//t}%"))

        def on_log(msg):
            self.after(0, lambda m=msg: self._log(m))

        def run_batch():
            from src.utils.batch_importer import generate_batch_certificates
            result = generate_batch_certificates(
                self._rows, self.employee_repo, self.certificate_service,
                on_progress=on_progress, on_log=on_log, max_workers=2
            )
            self.after(0, lambda: self._on_import_complete(result))

        threading.Thread(target=run_batch, daemon=True).start()

    def _on_import_complete(self, result):
        self._btn_import.configure(state="normal", text="Gerar Todos")
        self._btn_cancel.configure(state="disabled")

        self._log("-" * 50)
        self._log("Importacao concluida!")

        lines = []
        if result["gerados"] > 0:
            lines.append(f"Gerados: {result['gerados']}")
        if result["registrados_sem_pdf"] > 0:
            lines.append(f"Registrados (sem PDF): {result['registrados_sem_pdf']}")
        if result["erros"]:
            lines.append(f"Erros: {len(result['erros'])}")

        summary = " | ".join(lines) if lines else "Nenhum certificado gerado"
        color = COLORS["success"] if result["gerados"] > 0 else COLORS["warning"]
        self._status_label.configure(text=summary, text_color=color)

        self._result_box.configure(state="normal")
        self._result_box.delete("1.0", "end")
        if result["gerados"] > 0:
            self._result_box.insert("end", f"OK: {result['gerados']} certificado(s) gerado(s) com PDF\n")
        if result["registrados_sem_pdf"] > 0:
            self._result_box.insert("end", f"SEM PDF: {result['registrados_sem_pdf']} certificado(s) registrado(s) sem PDF (sem CPF)\n")
        for err in result["erros"][:20]:
            self._result_box.insert("end", f"ERRO: {err}\n")
        if len(result["erros"]) > 20:
            self._result_box.insert("end", f"... e mais {len(result['erros'])-20} erros\n")
        self._result_box.configure(state="disabled")

        self._show_report(result)

        if result["gerados"] > 0:
            self._rows = []
            self._file_var.set("")
            for w in self._preview_frame.winfo_children():
                w.destroy()

    def _show_report(self, result: dict):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Relatorio da Importacao")
        dialog.geometry("450x400")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(fg_color=COLORS["background"])

        fonts = get_fonts()

        ctk.CTkLabel(
            dialog, text="Relatorio da Importacao",
            font=fonts["title"], text_color=COLORS["primary"]
        ).pack(padx=20, pady=(20, 15))

        ctk.CTkLabel(
            dialog, text=f"Total processado: {len(self._rows) if self._rows else result['gerados'] + result['registrados_sem_pdf'] + len(result['erros'])}",
            font=fonts["body"], text_color=COLORS["text"]
        ).pack(padx=20, pady=(0, 10))

        stats_frame = ctk.CTkFrame(dialog, fg_color=COLORS["surface"], corner_radius=8)
        stats_frame.pack(fill="x", padx=20, pady=(0, 15))

        if result["gerados"] > 0:
            row = ctk.CTkFrame(stats_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=8)
            ctk.CTkLabel(row, text="certificados gerados com PDF", font=fonts["body"], text_color=COLORS["success"]).pack(side="left")
            ctk.CTkLabel(row, text=str(result["gerados"]), font=fonts["body_bold"], text_color=COLORS["success"]).pack(side="right")

        if result["registrados_sem_pdf"] > 0:
            row = ctk.CTkFrame(stats_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=8)
            ctk.CTkLabel(row, text="registrados sem PDF (sem CPF)", font=fonts["body"], text_color=COLORS["warning"]).pack(side="left")
            ctk.CTkLabel(row, text=str(result["registrados_sem_pdf"]), font=fonts["body_bold"], text_color=COLORS["warning"]).pack(side="right")

        if result["erros"]:
            row = ctk.CTkFrame(stats_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=8)
            ctk.CTkLabel(row, text="erros", font=fonts["body"], text_color=COLORS["error"]).pack(side="left")
            ctk.CTkLabel(row, text=str(len(result["erros"])), font=fonts["body_bold"], text_color=COLORS["error"]).pack(side="right")

        ctk.CTkButton(
            dialog, text="Fechar", font=fonts["body_bold"],
            height=36, fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            command=dialog.destroy
        ).pack(padx=20, pady=(15, 20))
