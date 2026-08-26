import customtkinter as ctk
from tkinter import messagebox, filedialog
from src.ui.styles import COLORS, FONTS
from src.core.backup_manager import BackupManager
from src.core.config import verify_restore_password, has_restore_password


class BackupPage(ctk.CTkFrame):
    """Página de gerenciamento de backups."""
    
    def __init__(self, master, backup_manager: BackupManager, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.backup_manager = backup_manager
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header,
            text="💾 Backup e Restauração",
            font=FONTS["title"],
            text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w")
        
        # Status backup automático
        self.lbl_auto_status = ctk.CTkLabel(
            header,
            text="Backup automático: Verificando...",
            font=FONTS["small"],
            text_color=COLORS["muted"]
        )
        self.lbl_auto_status.grid(row=0, column=1, sticky="e")
        
        # Botões ação
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        
        ctk.CTkButton(
            btn_frame,
            text="📥 Backup Manual Agora",
            font=FONTS["body_bold"],
            height=36,
            fg_color=COLORS["success"],
            hover_color="#256B28",
            command=self._manual_backup
        ).pack(side="left", padx=(0, 12))
        
        ctk.CTkButton(
            btn_frame,
            text="🔄 Restaurar Backup",
            font=FONTS["body_bold"],
            height=36,
            fg_color=COLORS["warning"],
            hover_color="#E65100",
            command=self._open_restore_dialog
        ).pack(side="left")
        
        # Lista de backups
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"], corner_radius=12)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        backups = self.backup_manager.list_backups()
        
        if not backups:
            ctk.CTkLabel(
                self.list_frame,
                text="Nenhum backup encontrado",
                font=FONTS["body"],
                text_color=COLORS["muted"]
            ).pack(pady=40)
            return
        
        # Header
        header = ctk.CTkFrame(self.list_frame, fg_color=COLORS["primary"], corner_radius=6)
        header.pack(fill="x", padx=8, pady=(8, 4))
        header.grid_columnconfigure((0,1,2), weight=1)
        
        ctk.CTkLabel(header, text="Arquivo", font=FONTS["small_bold"], text_color=COLORS["surface"]).grid(row=0, column=0, sticky="w", padx=12, pady=8)
        ctk.CTkLabel(header, text="Tipo", font=FONTS["small_bold"], text_color=COLORS["surface"]).grid(row=0, column=1, sticky="w", padx=12, pady=8)
        ctk.CTkLabel(header, text="Ações", font=FONTS["small_bold"], text_color=COLORS["surface"]).grid(row=0, column=2, sticky="e", padx=12, pady=8)
        
        for backup in backups:
            self._create_backup_row(backup)
        
        # Atualiza status automático
        from src.core.history_repo import HistoryRepository
        history = HistoryRepository()
        last = history.get_backup_meta('last_auto_backup')
        if last:
            self.lbl_auto_status.configure(
                text=f"Último backup automático: {last}",
                text_color=COLORS["success"]
            )
        else:
            self.lbl_auto_status.configure(
                text="Backup automático: Nunca executado",
                text_color=COLORS["warning"]
            )

    def _create_backup_row(self, backup_path):
        import os
        from datetime import datetime
        
        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.pack(fill="x", pady=2, padx=8)
        row.grid_columnconfigure((0,1,2), weight=1)
        
        # Nome
        name = backup_path.name
        is_auto = name.startswith("certificados_auto_")
        type_label = "Automático" if is_auto else "Manual"
        type_color = COLORS["accent"] if is_auto else COLORS["success"]
        
        ctk.CTkLabel(
            row,
            text=name,
            font=FONTS["small"],
            text_color=COLORS["text"]
        ).grid(row=0, column=0, sticky="w", padx=12, pady=8)
        
        ctk.CTkLabel(
            row,
            text=type_label,
            font=FONTS["small_bold"],
            text_color=type_color
        ).grid(row=0, column=1, sticky="w", padx=12, pady=8)
        
        # Botões
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=2, sticky="e", padx=12, pady=4)
        
        ctk.CTkButton(
            btn_frame,
            text="📁",
            width=32,
            height=32,
            font=FONTS["small"],
            fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"],
            command=lambda p=backup_path: self._open_folder(p)
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="⬇️",
            width=32,
            height=32,
            font=FONTS["small"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["secondary"],
            command=lambda p=backup_path: self._download_backup(p)
        ).pack(side="left", padx=2)

    def _manual_backup(self):
        """Cria backup manual."""
        self.btn_manual = None  # Referência para desabilitar
        # Desabilita botão temporariamente
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkButton) and "Backup Manual" in child.cget("text"):
                        child.configure(state="disabled", text="⏳ Fazendo backup...")
                        self.btn_manual = child
                        break
        
        self.update()
        
        backup_path = self.backup_manager.create_backup(auto=False)
        
        if self.btn_manual:
            self.btn_manual.configure(state="normal", text="📥 Backup Manual Agora")
        
        if backup_path:
            messagebox.showinfo("Sucesso", f"Backup criado:\n{backup_path.name}", parent=self)
            self._refresh_list()
        else:
            messagebox.showerror("Erro", "Falha ao criar backup", parent=self)

    def _open_restore_dialog(self):
        """Dialog para restaurar backup com senha."""
        backups = self.backup_manager.list_backups()
        if not backups:
            messagebox.showinfo("Aviso", "Nenhum backup disponível para restaurar", parent=self)
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Restaurar Backup")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        ctk.CTkLabel(dialog, text="⚠️ Restaurar Backup", font=FONTS["heading"], text_color=COLORS["warning"]).pack(pady=20)
        ctk.CTkLabel(dialog, text="Isso SUBSTITUIRÁ todos os dados atuais.\nOperação irreversível!", font=FONTS["body"], text_color=COLORS["error"], justify="center").pack(pady=(0, 20))
        
        # Seleção de backup
        ctk.CTkLabel(dialog, text="Selecione o backup:", font=FONTS["body_bold"]).pack(anchor="w", padx=30)
        
        backup_var = ctk.StringVar(value=backups[0].name)
        backup_combo = ctk.CTkComboBox(
            dialog,
            values=[b.name for b in backups],
            variable=backup_var,
            font=FONTS["body"],
            height=36,
            width=400
        )
        backup_combo.pack(pady=(4, 16), padx=30)
        
        # Senha
        ctk.CTkLabel(dialog, text="Senha de restauração:", font=FONTS["body_bold"]).pack(anchor="w", padx=30)
        pass_var = ctk.StringVar()
        pass_entry = ctk.CTkEntry(dialog, textvariable=pass_var, font=FONTS["body"], height=36, width=400, show="•", placeholder_text="Digite a senha")
        pass_entry.pack(pady=(4, 20), padx=30)
        
        def do_restore():
            password = pass_var.get()
            if not password:
                messagebox.showerror("Erro", "Senha é obrigatória", parent=dialog)
                return
            
            selected_name = backup_var.get()
            selected_path = next((b for b in backups if b.name == selected_name), None)
            
            if not selected_path:
                messagebox.showerror("Erro", "Backup não encontrado", parent=dialog)
                return
            
            if not verify_restore_password(password):
                messagebox.showerror("Erro", "Senha incorreta", parent=dialog)
                return
            
            # Confirmação final
            if not messagebox.askyesno(
                "CONFIRMAÇÃO FINAL",
                f"TEM CERTEZA?\n\n"
                f"Backup: {selected_name}\n"
                f"Isso APAGARÁ todos os certificados e funcionários atuais.\n"
                f"Não é possível desfazer!",
                parent=dialog
            ):
                return
            
            dialog.destroy()
            
            # Restaura
            if self.backup_manager.restore_backup(selected_path, password):
                messagebox.showinfo("Sucesso", "Backup restaurado! O programa será reiniciado.", parent=self)
                # Reinicia app
                self.quit()
            else:
                messagebox.showerror("Erro", "Falha ao restaurar backup", parent=self)
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        ctk.CTkButton(btn_frame, text="Cancelar", command=dialog.destroy, fg_color=COLORS["muted"]).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Restaurar", command=do_restore, fg_color=COLORS["error"], hover_color="#B71C1C").pack(side="left", padx=10)

    def _open_folder(self, backup_path):
        import os
        import subprocess
        import sys
        folder = backup_path.parent
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception:
            pass

    def _download_backup(self, backup_path):
        """Copia backup para local escolhido pelo usuário."""
        dest = filedialog.asksaveasfilename(
            defaultextension=".db.gz",
            filetypes=[("Backup", "*.db.gz"), ("Todos", "*.*")],
            initialfile=backup_path.name,
            title="Salvar backup como..."
        )
        if dest:
            import shutil
            try:
                shutil.copy2(backup_path, dest)
                messagebox.showinfo("Sucesso", f"Backup copiado para:\n{dest}", parent=self)
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao copiar: {e}", parent=self)