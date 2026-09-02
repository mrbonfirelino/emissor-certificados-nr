import customtkinter as ctk
from tkinter import messagebox
from src.ui.styles import COLORS, get_fonts, get_font_scale, save_font_scale
from src.core.config import load_company_config, save_company_config, set_restore_password, has_restore_password
from src.core.models import CompanyConfig
from src.core.app_settings import load_app_settings, save_app_settings
from src.utils.validators import validar_cnpj, formatar_cnpj, validar_registro_mte, formatar_registro_mte


class ConfigPage(ctk.CTkFrame):
    def __init__(self, master, on_config_saved: callable = None, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.on_config_saved = on_config_saved
        self.config = load_company_config()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()
        self._load_config()

    def _build_ui(self):
        fonts = get_fonts()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)

        ctk.CTkLabel(
            header, text="Configurações do programa",
            font=fonts["title"], text_color=COLORS["primary"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Dados para os certificados e configurações gerais.",
            font=fonts["body"], text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(4, 0))

        form_card = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"], corner_radius=12)
        form_card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        form_card.grid_columnconfigure(0, weight=1)

        form = ctk.CTkFrame(form_card, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=30, pady=30)
        form.grid_columnconfigure(0, weight=1)

        row = 0

        # Empresa
        ctk.CTkLabel(form, text="Nome da Empresa *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.empresa_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.empresa_var, font=fonts["body"], height=36, corner_radius=6).grid(row=row+1, column=0, sticky="ew", pady=(0, 16))
        row += 2

        # CNPJ
        ctk.CTkLabel(form, text="CNPJ *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.cnpj_var = ctk.StringVar()
        self.cnpj_entry = ctk.CTkEntry(form, textvariable=self.cnpj_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="00.000.000/0000-00")
        self.cnpj_entry.grid(row=row+1, column=0, sticky="ew", pady=(0, 16))
        self.cnpj_entry.bind("<FocusOut>", self._format_cnpj_on_focus_out)
        row += 2

        # Local
        ctk.CTkLabel(form, text="Local do Treinamento *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.local_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.local_var, font=fonts["body"], height=36, corner_radius=6).grid(row=row+1, column=0, sticky="ew", pady=(0, 16))
        row += 2

        # Instrutor
        ctk.CTkLabel(form, text="Instrutor Responsavel *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.instrutor_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.instrutor_var, font=fonts["body"], height=36, corner_radius=6).grid(row=row+1, column=0, sticky="ew", pady=(0, 16))
        row += 2

        # Registro MTE
        ctk.CTkLabel(form, text="Registro MTE do Instrutor *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.registro_var = ctk.StringVar()
        self.registro_entry = ctk.CTkEntry(form, textvariable=self.registro_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="44633/RJ")
        self.registro_entry.grid(row=row+1, column=0, sticky="ew", pady=(0, 16))
        self.registro_var.trace_add("write", self._format_registro)
        row += 2

        # Separador
        ctk.CTkFrame(form, height=2, fg_color=COLORS["border"]).grid(row=row, column=0, sticky="ew", pady=20)
        row += 1

        # Senha de restauracao
        ctk.CTkLabel(form, text="Senha de Restauracao de Backup", font=fonts["heading"], text_color=COLORS["primary"]).grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1
        ctk.CTkLabel(form, text="Necessaria para restaurar backups. Guarde em local seguro.", font=fonts["small"], text_color=COLORS["muted"]).grid(row=row, column=0, sticky="w", pady=(0, 16))
        row += 1

        self.restore_pass_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.restore_pass_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="Nova senha (deixe vazio para nao alterar)", show="*").grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        self.restore_confirm_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.restore_confirm_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="Confirmar senha", show="*").grid(row=row, column=0, sticky="ew", pady=(0, 12))
        row += 1

        if has_restore_password():
            ctk.CTkLabel(form, text="Senha de restauracao ja configurada", font=fonts["small"], text_color=COLORS["success"]).grid(row=row, column=0, sticky="w", pady=(0, 16))
        else:
            ctk.CTkLabel(form, text="Senha de restauracao NAO configurada", font=fonts["small"], text_color=COLORS["warning"]).grid(row=row, column=0, sticky="w", pady=(0, 16))
        row += 1

        # Separador
        ctk.CTkFrame(form, height=2, fg_color=COLORS["border"]).grid(row=row, column=0, sticky="ew", pady=20)
        row += 1

        # Tamanho da fonte
        ctk.CTkLabel(form, text="Tamanho da Fonte", font=fonts["heading"], text_color=COLORS["primary"]).grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1
        ctk.CTkLabel(form, text="Ajuste o tamanho do texto da interface", font=fonts["small"], text_color=COLORS["muted"]).grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1

        font_frame = ctk.CTkFrame(form, fg_color="transparent")
        font_frame.grid(row=row, column=0, sticky="ew", pady=(0, 20))
        row += 1

        self.font_scale_var = ctk.DoubleVar(value=get_font_scale())

        self.btn_font_down = ctk.CTkButton(
            font_frame, text="A-", font=("Segoe UI", 14, "bold"),
            width=40, height=36, fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"],
            command=lambda: self._change_font_scale(-0.1)
        )
        self.btn_font_down.pack(side="left", padx=(0, 8))

        self.font_scale_label = ctk.CTkLabel(
            font_frame, text=f"{self.font_scale_var.get():.0%}",
            font=("Segoe UI", 12, "bold"), text_color=COLORS["text"]
        )
        self.font_scale_label.pack(side="left", padx=(0, 8))

        self.btn_font_up = ctk.CTkButton(
            font_frame, text="A+", font=("Segoe UI", 14, "bold"),
            width=40, height=36, fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"],
            command=lambda: self._change_font_scale(0.1)
        )
        self.btn_font_up.pack(side="left", padx=(0, 12))

        self.btn_font_reset = ctk.CTkButton(
            font_frame, text="Resetar", font=fonts["small"],
            width=60, height=30, fg_color=COLORS["muted"],
            hover_color=COLORS["text_secondary"],
            command=lambda: self._set_font_scale(1.0)
        )
        self.btn_font_reset.pack(side="left")

        # Separador
        ctk.CTkFrame(form, height=2, fg_color=COLORS["border"]).grid(row=row, column=0, sticky="ew", pady=20)
        row += 1

        # Preferencias (notificacoes)
        ctk.CTkLabel(form, text="Preferencias", font=fonts["heading"], text_color=COLORS["primary"]).grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        self._notificacoes_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            form, text="Notificacoes do Windows (aviso de emissao, backup e importacao)",
            variable=self._notificacoes_var,
            font=fonts["body"], text_color=COLORS["text"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            checkbox_height=20, checkbox_width=20
        ).grid(row=row, column=0, sticky="w", pady=(0, 16))
        row += 1

        # Separador
        ctk.CTkFrame(form, height=2, fg_color=COLORS["border"]).grid(row=row, column=0, sticky="ew", pady=20)
        row += 1

        # Backups
        ctk.CTkLabel(form, text="Backups", font=fonts["heading"], text_color=COLORS["primary"]).grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1
        ctk.CTkLabel(form, text="Backup periodico enquanto o programa estiver aberto (alem do semanal)",
                     font=fonts["small"], text_color=COLORS["muted"]).grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1

        backup_frame = ctk.CTkFrame(form, fg_color="transparent")
        backup_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        ctk.CTkLabel(backup_frame, text="Intervalo (minutos):", font=fonts["body"],
                     text_color=COLORS["text"]).pack(side="left", padx=(0, 8))
        self._backup_interval_var = ctk.StringVar(value="15")
        interval_entry = ctk.CTkEntry(backup_frame, textvariable=self._backup_interval_var,
                                      width=70, height=32, font=fonts["body"], corner_radius=6)
        interval_entry.pack(side="left")

        self._backup_duplo_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            form, text="Backup externo (copias em Documentos\\NormaTech-Backup e C:\\NormaTech-Backup)",
            variable=self._backup_duplo_var,
            font=fonts["body"], text_color=COLORS["text"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            checkbox_height=20, checkbox_width=20
        ).grid(row=row, column=0, sticky="w", pady=(0, 16))
        row += 1

        # Botao salvar
        ctk.CTkButton(
            form, text="Salvar Configuracao",
            font=fonts["body_bold"], height=40,
            fg_color=COLORS["success"], hover_color="#256B28",
            command=self._save_config
        ).grid(row=row, column=0, sticky="e")
        row += 1

    def _change_font_scale(self, delta):
        new_val = round(self.font_scale_var.get() + delta, 1)
        self._set_font_scale(new_val)

    def _set_font_scale(self, val):
        val = max(0.7, min(1.6, round(val, 1)))
        self.font_scale_var.set(val)
        self.font_scale_label.configure(text=f"{val:.0%}")
        save_font_scale(val)

    def _format_cnpj_on_focus_out(self, event=None):
        val = self.cnpj_var.get()
        digits = ''.join(c for c in val if c.isdigit())
        if len(digits) <= 14:
            formatted = val
            if len(digits) > 12:
                formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
            elif len(digits) > 8:
                formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:]}"
            elif len(digits) > 5:
                formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:]}"
            elif len(digits) > 2:
                formatted = f"{digits[:2]}.{digits[2:]}"
            if formatted != val:
                self.cnpj_var.set(formatted)

    def _format_registro(self, *args):
        import re
        val = self.registro_var.get().strip().upper()
        match = re.match(r'(?:MTE\s*)?(\d{1,6})\s*/?\s*([A-Z]{2})', val)
        if match:
            num = match.group(1)
            uf = match.group(2)
            self.registro_var.set(f"MTE {num}/{uf}")

    def _load_config(self):
        if self.config:
            self.empresa_var.set(self.config.empresa_nome)
            self.cnpj_var.set(self.config.empresa_cnpj)
            self.local_var.set(self.config.local_treinamento)
            self.instrutor_var.set(self.config.instrutor_nome)
            self.registro_var.set(self.config.instrutor_registro_mte)
        settings = load_app_settings()
        self._notificacoes_var.set(bool(settings.get("notificacoes_ativas", True)))
        self._backup_interval_var.set(str(settings.get("backup_intervalo_min", 15)))
        self._backup_duplo_var.set(bool(settings.get("backup_duplo", True)))

    def _save_config(self):
        empresa = self.empresa_var.get().strip()
        cnpj = self.cnpj_var.get().strip()
        local = self.local_var.get().strip()
        instrutor = self.instrutor_var.get().strip()
        registro = self.registro_var.get().strip()

        cnpj_fmt = formatar_cnpj(cnpj)
        registro_fmt = formatar_registro_mte(registro)

        if not empresa:
            messagebox.showerror("Erro", "Nome da empresa e obrigatorio", parent=self)
            return
        if not cnpj_fmt or not validar_cnpj(cnpj_fmt):
            messagebox.showerror("Erro", "CNPJ invalido", parent=self)
            return
        if not local:
            messagebox.showerror("Erro", "Local do treinamento e obrigatorio", parent=self)
            return
        if not instrutor:
            messagebox.showerror("Erro", "Nome do instrutor e obrigatorio", parent=self)
            return
        if not registro_fmt or not validar_registro_mte(registro_fmt):
            messagebox.showerror("Erro", "Registro MTE invalido (formato: 44633/RJ)", parent=self)
            return

        new_pass = self.restore_pass_var.get()
        confirm_pass = self.restore_confirm_var.get()
        if new_pass:
            if new_pass != confirm_pass:
                messagebox.showerror("Erro", "Senhas nao conferem", parent=self)
                return
            if len(new_pass) < 6:
                messagebox.showerror("Erro", "Senha deve ter pelo menos 6 caracteres", parent=self)
                return

        # preferencias do app
        try:
            intervalo = int(self._backup_interval_var.get().strip())
        except ValueError:
            messagebox.showerror("Erro", "Intervalo de backup deve ser um numero inteiro (minutos)", parent=self)
            return
        if not (1 <= intervalo <= 720):
            messagebox.showerror("Erro", "Intervalo de backup deve ficar entre 1 e 720 minutos", parent=self)
            return
        app_settings = {
            "notificacoes_ativas": bool(self._notificacoes_var.get()),
            "backup_intervalo_min": intervalo,
            "backup_duplo": bool(self._backup_duplo_var.get()),
        }
        save_app_settings(app_settings)

        try:
            config = CompanyConfig(
                empresa_nome=empresa,
                empresa_cnpj=cnpj_fmt,
                local_treinamento=local,
                instrutor_nome=instrutor,
                instrutor_registro_mte=registro_fmt
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Erro nos dados: {e}", parent=self)
            return

        if save_company_config(config):
            if new_pass:
                set_restore_password(new_pass)
            messagebox.showinfo("Sucesso", "Configuracao salva!", parent=self)
            if self.on_config_saved:
                self.on_config_saved()
        else:
            messagebox.showerror("Erro", "Erro ao salvar configuracao", parent=self)
