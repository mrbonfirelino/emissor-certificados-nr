import customtkinter as ctk
import os
import subprocess
import sys
from typing import Callable
from src.ui.components.nr_selector import NRSelector
from src.ui.components.employee_autocomplete import EmployeeAutocomplete
from src.ui.components.dynamic_form import DynamicForm
from src.ui.components.pdf_preview import PDFPreview
from src.ui.styles import COLORS, get_fonts
from src.core.models import Employee
from src.core.template_loader import load_nr_template, get_template_description
from src.core.certificate_service import CertificateService
from src.utils.date_utils import hoje, data_para_str as formatar_data
from datetime import date


class CertificatesPage(ctk.CTkFrame):
    def __init__(
        self,
        master,
        certificate_service: CertificateService,
        employee_repo,
        on_navigate: Callable[[str], None] = None,
        **kwargs
    ):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.certificate_service = certificate_service
        self.employee_repo = employee_repo
        self.on_navigate = on_navigate

        self.selected_nr: str = None
        self.selected_employee: Employee = None
        self.current_template = None

        self._build_ui()
        self._load_first_nr()

    def _build_ui(self):
        fonts = get_fonts()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === SIDEBAR - NRs ===
        sidebar = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=0, width=220, border_width=1, border_color=COLORS["border"])
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        ctk.CTkLabel(
            header, text="Normas Regulamentadoras",
            font=fonts["heading"], text_color=COLORS["primary"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text="Selecione o NR",
            font=fonts["small"], text_color=COLORS["muted"]
        ).pack(anchor="w")

        self.nr_scroll = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.nr_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.nr_scroll.grid_columnconfigure(0, weight=1)
        self.nr_scroll.bind("<MouseWheel>", lambda e: self.nr_scroll._parent_canvas.yview_scroll(int(-1 * (e.delta / 120) * 2.5), "units"))

        self.nr_selector = NRSelector(self.nr_scroll, on_select=self._on_nr_selected, columns=1)
        self.nr_selector.pack(fill="both", expand=True)

        # === CONTEUDO ===
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        self.content_header = ctk.CTkFrame(content, fg_color="transparent")
        self.content_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.lbl_nr_title = ctk.CTkLabel(
            self.content_header, text="Selecione um NR",
            font=fonts["title"], text_color=COLORS["primary"]
        )
        self.lbl_nr_title.pack(anchor="w")

        self.lbl_nr_desc = ctk.CTkLabel(
            self.content_header, text="Escolha uma norma regulamentadora na lista ao lado",
            font=fonts["body"], text_color=COLORS["text_secondary"]
        )
        self.lbl_nr_desc.pack(anchor="w", pady=(2, 0))

        # Riscos badges
        self.riscos_frame = ctk.CTkFrame(self.content_header, fg_color="transparent")
        self.riscos_frame.pack(anchor="w", pady=(4, 0))

        # Form + Preview (40/60)
        main_split = ctk.CTkFrame(content, fg_color="transparent")
        main_split.grid(row=1, column=0, sticky="nsew")
        main_split.grid_columnconfigure(0, weight=2)
        main_split.grid_columnconfigure(1, weight=3)
        main_split.grid_rowconfigure(0, weight=1)

        # === FORM ===
        form_container = ctk.CTkFrame(main_split, fg_color=COLORS["surface"], corner_radius=12)
        form_container.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        form_container.grid_columnconfigure(0, weight=1)
        form_container.grid_rowconfigure(1, weight=1)

        form_header = ctk.CTkFrame(form_container, fg_color="transparent")
        form_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(
            form_header, text="Dados do Certificado",
            font=fonts["heading"], text_color=COLORS["primary"]
        ).pack(anchor="w")

        self.form_scroll = ctk.CTkScrollableFrame(form_container, fg_color="transparent")
        self.form_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.form_scroll.grid_columnconfigure(0, weight=1)
        self.form_scroll.bind("<MouseWheel>", lambda e: self.form_scroll._parent_canvas.yview_scroll(int(-1 * (e.delta / 120) * 2.5), "units"))

        self._build_form_fields()

        btn_frame = ctk.CTkFrame(form_container, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))

        self.btn_preview = ctk.CTkButton(
            btn_frame, text="Visualizar",
            font=fonts["body_bold"], height=36,
            fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
            command=self._on_preview
        )
        self.btn_preview.pack(side="left", padx=(0, 8))

        self.btn_generate = ctk.CTkButton(
            btn_frame, text="Gerar Certificado",
            font=fonts["body_bold"], height=36,
            fg_color=COLORS["success"], hover_color="#256B28",
            command=self._on_generate
        )
        self.btn_generate.pack(side="left", padx=(0, 8))

        self.btn_view_pdf = ctk.CTkButton(
            btn_frame, text="Visualizar PDF",
            font=fonts["body_bold"], height=36,
            fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
            command=self._on_view_pdf
        )
        self.btn_view_pdf.pack(side="left")

        # === PREVIEW ===
        self.preview = PDFPreview(main_split)
        self.preview.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        self.preview.set_on_pdf_preview(self._on_pdf_preview)

    def _build_form_fields(self):
        fonts = get_fonts()

        ctk.CTkLabel(self.form_scroll, text="Nome do Funcionario *", font=fonts["body_bold"], text_color=COLORS["text"]).pack(anchor="w", pady=(0, 4))

        self.employee_autocomplete = EmployeeAutocomplete(
            self.form_scroll, employee_repo=self.employee_repo,
            on_select=self._on_employee_selected,
            placeholder="Digite nome ou CPF..."
        )
        self.employee_autocomplete.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(self.form_scroll, text="CPF", font=fonts["body_bold"], text_color=COLORS["text"]).pack(anchor="w", pady=(0, 4))
        self.cpf_var = ctk.StringVar()
        self.cpf_entry = ctk.CTkEntry(
            self.form_scroll, textvariable=self.cpf_var,
            font=fonts["body"], height=32, corner_radius=6,
            placeholder_text="Auto-preenchido", state="readonly"
        )
        self.cpf_entry.pack(fill="x", pady=(0, 12))

        # Data do treinamento (dia unico)
        ctk.CTkLabel(self.form_scroll, text="Data do Treinamento *", font=fonts["body_bold"], text_color=COLORS["text"]).pack(anchor="w", pady=(0, 4))
        self.data_var = ctk.StringVar(value=formatar_data(hoje()))
        ctk.CTkEntry(
            self.form_scroll, textvariable=self.data_var,
            font=fonts["body"], height=32, corner_radius=6,
            placeholder_text="DD/MM/AAAA"
        ).pack(fill="x", pady=(0, 12))

        # Carga Horaria
        ctk.CTkLabel(self.form_scroll, text="Carga Horaria (h) *", font=fonts["body_bold"], text_color=COLORS["text"]).pack(anchor="w", pady=(0, 4))
        self.carga_var = ctk.StringVar(value="8")
        ctk.CTkEntry(
            self.form_scroll, textvariable=self.carga_var,
            font=fonts["body"], height=32, corner_radius=6,
            placeholder_text="Ex: 8"
        ).pack(fill="x", pady=(0, 12))

        # Descricao
        ctk.CTkLabel(self.form_scroll, text="Descricao *", font=fonts["body_bold"], text_color=COLORS["text"]).pack(anchor="w", pady=(0, 4))
        self.desc_var = ctk.StringVar()
        ctk.CTkEntry(
            self.form_scroll, textvariable=self.desc_var,
            font=fonts["body"], height=32, corner_radius=6,
            placeholder_text="Puxa do template"
        ).pack(fill="x", pady=(0, 12))

        # Dynamic Form
        self.dynamic_form = DynamicForm(self.form_scroll, template=None, on_change=self._on_extra_fields_change)
        self.dynamic_form.pack(fill="x", pady=(0, 12))

    def _load_first_nr(self):
        from src.core.template_loader import list_available_nrs
        nrs = list_available_nrs()
        if nrs:
            self._on_nr_selected(nrs[0])

    def _on_nr_selected(self, nr_code: str):
        fonts = get_fonts()
        self.selected_nr = nr_code
        self.current_template = load_nr_template(nr_code)

        if self.current_template:
            self.lbl_nr_title.configure(text=f"{self.current_template.nr_code} - {self.current_template.nr_name}")
            self.lbl_nr_desc.configure(text=f"Carga minima: {self.current_template.carga_horaria_minima}h | Validade: {self.current_template.validade_meses} meses")
            self.desc_var.set(self.current_template.descricao_padrao)
            self.carga_var.set(str(self.current_template.carga_horaria_minima))
            self.dynamic_form.set_template(self.current_template)

            # Riscos badges
            for w in self.riscos_frame.winfo_children():
                w.destroy()
            riscos = getattr(self.current_template, 'riscos', [])
            if riscos:
                ctk.CTkLabel(self.riscos_frame, text="Riscos:", font=fonts["small_bold"], text_color=COLORS["text"]).pack(side="left", padx=(0, 4))
                for r in riscos:
                    badge = ctk.CTkLabel(
                        self.riscos_frame, text=r,
                        font=fonts["tiny"], text_color=COLORS["surface"],
                        fg_color=COLORS["warning"], corner_radius=8,
                        padx=6, pady=2
                    )
                    badge.pack(side="left", padx=2)

            self._update_preview()

    def _on_employee_selected(self, employee: Employee):
        self.selected_employee = employee
        self.cpf_var.set(employee.cpf or "")
        has_cpf = bool(employee.cpf and employee.cpf.strip())
        self.btn_generate.configure(
            state="normal" if has_cpf else "disabled",
            fg_color=COLORS["success"] if has_cpf else COLORS["muted"]
        )
        if not has_cpf:
            self.btn_generate.configure(text="CPF obrigatório")
        else:
            self.btn_generate.configure(text="Gerar Certificado")
        self._update_preview()

    def preload_employee_by_id(self, emp_id: int):
        """Pre-seleciona um funcionario (acao 'Emitir' dos cards de Vencimentos)."""
        try:
            emp = self.employee_repo.get_by_id(emp_id)
        except Exception:
            emp = None
        if not emp:
            return
        self.employee_autocomplete.set_employee(emp)
        self._on_employee_selected(emp)

    def _on_extra_fields_change(self, values: dict):
        self._update_preview()

    def _on_preview(self):
        self._update_preview()

    def _on_pdf_preview(self):
        if not self._validate_form():
            return
        try:
            from src.utils.validators import validar_data
            from src.utils.paths import get_data_dir
            data_treinamento = validar_data(self.data_var.get())
            carga = int(self.carga_var.get())

            preview_dir = get_data_dir() / "_previews"
            preview_dir.mkdir(exist_ok=True)

            preview_filename = f"preview_{self.selected_employee.nome.replace(' ', '_')}_{data_treinamento.strftime('%Y%m%d')}.pdf"
            pdf_path = preview_dir / preview_filename

            pdf_path = self.certificate_service.generate_preview_pdf(
                nr_code=self.selected_nr,
                employee=self.selected_employee,
                data_treinamento=data_treinamento,
                carga_horaria=carga,
                descricao_treinamento=self.desc_var.get(),
                campos_extra=self.dynamic_form.get_values(),
                output_path=pdf_path
            )

            if pdf_path and pdf_path.exists():
                self.preview.show_pdf_image(str(pdf_path))
            else:
                self._show_error("Erro ao gerar preview do PDF.")
        except Exception as e:
            self._show_error(f"Erro: {e}")

    def _update_preview(self):
        if not self.selected_nr or not self.current_template:
            self.preview.set_content("Selecione um NR.")
            return
        if not self.selected_employee:
            self.preview.set_content("Selecione um funcionario.")
            return
        if not self.selected_employee.cpf or not self.selected_employee.cpf.strip():
            self.preview.set_content(
                "Funcionario sem CPF cadastrado.\n\n"
                "Edite o funcionario para adicionar o CPF antes de emitir o certificado."
            )
            return

        try:
            from src.utils.validators import validar_data
            data_treinamento = validar_data(self.data_var.get())
            carga = int(self.carga_var.get()) if self.carga_var.get().isdigit() else 0

            if not data_treinamento:
                self.preview.set_content("Preencha a data (DD/MM/AAAA).")
                return

            cert_data = self.certificate_service.get_certificate_data_for_preview(
                nr_code=self.selected_nr,
                employee=self.selected_employee,
                data_treinamento=data_treinamento,
                carga_horaria=carga,
                descricao_treinamento=self.desc_var.get(),
                campos_extra=self.dynamic_form.get_values()
            )

            if cert_data:
                preview_text = self._format_preview(cert_data, self.current_template)
                self.preview.set_content(preview_text)
            else:
                self.preview.set_content("Erro ao gerar preview.")
        except Exception as e:
            self.preview.set_content(f"Erro: {e}")

    def _format_preview(self, data, template) -> str:
        lines = [
            f"{'='*60}",
            f"     CERTIFICADO - {data.nr_code}",
            f"{'='*60}",
            f"",
            f"Funcionario: {data.funcionario_nome}",
            f"CPF: {data.funcionario_cpf}",
            f"Empresa: {data.empresa_nome}",
            f"CNPJ: {data.empresa_cnpj}",
            f"Local: {data.local_treinamento}",
            f"Instrutor: {data.instrutor_nome}",
            f"Registro MTE: {data.instrutor_registro_mte}",
            f"Data: {data.data_treinamento.strftime('%d/%m/%Y')}",
            f"Carga: {data.carga_horaria}h",
            f"Descricao: {data.descricao_treinamento}",
            f"",
            f"{'-'*60}",
            f"CONTEUDO PROGRAMATICO:",
            f"{'-'*60}",
        ]
        for item in data.conteudo_programatico:
            lines.append(f"  {item}")

        lines.extend([
            f"",
            f"{'-'*60}",
            f"ASSINATURAS:",
            f"{'-'*60}",
            f"  Instrutor/Responsavel Tecnico    |    Participante",
        ])

        return "\n".join(lines)

    def _on_generate(self):
        if not self._validate_form():
            return

        fonts = get_fonts()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirmar")
        dialog.geometry("420x200")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 210
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 100
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            dialog, text="Gerar Certificado?",
            font=fonts["heading"], text_color=COLORS["primary"]
        ).pack(pady=(20, 8))
        ctk.CTkLabel(
            dialog,
            text=f"Deseja gerar o certificado para\n{self.selected_employee.nome}?",
            font=fonts["body"], text_color=COLORS["text"], wraplength=380, justify="center"
        ).pack(pady=(0, 16))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30)

        def confirm():
            dialog.destroy()
            self._do_generate()

        def cancel():
            dialog.destroy()

        ctk.CTkButton(
            btn_frame, text="Cancelar", font=fonts["body_bold"], height=36,
            fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
            command=cancel
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_frame, text="Confirmar", font=fonts["body_bold"], height=36,
            fg_color=COLORS["success"], hover_color="#256B28",
            command=confirm
        ).pack(side="right")

    def _do_generate(self):
        try:
            from src.utils.validators import validar_data
            data_treinamento = validar_data(self.data_var.get())
            carga = int(self.carga_var.get())

            pdf_path = self.certificate_service.generate_certificate(
                nr_code=self.selected_nr,
                employee=self.selected_employee,
                data_treinamento=data_treinamento,
                carga_horaria=carga,
                descricao_treinamento=self.desc_var.get(),
                campos_extra=self.dynamic_form.get_values()
            )

            if pdf_path:
                self._show_success_dialog(pdf_path)
                self._clear_form()
            else:
                self._show_error("Erro ao gerar PDF.")
        except Exception as e:
            self._show_error(f"Erro: {e}")

    def _on_view_pdf(self):
        if not self._validate_form():
            return

        try:
            from src.utils.validators import validar_data
            data_treinamento = validar_data(self.data_var.get())
            carga = int(self.carga_var.get())

            from src.utils.paths import get_data_dir
            preview_dir = get_data_dir() / "_previews"
            preview_dir.mkdir(exist_ok=True)

            preview_filename = f"preview_{self.selected_employee.nome.replace(' ', '_')}_{data_treinamento.strftime('%Y%m%d')}.pdf"
            pdf_path = preview_dir / preview_filename

            pdf_path = self.certificate_service.generate_preview_pdf(
                nr_code=self.selected_nr,
                employee=self.selected_employee,
                data_treinamento=data_treinamento,
                carga_horaria=carga,
                descricao_treinamento=self.desc_var.get(),
                campos_extra=self.dynamic_form.get_values(),
                output_path=pdf_path
            )

            if not pdf_path:
                self._show_error("Erro ao gerar PDF para visualizacao.")
                return

            if sys.platform == "win32":
                os.startfile(str(pdf_path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(pdf_path)])
            else:
                subprocess.run(["xdg-open", str(pdf_path)])

            fonts = get_fonts()
            dialog = ctk.CTkToplevel(self)
            dialog.title("Salvar Certificado")
            dialog.geometry("420x200")
            dialog.transient(self)
            dialog.grab_set()
            dialog.resizable(False, False)

            dialog.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 210
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 100
            dialog.geometry(f"+{x}+{y}")

            ctk.CTkLabel(dialog, text="Salvar este certificado?", font=fonts["heading"], text_color=COLORS["primary"]).pack(pady=(20, 8))
            ctk.CTkLabel(dialog, text=pdf_path.name, font=fonts["body"], text_color=COLORS["text"], wraplength=380).pack(pady=(0, 16))

            btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            btn_frame.pack(fill="x", padx=30)

            def confirm_save():
                final_dir = get_data_dir()
                final_path = final_dir / pdf_path.name
                if pdf_path.exists():
                    import shutil
                    shutil.move(str(pdf_path), str(final_path))

                pdf_path_real = self.certificate_service.generate_certificate(
                    nr_code=self.selected_nr,
                    employee=self.selected_employee,
                    data_treinamento=data_treinamento,
                    carga_horaria=carga,
                    descricao_treinamento=self.desc_var.get(),
                    campos_extra=self.dynamic_form.get_values()
                )

                if pdf_path_real:
                    try:
                        preview_dir.rmdir()
                    except OSError:
                        pass
                    self._show_success_dialog(pdf_path_real)
                    self._clear_form()
                dialog.destroy()

            def cancel_and_delete():
                if pdf_path.exists():
                    pdf_path.unlink()
                try:
                    preview_dir.rmdir()
                except OSError:
                    pass
                dialog.destroy()

            ctk.CTkButton(btn_frame, text="Cancelar", font=fonts["body_bold"], height=36, fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"], command=cancel_and_delete).pack(side="left", padx=(0, 8))
            ctk.CTkButton(btn_frame, text="Salvar", font=fonts["body_bold"], height=36, fg_color=COLORS["success"], hover_color="#256B28", command=confirm_save).pack(side="right")

        except Exception as e:
            self._show_error(f"Erro: {e}")

    def _validate_form(self) -> bool:
        errors = []
        if not self.selected_nr:
            errors.append("Selecione um NR")
        if not self.selected_employee:
            errors.append("Selecione um funcionario")
        elif not self.selected_employee.cpf or not self.selected_employee.cpf.strip():
            errors.append("Funcionario sem CPF cadastrado. Edite o funcionario para adicionar o CPF.")
        if not self.data_var.get().strip():
            errors.append("Data obrigatoria")
        if not self.carga_var.get().strip().isdigit() or int(self.carga_var.get()) <= 0:
            errors.append("Carga horaria invalida")
        if not self.desc_var.get().strip():
            errors.append("Descricao obrigatoria")

        valid, extra_errors = self.dynamic_form.validate()
        if not valid:
            errors.extend(extra_errors)

        if errors:
            self._show_error("\n".join(errors))
            return False
        return True

    def _clear_form(self):
        self.employee_autocomplete.clear()
        self.cpf_var.set("")
        self.data_var.set(formatar_data(hoje()))
        self.carga_var.set(str(self.current_template.carga_horaria_minima if self.current_template else 8))
        self.desc_var.set(self.current_template.descricao_padrao if self.current_template else "")
        self.dynamic_form.clear()
        self.preview.set_content("Certificado gerado! Preencha para o proximo.")

    def _show_success_dialog(self, pdf_path):
        fonts = get_fonts()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Sucesso")
        dialog.geometry("400x180")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        ctk.CTkLabel(dialog, text="Certificado Gerado!", font=fonts["heading"], text_color=COLORS["success"]).pack(pady=16)
        ctk.CTkLabel(dialog, text=f"Salvo em:\n{pdf_path.name}", font=fonts["body"], wraplength=350).pack(pady=8)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy, fg_color=COLORS["primary"]).pack(pady=16)

    def _show_error(self, message: str):
        fonts = get_fonts()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Erro")
        dialog.geometry("400x160")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        ctk.CTkLabel(dialog, text="Erro", font=fonts["heading"], text_color=COLORS["error"]).pack(pady=16)
        ctk.CTkLabel(dialog, text=message, font=fonts["body"], wraplength=350, justify="center").pack(pady=8)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy, fg_color=COLORS["error"]).pack(pady=16)
