import customtkinter as ctk
import os
import subprocess
import sys
from typing import Optional
from tkinter import messagebox, filedialog
from src.ui.styles import COLORS, get_fonts
from src.core.history_repo import HistoryRepository
from src.core.models import CertificateRecord
from src.ui.components.pagination import PaginationBar


class HistoryPage(ctk.CTkFrame):

    def __init__(self, master, history_repo: HistoryRepository, **kwargs):
        super().__init__(master, fg_color=COLORS["background"], **kwargs)
        self.history_repo = history_repo
        self.selected_cert: Optional[CertificateRecord] = None

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
            self._header, text="Histórico de Emissões (Certificados)",
            font=fonts["title"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w")

        self.lbl_count = ctk.CTkLabel(
            self._header, text="Total: 0",
            font=fonts["body"], text_color=COLORS["text_secondary"]
        )
        self.lbl_count.grid(row=0, column=1, sticky="e")

        filter_frame = ctk.CTkFrame(self._header, fg_color="transparent")
        filter_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        filter_frame.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            filter_frame, textvariable=self.search_var,
            font=fonts["body"], height=36, corner_radius=6,
            placeholder_text="Buscar por nome, CPF, numero ou NR..."
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda *args: self._on_search())

        ctk.CTkButton(
            filter_frame, text="Buscar", width=80, height=36,
            font=fonts["body_bold"], fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"],
            command=self._on_search
        ).grid(row=0, column=1, sticky="e", padx=(0, 8))

        ctk.CTkButton(
            filter_frame, text="Limpar", width=80, height=36,
            font=fonts["body"], fg_color=COLORS["muted"],
            hover_color=COLORS["text_secondary"],
            command=lambda: (self.search_var.set(""), self._on_search())
        ).grid(row=0, column=2, sticky="e")

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

    def _on_search(self):
        self.pagination.reset()
        self._refresh_list()

    def _refresh_list(self):
        fonts = get_fonts()
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        query = self.search_var.get().strip()
        if query:
            total = self.history_repo.count_search(query)
            certs = self.history_repo.search(query, limit=PaginationBar.ITEMS_PER_PAGE, offset=self.pagination.offset)
        else:
            total = self.history_repo.count_all()
            certs = self.history_repo.get_all(limit=PaginationBar.ITEMS_PER_PAGE, offset=self.pagination.offset)

        self.pagination.set_total(total)
        self.lbl_count.configure(text=f"Total: {total}")

        if not certs:
            ctk.CTkLabel(
                self.list_frame,
                text="Nenhum certificado emitido" if not query else "Nenhum resultado encontrado",
                font=fonts["body"], text_color=COLORS["muted"]
            ).grid(row=0, column=0, pady=40, padx=20)
            return

        self._create_table_header()

        for i, cert in enumerate(certs):
            self._create_cert_row(cert, i + 1, i % 2 == 1)

    def _create_table_header(self):
        fonts = get_fonts()
        header = ctk.CTkFrame(self.list_frame, fg_color=COLORS["primary"], corner_radius=6, height=36)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=2)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=3)
        header.grid_columnconfigure(3, weight=2)
        header.grid_columnconfigure(4, weight=1)
        header.grid_columnconfigure(5, weight=1)
        header.grid_columnconfigure(6, weight=2)

        for text, col in [("Numero", 0), ("NR", 1), ("Funcionario", 2),
                          ("Data", 3), ("Carga", 4), ("Assinado", 5), ("Acoes", 6)]:
            ctk.CTkLabel(
                header, text=text,
                font=fonts["small_bold"], text_color=COLORS["surface"],
                anchor="center" if col < 6 else "e"
            ).grid(row=0, column=col, sticky="ew" if col < 6 else "e", padx=12, pady=6)

    def _create_cert_row(self, cert: CertificateRecord, row_idx: int, alternate: bool = False):
        fonts = get_fonts()
        bg = COLORS["background"] if alternate else "transparent"
        row = ctk.CTkFrame(self.list_frame, fg_color=bg, corner_radius=0, height=36)
        row.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=0)
        row.grid_propagate(False)
        row.grid_columnconfigure(0, weight=2)
        row.grid_columnconfigure(1, weight=1)
        row.grid_columnconfigure(2, weight=3)
        row.grid_columnconfigure(3, weight=2)
        row.grid_columnconfigure(4, weight=1)
        row.grid_columnconfigure(5, weight=1)
        row.grid_columnconfigure(6, weight=2)

        ctk.CTkLabel(row, text=cert.cert_number,
            font=fonts["small_bold"], text_color=COLORS["primary"], anchor="center"
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=6)

        ctk.CTkLabel(row, text=cert.nr_code,
            font=fonts["small"], text_color=COLORS["text"], anchor="center"
        ).grid(row=0, column=1, sticky="ew", padx=12, pady=6)

        nome_cpf = f"{cert.funcionario_nome} ({cert.funcionario_cpf})" if cert.funcionario_cpf else cert.funcionario_nome
        ctk.CTkLabel(row, text=nome_cpf,
            font=fonts["small"], text_color=COLORS["text"], anchor="center"
        ).grid(row=0, column=2, sticky="ew", padx=12, pady=6)

        ctk.CTkLabel(row, text=cert.data_fim,
            font=fonts["small"], text_color=COLORS["text_secondary"], anchor="center"
        ).grid(row=0, column=3, sticky="ew", padx=12, pady=6)

        ctk.CTkLabel(row, text=f"{cert.carga_horaria}h",
            font=fonts["small"], text_color=COLORS["text_secondary"], anchor="center"
        ).grid(row=0, column=4, sticky="ew", padx=12, pady=6)

        # indicador de documento assinado anexado
        if cert.has_signed_doc:
            badge = ctk.CTkLabel(row, text="ASSINADO", font=fonts["tiny"],
                                 text_color=COLORS["success"], fg_color="#E6F2E6",
                                 corner_radius=4)
            badge.grid(row=0, column=5, padx=8, pady=4)
        else:
            ctk.CTkLabel(row, text="—", font=fonts["small"],
                         text_color=COLORS["muted"], anchor="center"
                         ).grid(row=0, column=5, sticky="ew", padx=12, pady=6)

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=6, sticky="e", padx=8, pady=4)

        ctk.CTkButton(btn_frame, text="PDF", width=40, height=26,
            font=fonts["small"], fg_color=COLORS["secondary"],
            hover_color=COLORS["primary"],
            command=lambda c=cert: self._open_pdf(c)
        ).pack(side="left", padx=2)

        ctk.CTkButton(btn_frame, text="Pasta", width=45, height=26,
            font=fonts["small"], fg_color=COLORS["accent"],
            hover_color=COLORS["secondary"],
            command=lambda c=cert: self._open_folder(c)
        ).pack(side="left", padx=2)

        ctk.CTkButton(btn_frame, text="Anexar", width=52, height=26,
            font=fonts["small"], fg_color=COLORS["warning"],
            hover_color="#BF5300",
            command=lambda c=cert: self._attach_signed(c)
        ).pack(side="left", padx=2)

        btn_baixar = ctk.CTkButton(btn_frame, text="Baixar", width=52, height=26,
            font=fonts["small"], fg_color=COLORS["success"],
            hover_color="#256B28",
            command=lambda c=cert: self._download_signed(c)
        )
        if not cert.has_signed_doc:
            btn_baixar.configure(state="disabled")
        btn_baixar.pack(side="left", padx=2)

        sep = ctk.CTkFrame(self.list_frame, fg_color=COLORS["border"], height=1)
        sep.grid(row=row_idx + 1, column=0, sticky="ew", padx=12, pady=0)

    # ── Documento assinado (escaneado) ───────────────────────

    def _attach_signed(self, cert: CertificateRecord):
        if cert.has_signed_doc:
            resp = messagebox.askyesnocancel(
                "Documento assinado",
                "Este certificado ja possui documento assinado anexado.\n\n"
                "Sim = substituir por novo arquivo\n"
                "Nao = remover o documento atual\n"
                "Cancelar = fechar sem alterar",
                parent=self
            )
            if resp is None:
                return
            if resp is False:
                if self.history_repo.remove_signed_doc(cert.id):
                    messagebox.showinfo("Sucesso", "Documento assinado removido.", parent=self)
                    self._refresh_list()
                else:
                    self._show_error("Erro ao remover documento")
                return
            # resp True: segue para substituir

        path = filedialog.askopenfilename(
            title=f"Anexar certificado assinado ({cert.cert_number})",
            filetypes=[("Documentos", "*.pdf *.jpg *.jpeg *.png"), ("Todos", "*.*")],
            parent=self
        )
        if not path:
            return
        try:
            ext = path.rsplit(".", 1)[-1].lower()
            with open(path, "rb") as f:
                data = f.read()
            self.history_repo.attach_signed_doc(cert.id, data, ext)
            messagebox.showinfo("Sucesso", "Documento assinado anexado ao certificado.", parent=self)
            self._refresh_list()
        except ValueError as e:
            messagebox.showerror("Erro", str(e), parent=self)
        except Exception as e:
            self._show_error(f"Erro ao anexar documento: {e}")

    def _download_signed(self, cert: CertificateRecord):
        result = self.history_repo.get_signed_doc(cert.id)
        if not result:
            messagebox.showwarning("Aviso", "Nenhum documento assinado anexado.", parent=self)
            return
        data, tipo = result
        ext_map = {"pdf": ".pdf", "jpg": ".jpg", "jpeg": ".jpg", "png": ".png"}
        ext = ext_map.get(tipo, ".pdf")
        path = filedialog.asksaveasfilename(
            title="Salvar documento assinado",
            defaultextension=ext,
            initialfile=f"{cert.cert_number}_assinado{ext}",
            parent=self
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
            self._show_error(f"Erro ao salvar documento: {e}")

    def _open_pdf(self, cert: CertificateRecord):
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
            self._show_error("Arquivo PDF nao encontrado")

    def _open_folder(self, cert: CertificateRecord):
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

    def refresh(self):
        self.pagination.reset()
        self._refresh_list()

    def _show_error(self, message: str):
        fonts = get_fonts()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Erro")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text=message, font=fonts["body"], wraplength=350).pack(pady=20)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy, fg_color=COLORS["error"]).pack()
