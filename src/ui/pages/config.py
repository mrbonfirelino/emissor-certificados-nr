import customtkinter as ctk
from tkinter import messagebox
from src.ui.styles import COLORS, get_fonts, get_font_scale, save_font_scale
from src.core.config import load_company_config, save_company_config, set_restore_password, has_restore_password
from src.core.models import CompanyConfig
from src.core.app_settings import load_app_settings, save_app_settings
from src.utils.validators import validar_cnpj, formatar_cnpj, validar_registro_mte, formatar_registro_mte
from src.ui.components.collapsible_section import CollapsibleSection


class ConfigPage(ctk.CTkFrame):
    def __init__(self, master, on_config_saved: callable = None, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.on_config_saved = on_config_saved
        self.config = load_company_config()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()
        self._load_config()
        self._refresh_log()

    def _refresh_log(self):
        from src.utils.error_log import read_log_tail
        text = read_log_tail()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        if text:
            self.log_box.insert("1.0", text)
        else:
            self.log_box.insert("1.0", "(nenhum erro registrado)")
        self.log_box.configure(state="disabled")

    def _limpar_log(self):
        if not messagebox.askyesno("Limpar log", "Apagar todo o conteúdo do log de erros?", parent=self):
            return
        from src.utils.error_log import clear_log
        if clear_log():
            self._refresh_log()
        else:
            messagebox.showerror("Erro", "Não foi possível limpar o log.", parent=self)

    def _abrir_pasta_dados(self):
        import os
        import sys
        from src.utils.paths import get_data_dir
        pasta = str(get_data_dir())
        try:
            if sys.platform == "win32":
                os.startfile(pasta)
            else:
                import subprocess
                subprocess.run(["xdg-open", pasta])
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{e}", parent=self)

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

        # ── Secao 1: Dados da Empresa (aberta por padrao) ──
        sec_empresa = CollapsibleSection(form, "Dados da Empresa", aberta=True)
        sec_empresa.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1
        emp = sec_empresa.content

        ctk.CTkLabel(emp, text="Nome da Empresa *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.empresa_var = ctk.StringVar()
        ctk.CTkEntry(emp, textvariable=self.empresa_var, font=fonts["body"], height=36, corner_radius=6).grid(row=1, column=0, sticky="ew", pady=(0, 16))

        ctk.CTkLabel(emp, text="CNPJ *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.cnpj_var = ctk.StringVar()
        self.cnpj_entry = ctk.CTkEntry(emp, textvariable=self.cnpj_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="00.000.000/0000-00")
        self.cnpj_entry.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        self.cnpj_entry.bind("<FocusOut>", self._format_cnpj_on_focus_out)

        ctk.CTkLabel(emp, text="Local do Treinamento *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.local_var = ctk.StringVar()
        ctk.CTkEntry(emp, textvariable=self.local_var, font=fonts["body"], height=36, corner_radius=6).grid(row=5, column=0, sticky="ew", pady=(0, 16))

        ctk.CTkLabel(emp, text="Instrutor Responsavel *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=6, column=0, sticky="w", pady=(0, 4))
        self.instrutor_var = ctk.StringVar()
        ctk.CTkEntry(emp, textvariable=self.instrutor_var, font=fonts["body"], height=36, corner_radius=6).grid(row=7, column=0, sticky="ew", pady=(0, 16))

        ctk.CTkLabel(emp, text="Registro MTE do Instrutor *", font=fonts["body_bold"], text_color=COLORS["text"]).grid(row=8, column=0, sticky="w", pady=(0, 4))
        self.registro_var = ctk.StringVar()
        self.registro_entry = ctk.CTkEntry(emp, textvariable=self.registro_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="44633/RJ")
        self.registro_entry.grid(row=9, column=0, sticky="ew", pady=(0, 4))
        self.registro_var.trace_add("write", self._format_registro)

        # ── Secao 2: Seguranca (senha de restauracao) ──
        sec_seguranca = CollapsibleSection(form, "Segurança")
        sec_seguranca.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1
        seg = sec_seguranca.content

        ctk.CTkLabel(seg, text="Senha de Restauracao de Backup", font=fonts["body_bold"], text_color=COLORS["primary"]).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkLabel(seg, text="Necessaria para restaurar backups. Guarde em local seguro.", font=fonts["small"], text_color=COLORS["muted"]).grid(row=1, column=0, sticky="w", pady=(0, 12))

        self.restore_pass_var = ctk.StringVar()
        ctk.CTkEntry(seg, textvariable=self.restore_pass_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="Nova senha (deixe vazio para nao alterar)", show="*").grid(row=2, column=0, sticky="ew", pady=(0, 8))

        self.restore_confirm_var = ctk.StringVar()
        ctk.CTkEntry(seg, textvariable=self.restore_confirm_var, font=fonts["body"], height=36, corner_radius=6, placeholder_text="Confirmar senha", show="*").grid(row=3, column=0, sticky="ew", pady=(0, 12))

        if has_restore_password():
            ctk.CTkLabel(seg, text="Senha de restauracao ja configurada", font=fonts["small"], text_color=COLORS["success"]).grid(row=4, column=0, sticky="w", pady=(0, 6))
        else:
            ctk.CTkLabel(seg, text="Senha de restauracao NAO configurada", font=fonts["small"], text_color=COLORS["warning"]).grid(row=4, column=0, sticky="w", pady=(0, 6))

        # ── Secao 3: Aparencia e notificacoes ──
        sec_aparencia = CollapsibleSection(form, "Aparência e Notificações")
        sec_aparencia.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1
        apa = sec_aparencia.content

        ctk.CTkLabel(apa, text="Ajuste o tamanho do texto da interface", font=fonts["small"], text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w", pady=(0, 12))

        font_frame = ctk.CTkFrame(apa, fg_color="transparent")
        font_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))

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

        self._notificacoes_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            apa, text="Notificacoes do Windows (aviso de emissao, backup e importacao)",
            variable=self._notificacoes_var,
            font=fonts["body"], text_color=COLORS["text"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            checkbox_height=20, checkbox_width=20
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))

        # ── Secao 4: Backups ──
        sec_backups = CollapsibleSection(form, "Backups")
        sec_backups.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1
        bak = sec_backups.content

        ctk.CTkLabel(bak, text="Backup periodico enquanto o programa estiver aberto (alem do semanal)",
                     font=fonts["small"], text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w", pady=(0, 12))

        backup_frame = ctk.CTkFrame(bak, fg_color="transparent")
        backup_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(backup_frame, text="Intervalo (minutos):", font=fonts["body"],
                     text_color=COLORS["text"]).pack(side="left", padx=(0, 8))
        self._backup_interval_var = ctk.StringVar(value="15")
        interval_entry = ctk.CTkEntry(backup_frame, textvariable=self._backup_interval_var,
                                      width=70, height=32, font=fonts["body"], corner_radius=6)
        interval_entry.pack(side="left")

        self._backup_duplo_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            bak, text="Backup externo (copias em Documentos\\NormaTech-Backup e C:\\NormaTech-Backup)",
            variable=self._backup_duplo_var,
            font=fonts["body"], text_color=COLORS["text"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            checkbox_height=20, checkbox_width=20
        ).grid(row=2, column=0, sticky="w", pady=(0, 8))

        self._backup_rede_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            bak, text="Backup em rede (drive mapeado — pula com aviso se o drive estiver fora)",
            variable=self._backup_rede_var,
            font=fonts["body"], text_color=COLORS["text"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            checkbox_height=20, checkbox_width=20
        ).grid(row=3, column=0, sticky="w", pady=(0, 6))

        rede_frame = ctk.CTkFrame(bak, fg_color="transparent")
        rede_frame.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkLabel(rede_frame, text="Caminho na rede:", font=fonts["body"],
                     text_color=COLORS["text"]).pack(side="left", padx=(0, 8))
        self._backup_rede_path_var = ctk.StringVar(value=r"Z:\SEGURANÇA\NORMATECH-BACKUP")
        ctk.CTkEntry(rede_frame, textvariable=self._backup_rede_path_var,
                     font=fonts["body"], height=32, corner_radius=6
                     ).pack(side="left", fill="x", expand=True)

        # Tarefa agendada do Windows (backup diario headless — item 2.19)
        self._task_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            bak, text="Tarefa Agendada do Windows (backup diário com o programa fechado)",
            variable=self._task_var, font=fonts["body"], text_color=COLORS["text"],
            progress_color=COLORS["primary"], switch_height=22, switch_width=42
        ).grid(row=5, column=0, sticky="w", pady=(2, 6))

        task_frame = ctk.CTkFrame(bak, fg_color="transparent")
        task_frame.grid(row=6, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkLabel(task_frame, text="Horário (HH:MM):", font=fonts["body"],
                     text_color=COLORS["text"]).pack(side="left", padx=(0, 8))
        self._task_hora_var = ctk.StringVar(value="12:00")
        ctk.CTkEntry(task_frame, textvariable=self._task_hora_var,
                     width=70, height=32, font=fonts["body"], corner_radius=6
                     ).pack(side="left")
        self._task_status_lbl = ctk.CTkLabel(
            task_frame, text="Tarefa inativa", font=fonts["small"],
            text_color=COLORS["muted"]
        )
        self._task_status_lbl.pack(side="left", padx=(16, 0))

        # ── Secao 5: Documentos em Rede ──
        sec_rede = CollapsibleSection(form, "Documentos em Rede")
        sec_rede.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1
        red = sec_rede.content

        ctk.CTkLabel(red, text="Copia de certificados, cartoes, assinados e outros documentos em pastas por funcionario.",
                     font=fonts["small"], text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w", pady=(0, 12))

        self._rede_docs_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            red, text="Salvar copia dos documentos em pasta de rede",
            variable=self._rede_docs_var,
            font=fonts["body"], text_color=COLORS["text"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            checkbox_height=20, checkbox_width=20
        ).grid(row=1, column=0, sticky="w", pady=(0, 6))

        rede_docs_frame = ctk.CTkFrame(red, fg_color="transparent")
        rede_docs_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        rede_docs_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(rede_docs_frame, text="Caminho na rede:", font=fonts["body"],
                     text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._rede_docs_path_var = ctk.StringVar(value="")
        ctk.CTkEntry(rede_docs_frame, textvariable=self._rede_docs_path_var,
                     font=fonts["body"], height=32, corner_radius=6
                     ).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ctk.CTkButton(rede_docs_frame, text="Procurar...", width=90, height=32,
                      font=fonts["small"], fg_color=COLORS["muted"],
                      hover_color=COLORS["text_secondary"],
                      command=self._procurar_rede_docs).grid(row=0, column=2)

        ctk.CTkLabel(
            red,
            text="Estrutura: {Funcionario}/Certificados/{NR} (vencidos em 00_Certificados_OLD), "
                 "Cartoes, Certificados Assinados e Outros; lotes em Cartoes_Gerais.",
            font=fonts["small"], text_color=COLORS["muted"], wraplength=520, justify="left"
        ).grid(row=3, column=0, sticky="w", pady=(0, 8))

        ctk.CTkButton(
            red, text="Sincronizar Agora", width=140, height=32,
            font=fonts["body_bold"], fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
            command=self._sincronizar_agora
        ).grid(row=4, column=0, sticky="w", pady=(0, 4))

        # ── Secao 6: Diagnostico — Log de erros ──
        sec_diag = CollapsibleSection(form, "Diagnóstico — Log de Erros")
        sec_diag.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1
        dia = sec_diag.content

        ctk.CTkLabel(dia, text="Últimos erros capturados pelo programa (data/error.log).",
                     font=fonts["small"], text_color=COLORS["muted"]).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.log_box = ctk.CTkTextbox(
            dia, height=180, font=fonts["mono"],
            fg_color=COLORS["background"], corner_radius=6,
            text_color=COLORS["text_secondary"]
        )
        self.log_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        log_btns = ctk.CTkFrame(dia, fg_color="transparent")
        log_btns.grid(row=2, column=0, sticky="w", pady=(0, 6))

        ctk.CTkButton(
            log_btns, text="Atualizar", width=90, height=30,
            font=fonts["small"], fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"], command=self._refresh_log
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            log_btns, text="Limpar", width=80, height=30,
            font=fonts["small"], fg_color=COLORS["error"],
            hover_color="#8E1E1E", command=self._limpar_log
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            log_btns, text="Abrir Pasta", width=96, height=30,
            font=fonts["small"], fg_color=COLORS["muted"],
            hover_color=COLORS["text_secondary"], command=self._abrir_pasta_dados
        ).pack(side="left")

        # Botao salvar (fixo no rodape)
        ctk.CTkButton(
            form, text="Salvar Configuracao",
            font=fonts["body_bold"], height=40,
            fg_color=COLORS["success"], hover_color="#256B28",
            command=self._save_config
        ).grid(row=row, column=0, sticky="e", pady=(12, 0))

    def _procurar_rede_docs(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Pasta de rede para os documentos", parent=self)
        if path:
            self._rede_docs_path_var.set(path)

    def _sincronizar_agora(self):
        if not self._rede_docs_var.get():
            messagebox.showwarning("Aviso", "Ative o salvamento em rede antes de sincronizar.", parent=self)
            return
        caminho = self._rede_docs_path_var.get().strip()
        if not caminho:
            messagebox.showwarning("Aviso", "Informe o caminho na rede.", parent=self)
            return
        import threading
        from src.core import network_sync
        from src.core.app_settings import set_setting
        set_setting("rede_documentos_ativo", True)
        set_setting("rede_documentos_caminho", caminho)
        messagebox.showinfo("Sincronizacao", "Sincronizacao iniciada em segundo plano.\n"
                            "Voce recebera uma notificacao ao terminar.", parent=self)
        threading.Thread(
            target=network_sync.sync_all, kwargs={"notify_success": True}, daemon=True
        ).start()

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
        self._backup_rede_var.set(bool(settings.get("backup_rede_ativo", True)))
        self._backup_rede_path_var.set(str(settings.get(
            "backup_rede_caminho", r"Z:\SEGURANÇA\NORMATECH-BACKUP")))
        self._rede_docs_var.set(bool(settings.get("rede_documentos_ativo", False)))
        self._rede_docs_path_var.set(str(settings.get("rede_documentos_caminho", "") or ""))
        self._task_var.set(bool(settings.get("tarefa_agendada_ativo", False)))
        self._task_hora_var.set(str(settings.get("tarefa_agendada_hora", "12:00") or "12:00"))
        self._refresh_task_status()

    def _refresh_task_status(self):
        """Indica na UI se a tarefa agendada do Windows esta ativa."""
        try:
            from src.core.scheduled_task import is_active
            ativa = is_active()
        except Exception:
            ativa = False
        self._task_status_lbl.configure(
            text="Tarefa ativa — backup diário" if ativa else "Tarefa inativa",
            text_color=COLORS["success"] if ativa else COLORS["muted"],
        )

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
        task_hora = self._task_hora_var.get().strip() or "12:00"
        task_ativo = bool(self._task_var.get())
        if task_ativo:
            from src.core.scheduled_task import validar_hora
            if not validar_hora(task_hora):
                messagebox.showerror("Erro", "Horário da tarefa agendada inválido (use HH:MM, 24h)", parent=self)
                return
        app_settings = {
            "notificacoes_ativas": bool(self._notificacoes_var.get()),
            "backup_intervalo_min": intervalo,
            "backup_duplo": bool(self._backup_duplo_var.get()),
            "backup_rede_ativo": bool(self._backup_rede_var.get()),
            "backup_rede_caminho": self._backup_rede_path_var.get().strip()
                                   or r"Z:\SEGURANÇA\NORMATECH-BACKUP",
            "rede_documentos_ativo": bool(self._rede_docs_var.get()),
            "rede_documentos_caminho": self._rede_docs_path_var.get().strip(),
            "tarefa_agendada_ativo": task_ativo,
            "tarefa_agendada_hora": task_hora,
        }
        save_app_settings(app_settings)

        # aplica (registra/remove) a tarefa agendada do Windows
        try:
            from src.core import scheduled_task
            if task_ativo:
                if not scheduled_task.register(task_hora):
                    messagebox.showwarning(
                        "Aviso", "Não foi possível registrar a tarefa agendada do Windows.", parent=self)
            elif scheduled_task.is_active():
                scheduled_task.remove()
            self._refresh_task_status()
        except Exception:
            messagebox.showwarning("Aviso", "Erro ao aplicar a tarefa agendada.", parent=self)

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
