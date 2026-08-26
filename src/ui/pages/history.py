import customtkinter as ctk
import os
import subprocess
import sys
from typing import Optional
from src.ui.styles import COLORS, FONTS
from src.core.history_repo import HistoryRepository
from src.core.models import CertificateRecord


class HistoryPage(ctk.CTkFrame):
    """Página de histórico de certificados emitidos."""
    
    def __init__(self, master, history_repo: HistoryRepository, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.history_repo = history_repo
        self.selected_cert: Optional[CertificateRecord] = None
        
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
            text="📋 Histórico de Certificados",
            font=FONTS["title"],
            text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w")
        
        # Total count
        self.lbl_count = ctk.CTkLabel(
            header,
            text="Total: 0",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        self.lbl_count.grid(row=0, column=1, sticky="e")
        
        # Search + filters
        filter_frame = ctk.CTkFrame(header, fg_color="transparent")
        filter_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        filter_frame.grid_columnconfigure(1, weight=1)
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            filter_frame,
            textvariable=self.search_var,
            font=FONTS["body"],
            height=36,
            corner_radius=6,
            placeholder_text="🔍 Buscar por nome, CPF, número ou NR..."
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_var.trace_add("write", lambda *args: self._refresh_list())
        
        self.btn_clear = ctk.CTkButton(
            filter_frame,
            text="Limpar",
            width=80,
            height=36,
            font=FONTS["body"],
            fg_color=COLORS["muted"],
            hover_color=COLORS["text_secondary"],
            command=lambda: self.search_var.set("")
        )
        self.btn_clear.grid(row=0, column=1, sticky="e")
        
        # Lista
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"], corner_radius=12)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        query = self.search_var.get().strip()
        if query:
            certs = self.history_repo.search(query, limit=200)
        else:
            certs = self.history_repo.get_all(limit=200)
        
        total = self.history_repo.count_total()
        self.lbl_count.configure(text=f"Total: {total} | Exibindo: {len(certs)}")
        
        if not certs:
            ctk.CTkLabel(
                self.list_frame,
                text="Nenhum certificado emitido" if not query else "Nenhum resultado encontrado",
                font=FONTS["body"],
                text_color=COLORS["muted"]
            ).pack(pady=40)
            return
        
        # Header da tabela
        self._create_table_header()
        
        for cert in certs:
            self._create_cert_row(cert)

    def _create_table_header(self):
        header = ctk.CTkFrame(self.list_frame, fg_color=COLORS["primary"], corner_radius=6)
        header.pack(fill="x", padx=8, pady=(8, 4))
        header.grid_columnconfigure((0,1,2,3,4,5), weight=1)
        
        cols = [
            ("Número", 0), ("NR", 1), ("Funcionário", 2), 
            ("Data", 3), ("Carga", 4), ("Ações", 5)
        ]
        for text, col in cols:
            ctk.CTkLabel(
                header,
                text=text,
                font=FONTS["small_bold"],
                text_color=COLORS["surface"]
            ).grid(row=0, column=col, sticky="w", padx=12, pady=8)

    def _create_cert_row(self, cert: CertificateRecord):
        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.pack(fill="x", pady=2, padx=8)
        row.grid_columnconfigure((0,1,2,3,4,5), weight=1)
        
        # Número
        ctk.CTkLabel(
            row,
            text=cert.cert_number,
            font=FONTS["small_bold"],
            text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w", padx=12, pady=8)
        
        # NR
        ctk.CTkLabel(
            row,
            text=cert.nr_code,
            font=FONTS["small"],
            text_color=COLORS["text"]
        ).grid(row=0, column=1, sticky="w", padx=12, pady=8)
        
        # Funcionário
        ctk.CTkLabel(
            row,
            text=f"{cert.funcionario_nome} ({cert.funcionario_cpf})",
            font=FONTS["small"],
            text_color=COLORS["text"]
        ).grid(row=0, column=2, sticky="w", padx=12, pady=8)
        
        # Data
        ctk.CTkLabel(
            row,
            text=cert.data_fim,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        ).grid(row=0, column=3, sticky="w", padx=12, pady=8)
        
        # Carga
        ctk.CTkLabel(
            row,
            text=f"{cert.carga_horaria}h",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        ).grid(row=0, column=4, sticky="w", padx=12, pady=8)
        
        # Ações
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=5, sticky="e", padx=12, pady=4)
        
        ctk.CTkButton(
            btn_frame,
            text="📄",
            width=32,
            height=32,
            font=FONTS["small"],
            fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"],
            command=lambda c=cert: self._open_pdf(c)
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            btn_frame,
            text="📁",
            width=32,
            height=32,
            font=FONTS["small"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["secondary"],
            command=lambda c=cert: self._open_folder(c)
        ).pack(side="left", padx=2)

    def _open_pdf(self, cert: CertificateRecord):
        """Abre PDF do certificado."""
        if cert.pdf_path and os.path.exists(cert.pdf_path):
            try:
                if sys.platform == "win32":
                    os.startfile(cert.pdf_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", cert.pdf_path])
                else:
                    subprocess.run(["xdg-open", cert.pdf_path])
            except Exception as e:
                self._show_error(f"Erro ao abrir PDF: {e}")
        else:
            self._show_error("Arquivo PDF não encontrado")

    def _open_folder(self, cert: CertificateRecord):
        """Abre pasta do certificado."""
        if cert.pdf_path:
            folder = os.path.dirname(cert.pdf_path)
            try:
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    subprocess.run(["open", folder])
                else:
                    subprocess.run(["xdg-open", folder])
            except Exception as e:
                self._show_error(f"Erro ao abrir pasta: {e}")

    def _show_error(self, message: str):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Erro")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text=message, font=FONTS["body"], wraplength=350).pack(pady=20)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy, fg_color=COLORS["error"]).pack()