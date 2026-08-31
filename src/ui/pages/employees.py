import customtkinter as ctk
from tkinter import messagebox, filedialog
from typing import Optional
from src.ui.styles import COLORS, get_fonts
from src.core.models import Employee
from src.core.employee_repo import EmployeeRepository
from src.utils.validators import validar_cpf, formatar_cpf
from src.ui.components.pagination import PaginationBar


class EmployeesPage(ctk.CTkFrame):
    def __init__(self, master, employee_repo: EmployeeRepository, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.employee_repo = employee_repo
        self.selected_employee: Optional[Employee] = None

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        fonts = get_fonts()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_propagate(False)

        # Row 0 — Header
        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        self._header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self._header, text="Funcionarios Cadastrados",
            font=fonts["title"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(self._header, fg_color="transparent")
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
        search_frame = ctk.CTkFrame(self._header, fg_color="transparent")
        search_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_frame, textvariable=self.search_var,
            font=fonts["body"], height=36, corner_radius=6,
            placeholder_text="Buscar por nome ou CPF..."
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_var.trace_add("write", lambda *args: self._on_search())

        funcoes_disponiveis = ["Todas"] + self.employee_repo.get_all_funcoes()
        self._funcao_filter_var = ctk.StringVar(value="Todas")
        self._funcao_filter_menu = ctk.CTkOptionMenu(
            search_frame, variable=self._funcao_filter_var,
            values=funcoes_disponiveis,
            font=fonts["small"], height=36, width=160,
            fg_color=COLORS["surface"], button_color=COLORS["secondary"],
            button_hover_color=COLORS["primary"],
            command=lambda _: self._refresh_list()
        )
        self._funcao_filter_menu.grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            search_frame, text="X", width=36, height=36,
            font=fonts["body"], fg_color=COLORS["muted"],
            hover_color=COLORS["text_secondary"],
            command=self._clear_search
        ).grid(row=0, column=2)

        # Row 1 — Lista (weight=1 preenche resto)
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"], corner_radius=12, height=200)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 5))
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Row 2 — Paginacao
        self.pagination = PaginationBar(self, on_page_change=self._refresh_list)
        self.pagination.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 5))

        self.after(200, lambda: self._fit_scroll_height(0))
        self.after(600, lambda: self._fit_scroll_height(0))

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
        if min(header_h, pag_h) < 5 and _retry < 5:
            self.after(300, lambda r=_retry + 1: self._fit_scroll_height(r))
            return
        margins = 30
        available = h - header_h - pag_h - margins
        self.list_frame.configure(height=max(available, 150))

    def _refresh_funcao_filter(self):
        """Repopula o dropdown de filtro de funcao com dados atuais do banco (pos-import/cadastro)."""
        if not hasattr(self, "_funcao_filter_menu"):
            return
        atual = self._funcao_filter_var.get()
        funcoes = ["Todas"] + self.employee_repo.get_all_funcoes()
        self._funcao_filter_menu.configure(values=funcoes)
        if atual not in funcoes:
            self._funcao_filter_var.set("Todas")

    def _clear_search(self):
        self.search_var.set("")
        self._funcao_filter_var.set("Todas")
        self.pagination.reset()
        self._refresh_list()

    def _on_search(self):
        self.pagination.reset()
        self._refresh_list()

    def _refresh_list(self):
        fonts = get_fonts()
        query = self.search_var.get().strip()
        funcao_filter = self._funcao_filter_var.get()

        for widget in self.list_frame.winfo_children():
            widget.destroy()

        # Buscar com paginacao
        if query:
            total = self.employee_repo.count_search(query)
        else:
            total = self.employee_repo.count_all()

        self.pagination.set_total(total)

        if query:
            employees = self.employee_repo.search(query, limit=PaginationBar.ITEMS_PER_PAGE * 10)
        else:
            employees = self.employee_repo.get_all(limit=PaginationBar.ITEMS_PER_PAGE, offset=self.pagination.offset)

        # Filtro de funcao (client-side)
        if funcao_filter and funcao_filter != "Todas":
            employees = [e for e in employees if (e.funcao or "") == funcao_filter]
            total = len(employees)

        if not employees:
            ctk.CTkLabel(
                self.list_frame,
                text="Nenhum funcionario cadastrado" if not query else "Nenhum resultado encontrado",
                font=fonts["body"], text_color=COLORS["muted"]
            ).grid(row=0, column=0, pady=40, padx=20)
            return

        # Header da tabela
        header = ctk.CTkFrame(self.list_frame, fg_color=COLORS["primary"], corner_radius=6, height=36)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 2))
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=0)
        header.grid_columnconfigure(1, weight=3)
        header.grid_columnconfigure(2, weight=2)
        header.grid_columnconfigure(3, weight=2)
        header.grid_columnconfigure(4, weight=2)
        header.grid_columnconfigure(5, weight=1)

        for col, text in enumerate(["Foto", "Nome", "Funcao", "CPF", "Telefone", "Acoes"]):
            ctk.CTkLabel(
                header, text=text, font=fonts["body_bold"],
                text_color="#FFFFFF", anchor="center" if col < 5 else "e"
            ).grid(row=0, column=col, sticky="ew" if col < 5 else "e", padx=10, pady=6)

        for i, emp in enumerate(employees):
            self._create_employee_row(emp, i + 1, i % 2 == 1)

    def _create_employee_row(self, emp: Employee, row_idx: int, alternate: bool = False):
        fonts = get_fonts()
        bg = COLORS["background"] if alternate else "transparent"
        row = ctk.CTkFrame(self.list_frame, fg_color=bg, corner_radius=0, height=40)
        row.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=0)
        row.grid_propagate(False)
        row.grid_columnconfigure(0, weight=0)
        row.grid_columnconfigure(1, weight=3)
        row.grid_columnconfigure(2, weight=2)
        row.grid_columnconfigure(3, weight=2)
        row.grid_columnconfigure(4, weight=2)
        row.grid_columnconfigure(5, weight=1)

        # Foto thumb 3x4
        if emp.foto:
            try:
                from src.utils.photo_utils import bytes_to_pil_image
                from PIL import Image
                pil = bytes_to_pil_image(emp.foto)
                if pil:
                    pil_thumb = pil.copy()
                    pil_thumb.thumbnail((28, 36), Image.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=pil_thumb, dark_image=pil_thumb, size=(28, 36))
                    lbl_img = ctk.CTkLabel(row, image=ctk_img, text="")
                    lbl_img.grid(row=0, column=0, padx=(8, 2), pady=4)
                    lbl_img._img_ref = ctk_img
                else:
                    ctk.CTkLabel(row, text="--", font=fonts["small"], text_color=COLORS["muted"]).grid(row=0, column=0, padx=8, pady=6)
            except Exception:
                ctk.CTkLabel(row, text="--", font=fonts["small"], text_color=COLORS["muted"]).grid(row=0, column=0, padx=8, pady=6)
        else:
            ctk.CTkLabel(row, text="--", font=fonts["small"], text_color=COLORS["muted"]).grid(row=0, column=0, padx=8, pady=6)

        tel_display = emp.telefone_formatado() if emp.telefone else "-"
        ctk.CTkLabel(row, text=emp.nome, font=fonts["body"], text_color=COLORS["text"], anchor="center").grid(row=0, column=1, sticky="ew", padx=10, pady=6)
        funcao_text = emp.funcao if emp.funcao else "-"
        ctk.CTkLabel(row, text=funcao_text, font=fonts["body"], text_color=COLORS["text_secondary"], anchor="center").grid(row=0, column=2, sticky="ew", padx=10, pady=6)
        ctk.CTkLabel(row, text=emp.cpf or "-", font=fonts["body"], text_color=COLORS["text_secondary"], anchor="center").grid(row=0, column=3, sticky="ew", padx=10, pady=6)
        ctk.CTkLabel(row, text=tel_display, font=fonts["body"], text_color=COLORS["text_secondary"], anchor="center").grid(row=0, column=4, sticky="ew", padx=10, pady=6)

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=5, sticky="e", padx=8, pady=4)

        ctk.CTkButton(
            btn_frame, text="Editar", width=60, height=26,
            font=fonts["small"], fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"],
            command=lambda e=emp: self._open_edit_dialog(e)
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text="Excluir", width=60, height=26,
            font=fonts["small"], fg_color=COLORS["error"],
            hover_color="#B71C1C",
            command=lambda e=emp: self._confirm_delete(e)
        ).pack(side="left", padx=2)

        sep = ctk.CTkFrame(self.list_frame, fg_color=COLORS["border"], height=1)
        sep.grid(row=row_idx + 1, column=0, sticky="ew", padx=12, pady=0)

    def _open_new_dialog(self):
        self._open_employee_dialog()

    def _open_edit_dialog(self, employee: Employee):
        self._open_employee_dialog(employee)

    def _open_employee_dialog(self, employee: Employee = None):
        fonts = get_fonts()
        is_edit = employee is not None

        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar Funcionario" if is_edit else "Novo Funcionario")
        dialog.geometry("520x680")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (520 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (680 // 2)
        dialog.geometry(f"+{x}+{y}")

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24, pady=24)
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form, text="Editar Funcionario" if is_edit else "Cadastrar Novo Funcionario",
            font=fonts["heading"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, pady=(0, 12))

        # --- Foto 3x4 ---
        foto_bytes = employee.foto if (is_edit and employee.foto) else None
        foto_changed = {"val": False}
        try:
            from src.utils.photo_utils import process_photo_3x4, bytes_to_pil_image
            from PIL import Image
        except Exception:
            process_photo_3x4 = None
            bytes_to_pil_image = None

        foto_frame = ctk.CTkFrame(form, fg_color=COLORS["background"], corner_radius=8, border_width=1, border_color=COLORS["border"], width=120, height=160)
        foto_frame.grid(row=1, column=0, pady=(0, 12))
        foto_frame.grid_propagate(False)
        foto_frame.grid_columnconfigure(0, weight=1)
        foto_frame.grid_rowconfigure(0, weight=1)

        lbl_foto = ctk.CTkLabel(foto_frame, text="Sem foto\n3x4", font=fonts["small"], text_color=COLORS["muted"])
        lbl_foto.grid(row=0, column=0, sticky="nsew")
        lbl_foto._image_ref = None  # keep ref

        def update_foto_preview(data: bytes = None):
            if data and bytes_to_pil_image:
                pil = bytes_to_pil_image(data)
                if pil:
                    try:
                        pil_thumb = pil.copy()
                        pil_thumb.thumbnail((90, 120), Image.LANCZOS)
                        ctk_img = ctk.CTkImage(light_image=pil_thumb, dark_image=pil_thumb, size=(90, 120))
                        lbl_foto.configure(image=ctk_img, text="")
                        lbl_foto._image_ref = ctk_img
                        return
                    except Exception:
                        pass
            lbl_foto.configure(image=None, text="Sem foto\n3x4")
            lbl_foto._image_ref = None

        if foto_bytes:
            update_foto_preview(foto_bytes)

        btn_foto_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_foto_frame.grid(row=2, column=0, pady=(0, 12))

        def choose_foto():
            if process_photo_3x4 is None:
                messagebox.showerror("Erro", "Pillow nao instalado", parent=dialog)
                return
            path = filedialog.askopenfilename(
                title="Escolher foto 3x4",
                filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Todos", "*.*")],
                parent=dialog
            )
            if not path:
                return
            try:
                data = process_photo_3x4(path)
                foto_bytes_new = data
                update_foto_preview(data)
                # armazena no closure
                nonlocal foto_bytes
                foto_bytes = foto_bytes_new
                foto_changed["val"] = True
            except Exception as e:
                messagebox.showerror("Erro", str(e), parent=dialog)

        def remove_foto():
            nonlocal foto_bytes
            foto_bytes = None
            foto_changed["val"] = True
            update_foto_preview(None)

        ctk.CTkButton(btn_foto_frame, text="Escolher foto", width=120, height=28, font=fonts["small"], fg_color=COLORS["secondary"], hover_color=COLORS["primary"], command=choose_foto).pack(side="left", padx=4)
        ctk.CTkButton(btn_foto_frame, text="Remover", width=80, height=28, font=fonts["small"], fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"], command=remove_foto).pack(side="left", padx=4)

        ctk.CTkLabel(form, text="Nome Completo *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=3, column=0, sticky="w", pady=(0, 4))
        nome_var = ctk.StringVar(value=employee.nome if is_edit else "")
        ctk.CTkEntry(form, textvariable=nome_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="Nome completo do funcionario").grid(row=4, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(form, text="CPF", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=5, column=0, sticky="w", pady=(0, 4))
        cpf_var = ctk.StringVar(value=employee.cpf if is_edit else "")
        ctk.CTkEntry(form, textvariable=cpf_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="000.000.000-00 (opcional)").grid(row=6, column=0, sticky="ew", pady=(0, 10))

        def format_cpf_entry(*args):
            val = cpf_var.get()
            if len(val) > 14:
                cpf_var.set(val[:14])
        cpf_var.trace_add("write", format_cpf_entry)

        ctk.CTkLabel(form, text="Telefone (celular)", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=7, column=0, sticky="w", pady=(0, 4))
        tel_display = ""
        if is_edit and employee.telefone:
            from src.utils.validators import formatar_telefone
            tel_display = formatar_telefone(employee.telefone)
        tel_var = ctk.StringVar(value=tel_display)
        ctk.CTkEntry(form, textvariable=tel_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="(21) 98420-9236 (opcional)").grid(row=8, column=0, sticky="ew", pady=(0, 10))

        def format_tel_entry(*args):
            # so formata quando os 11 digitos estao completos — evita cursor pulando durante digitacao
            import re as _re
            val = tel_var.get()
            dig = _re.sub(r'\D', '', val)
            if len(dig) < 11:
                return
            dig = dig[:11]
            tel_var.set(f"({dig[:2]}) {dig[2:7]}-{dig[7:]}")
        tel_var.trace_add("write", format_tel_entry)

        ctk.CTkLabel(form, text="Funcao", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=9, column=0, sticky="w", pady=(0, 4))
        from src.ui.pages.funcoes import load_funcoes
        funcoes_list = load_funcoes()
        funcao_var = ctk.StringVar(value=employee.funcao if (is_edit and employee.funcao) else "")
        funcao_entry = ctk.CTkComboBox(
            form, variable=funcao_var,
            values=funcoes_list if funcoes_list else ["Selecione uma funcao"],
            font=fonts["body"], height=36, corner_radius=6,
            fg_color=COLORS["surface"], border_color=COLORS["border"],
            button_color=COLORS["secondary"], button_hover_color=COLORS["primary"],
            state="readonly"
        )
        funcao_entry.grid(row=10, column=0, sticky="ew", pady=(0, 12))

        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.grid(row=11, column=0, sticky="ew", pady=(8, 0))
        btn_frame.grid_columnconfigure(0, weight=1)

        def save():
            nome = nome_var.get().strip()
            cpf = cpf_var.get().strip()
            funcao = funcao_var.get().strip() if funcao_var.get() else None
            tel_raw = tel_var.get().strip()
            if not nome:
                messagebox.showerror("Erro", "Nome e obrigatorio", parent=dialog)
                return
            cpf_fmt = None
            if cpf:
                if not validar_cpf(cpf):
                    messagebox.showerror("Erro", "CPF invalido", parent=dialog)
                    return
                cpf_fmt = formatar_cpf(cpf)
            tel_fmt = None
            if tel_raw:
                from src.utils.validators import validar_telefone
                if not validar_telefone(tel_raw):
                    messagebox.showerror("Erro", "Telefone invalido: use celular com DDD, 11 digitos (ex: (21) 98420-9236)", parent=dialog)
                    return
                import re as _re
                tel_fmt = _re.sub(r'\D', '', tel_raw)
            try:
                if is_edit:
                    success = self.employee_repo.update(employee.id, nome, cpf_fmt, funcao, telefone=tel_fmt)
                    if not success:
                        messagebox.showerror("Erro", "Erro ao atualizar funcionario", parent=dialog)
                        return
                    if foto_changed["val"]:
                        self.employee_repo.update_foto(employee.id, foto_bytes)
                    messagebox.showinfo("Sucesso", "Funcionario atualizado!", parent=dialog)
                else:
                    emp_id = self.employee_repo.create(nome, cpf_fmt, funcao, foto_bytes if foto_changed["val"] or foto_bytes else None, telefone=tel_fmt)
                    if emp_id:
                        messagebox.showinfo("Sucesso", "Funcionario cadastrado!", parent=dialog)
                    else:
                        messagebox.showerror("Erro", "Erro ao cadastrar funcionario", parent=dialog)
                        return
                dialog.destroy()
                self._refresh_funcao_filter()
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
                self._refresh_funcao_filter()
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
        fonts = get_fonts()

        dialog = ctk.CTkToplevel(self)
        dialog.title("Importar Funcionarios de Excel")
        dialog.geometry("550x480")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (550 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (480 // 2)
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
            text="Formato: Coluna A = Nome, Coluna B = CPF (opcional), Coluna C = Funcao (opcional),\nColuna D = Telefone celular (opcional, 11 digitos: 21984209236)\nA primeira linha (cabecalho) sera ignorada.",
            font=fonts["small"], text_color=COLORS["text_secondary"], justify="left"
        ).grid(row=1, column=0, sticky="w", pady=(0, 16))

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

        self._import_status = ctk.CTkLabel(
            content, text="", font=fonts["body"],
            text_color=COLORS["text"], justify="left"
        )
        self._import_status.grid(row=3, column=0, sticky="w", pady=(8, 16))

        self._import_result = ctk.CTkTextbox(
            content, font=fonts["mono"], height=120,
            fg_color=COLORS["background"], text_color=COLORS["text"],
            state="disabled", corner_radius=6
        )
        self._import_result.grid(row=4, column=0, sticky="ew", pady=(0, 16))

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
            self._refresh_funcao_filter()
            self._refresh_list()

    def refresh(self):
        self._refresh_funcao_filter()
        self._refresh_list()
