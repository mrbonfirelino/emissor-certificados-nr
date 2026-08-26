import customtkinter as ctk
from tkinter import messagebox, filedialog
from typing import Optional
from src.ui.styles import COLORS, get_fonts
from src.core.models import Employee
from src.core.employee_repo import EmployeeRepository
from src.utils.validators import validar_cpf, formatar_cpf


class EmployeesPage(ctk.CTkFrame):
    def __init__(self, master, employee_repo: EmployeeRepository, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.employee_repo = employee_repo
        self.selected_employee: Optional[Employee] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        fonts = get_fonts()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Funcionarios Cadastrados",
            font=fonts["title"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w")

        # Botoes
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Exportar Excel",
            font=fonts["body_bold"], height=32,
            fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
            command=self._export_excel
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Importar Excel",
            font=fonts["body_bold"], height=32,
            fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
            command=self._open_import_dialog
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="+ Novo",
            font=fonts["body_bold"], height=32,
            fg_color=COLORS["success"], hover_color="#256B28",
            command=self._open_new_dialog
        ).pack(side="left")

        # Search
        search_frame = ctk.CTkFrame(header, fg_color="transparent")
        search_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_frame, textvariable=self.search_var,
            font=fonts["body"], height=36, corner_radius=6,
            placeholder_text="🔍 Buscar por nome ou CPF..."
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_var.trace_add("write", lambda *args: self._refresh_list())

        ctk.CTkButton(
            search_frame, text="X", width=36, height=36,
            font=fonts["body"], fg_color=COLORS["muted"],
            hover_color=COLORS["text_secondary"],
            command=lambda: self.search_var.set("")
        ).grid(row=0, column=1)

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"], corner_radius=12)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        fonts = get_fonts()
        query = self.search_var.get().strip()
        if query:
            employees = self.employee_repo.search(query, limit=100)
        else:
            employees = self.employee_repo.get_all(limit=100)

        if not employees:
            ctk.CTkLabel(
                self.list_frame,
                text="Nenhum funcionario cadastrado" if not query else "Nenhum resultado encontrado",
                font=fonts["body"], text_color=COLORS["muted"]
            ).pack(pady=40)
            return

        for emp in employees:
            self._create_employee_row(emp)

    def _create_employee_row(self, emp: Employee):
        fonts = get_fonts()
        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.pack(fill="x", pady=4, padx=8)
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text=emp.nome, font=fonts["body"], text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=12, pady=8)
        ctk.CTkLabel(row, text=emp.cpf, font=fonts["body"], text_color=COLORS["text_secondary"]).grid(row=0, column=1, sticky="w", padx=12, pady=8)

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=2, sticky="e", padx=12, pady=4)

        ctk.CTkButton(
            btn_frame, text="Editar", width=60, height=28,
            font=fonts["small"], fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"],
            command=lambda e=emp: self._open_edit_dialog(e)
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text="Excluir", width=60, height=28,
            font=fonts["small"], fg_color=COLORS["error"],
            hover_color="#B71C1C",
            command=lambda e=emp: self._confirm_delete(e)
        ).pack(side="left", padx=2)

    def _open_new_dialog(self):
        self._open_employee_dialog()

    def _open_edit_dialog(self, employee: Employee):
        self._open_employee_dialog(employee)

    def _open_employee_dialog(self, employee: Employee = None):
        fonts = get_fonts()
        is_edit = employee is not None

        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar Funcionario" if is_edit else "Novo Funcionario")
        dialog.geometry("450x350")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (450 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (350 // 2)
        dialog.geometry(f"+{x}+{y}")

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=30, pady=30)
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form, text="Editar Funcionario" if is_edit else "Cadastrar Novo Funcionario",
            font=fonts["heading"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, pady=(0, 20))

        ctk.CTkLabel(form, text="Nome Completo *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=1, column=0, sticky="w", pady=(0, 4))
        nome_var = ctk.StringVar(value=employee.nome if is_edit else "")
        ctk.CTkEntry(form, textvariable=nome_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="Nome completo do funcionario").grid(row=2, column=0, sticky="ew", pady=(0, 16))

        ctk.CTkLabel(form, text="CPF *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=3, column=0, sticky="w", pady=(0, 4))
        cpf_var = ctk.StringVar(value=employee.cpf if is_edit else "")
        ctk.CTkEntry(form, textvariable=cpf_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="000.000.000-00").grid(row=4, column=0, sticky="ew", pady=(0, 20))

        def format_cpf_entry(*args):
            val = cpf_var.get()
            if len(val) > 14:
                cpf_var.set(val[:14])
        cpf_var.trace_add("write", format_cpf_entry)

        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        def save():
            nome = nome_var.get().strip()
            cpf = cpf_var.get().strip()
            if not nome:
                messagebox.showerror("Erro", "Nome e obrigatorio", parent=dialog)
                return
            if not cpf or not validar_cpf(cpf):
                messagebox.showerror("Erro", "CPF invalido", parent=dialog)
                return
            cpf_fmt = formatar_cpf(cpf)
            try:
                if is_edit:
                    success = self.employee_repo.update(employee.id, nome, cpf_fmt)
                    if success:
                        messagebox.showinfo("Sucesso", "Funcionario atualizado!", parent=dialog)
                    else:
                        messagebox.showerror("Erro", "CPF ja cadastrado para outro funcionario", parent=dialog)
                        return
                else:
                    emp_id = self.employee_repo.create(nome, cpf_fmt)
                    if emp_id:
                        messagebox.showinfo("Sucesso", "Funcionario cadastrado!", parent=dialog)
                    else:
                        messagebox.showerror("Erro", "CPF ja cadastrado", parent=dialog)
                        return
                dialog.destroy()
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar: {e}", parent=dialog)

        ctk.CTkButton(btn_frame, text="Cancelar", font=fonts["body_bold"], height=36, fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"], command=dialog.destroy).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(btn_frame, text="Salvar", font=fonts["body_bold"], height=36, fg_color=COLORS["success"], hover_color="#256B28", command=save).grid(row=0, column=1, sticky="e")

    def _confirm_delete(self, employee: Employee):
        from src.core.history_repo import HistoryRepository
        history = HistoryRepository()
        certs = history.get_by_employee(employee.id)

        if certs:
            messagebox.showerror(
                "Nao e possivel excluir",
                f"O funcionario '{employee.nome}' possui {len(certs)} certificado(s) emitido(s).\n"
                "Nao e possivel excluir para manter a integridade do historico.",
                parent=self
            )
            return

        if messagebox.askyesno(
            "Confirmar Exclusao",
            f"Tem certeza que deseja excluir '{employee.nome}' ({employee.cpf})?",
            parent=self
        ):
            if self.employee_repo.delete(employee.id):
                messagebox.showinfo("Sucesso", "Funcionario excluido!", parent=self)
                self._refresh_list()
            else:
                messagebox.showerror("Erro", "Erro ao excluir", parent=self)

    def _export_excel(self):
        try:
            from src.utils.excel_exporter import export_employees_to_excel
        except ImportError:
            messagebox.showerror("Erro", "openpyxl nao instalado", parent=self)
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="funcionarios.xlsx",
            title="Exportar funcionarios"
        )
        if not path:
            return

        try:
            count = export_employees_to_excel(self.employee_repo, path)
            messagebox.showinfo("Sucesso", f"Exportados {count} funcionarios", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {e}", parent=self)

    def _open_import_dialog(self):
        """Dialog de importacao de Excel."""
        fonts = get_fonts()

        dialog = ctk.CTkToplevel(self)
        dialog.title("Importar Funcionarios de Excel")
        dialog.geometry("550x400")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (550 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (400 // 2)
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content, text="Importar Funcionarios de Excel",
            font=fonts["heading"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, pady=(0, 8))

        ctk.CTkLabel(
            content,
            text="Formato esperado: Coluna A = Nome, Coluna B = CPF\nA primeira linha (cabecalho) sera ignorada.",
            font=fonts["small"], text_color=COLORS["text_secondary"], justify="left"
        ).grid(row=1, column=0, sticky="w", pady=(0, 16))

        # File selection
        file_frame = ctk.CTkFrame(content, fg_color="transparent")
        file_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        file_frame.grid_columnconfigure(0, weight=1)

        self._import_file_var = ctk.StringVar()
        ctk.CTkEntry(
            file_frame, textvariable=self._import_file_var,
            font=fonts["body"], height=36, corner_radius=6,
            placeholder_text="Selecione um arquivo .xlsx...",
            state="readonly"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        def browse_file():
            path = filedialog.askopenfilename(
                title="Selecionar arquivo Excel",
                filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")],
                parent=dialog
            )
            if path:
                self._import_file_var.set(path)

        ctk.CTkButton(
            file_frame, text="Procurar...", width=90, height=36,
            font=fonts["body"], fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"], command=browse_file
        ).grid(row=0, column=1)

        # Status area
        self._import_status = ctk.CTkLabel(
            content, text="", font=fonts["body"],
            text_color=COLORS["text"], justify="left"
        )
        self._import_status.grid(row=3, column=0, sticky="w", pady=(8, 16))

        # Result text
        self._import_result = ctk.CTkTextbox(
            content, font=fonts["mono"], height=120,
            fg_color=COLORS["background"], text_color=COLORS["text"],
            state="disabled", corner_radius=6
        )
        self._import_result.grid(row=4, column=0, sticky="ew", pady=(0, 16))

        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="ew")

        ctk.CTkButton(
            btn_frame, text="Cancelar", font=fonts["body_bold"],
            height=36, fg_color=COLORS["muted"],
            hover_color=COLORS["text_secondary"], command=dialog.destroy
        ).pack(side="left")

        self._btn_import = ctk.CTkButton(
            btn_frame, text="Importar", font=fonts["body_bold"],
            height=36, fg_color=COLORS["success"],
            hover_color="#256B28", command=lambda: self._do_import(dialog)
        )
        self._btn_import.pack(side="right")

    def _do_import(self, dialog):
        """Executa a importacao."""
        from src.utils.excel_importer import import_employees_from_excel

        filepath = self._import_file_var.get()
        if not filepath:
            messagebox.showerror("Erro", "Selecione um arquivo Excel", parent=dialog)
            return

        self._btn_import.configure(state="disabled", text="Importando...")
        self._import_status.configure(text="Processando...", text_color=COLORS["text_secondary"])
        dialog.update()

        imported, duplicates, errors, error_details = import_employees_from_excel(
            filepath, self.employee_repo
        )

        self._btn_import.configure(state="normal", text="Importar")

        # Build result message
        lines = []
        if imported > 0:
            lines.append(f"Importados: {imported}")
        if duplicates > 0:
            lines.append(f"Duplicados (ignorados): {duplicates}")
        if errors > 0:
            lines.append(f"Erros: {errors}")

        if not lines:
            self._import_status.configure(text="Nenhum funcionario encontrado no arquivo.", text_color=COLORS["warning"])
            return

        summary = " | ".join(lines)
        color = COLORS["success"] if imported > 0 else COLORS["warning"]
        self._import_status.configure(text=summary, text_color=color)

        # Show details
        self._import_result.configure(state="normal")
        self._import_result.delete("1.0", "end")
        if imported > 0:
            self._import_result.insert("end", f"OK: {imported} funcionario(s) importado(s)\n")
        if duplicates > 0:
            self._import_result.insert("end", f"SKIP: {duplicates} CPF(s) ja existente(s)\n")
        for detail in error_details[:20]:
            self._import_result.insert("end", f"ERRO: {detail}\n")
        if len(error_details) > 20:
            self._import_result.insert("end", f"... e mais {len(error_details)-20} erros\n")
        self._import_result.configure(state="disabled")

        if imported > 0:
            self._refresh_list()
