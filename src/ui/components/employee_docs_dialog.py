"""Dialog de documentos gerais do funcionario ("Outros": CNH, identidade, etc.).

Os arquivos sao salvos no banco (BLOB) e espelhados na pasta de rede
({Funcionario}/Outros) quando o espelhamento estiver ativo.
"""

import os
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox

from src.ui.styles import COLORS, get_fonts


def _fmt_tamanho(bytes_: int) -> str:
    b = bytes_ or 0
    if b >= 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    return f"{b / 1024:.0f} KB"


class EmployeeDocsDialog(ctk.CTkToplevel):

    def __init__(self, master, employee_repo, employee):
        super().__init__(master)
        self.employee_repo = employee_repo
        self.employee = employee
        self.title(f"Documentos — {employee.nome}")
        self.geometry("640x460")
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=COLORS["background"])

        fonts = get_fonts()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text=f"Outros documentos de {employee.nome}",
            font=fonts["heading"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header, text="Qualquer formato (ate 50MB). Salvo no banco e espelhado na rede (Funcionario/Outros).",
            font=fonts["small"], text_color=COLORS["muted"]
        ).grid(row=1, column=0, sticky="w")

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 8))
        self.list_frame.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 16))
        ctk.CTkButton(
            footer, text="+ Adicionar", height=32,
            font=fonts["body_bold"], fg_color=COLORS["success"], hover_color="#256B28",
            command=self._adicionar
        ).pack(side="left")
        ctk.CTkButton(
            footer, text="Fechar", height=32,
            font=fonts["body"], fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
            command=self.destroy
        ).pack(side="right")

        self._refresh()

    def _refresh(self):
        fonts = get_fonts()
        for w in self.list_frame.winfo_children():
            w.destroy()
        docs = self.employee_repo.list_docs(self.employee.id)
        if not docs:
            ctk.CTkLabel(
                self.list_frame, text="Nenhum documento anexado",
                font=fonts["body"], text_color=COLORS["muted"]
            ).grid(row=0, column=0, pady=30)
            return
        for i, doc in enumerate(docs):
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=10, pady=4)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                row, text=doc["tipo"].upper(), width=52,
                font=fonts["small_bold"], text_color=COLORS["primary"]
            ).grid(row=0, column=0, padx=(4, 8))
            ctk.CTkLabel(
                row, text=f"{doc['filename']}  ({_fmt_tamanho(doc['tamanho'])})",
                font=fonts["small"], text_color=COLORS["text"], anchor="w"
            ).grid(row=0, column=1, sticky="ew")
            ctk.CTkButton(
                row, text="Baixar", width=56, height=26,
                font=fonts["small"], fg_color=COLORS["secondary"],
                hover_color=COLORS["primary"],
                command=lambda d=doc: self._baixar(d)
            ).grid(row=0, column=2, padx=4)
            ctk.CTkButton(
                row, text="Remover", width=64, height=26,
                font=fonts["small"], fg_color=COLORS["error"], hover_color="#B71C1C",
                command=lambda d=doc: self._remover(d)
            ).grid(row=0, column=3, padx=4)

    def _adicionar(self):
        path = filedialog.askopenfilename(
            title=f"Adicionar documento ({self.employee.nome})",
            filetypes=[("Todos os arquivos", "*.*")],
            parent=self
        )
        if not path:
            return
        ext = path.rsplit(".", 1)[-1].lower()
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.employee_repo.add_doc(self.employee.id, os.path.basename(path), data, ext)
        except ValueError as e:
            messagebox.showerror("Erro", str(e), parent=self)
            return
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao anexar documento: {e}", parent=self)
            return
        self._espelhar(os.path.basename(path), data)
        self._refresh()

    def _baixar(self, doc):
        res = self.employee_repo.get_doc(doc["id"])
        if not res:
            messagebox.showwarning("Aviso", "Documento nao encontrado.", parent=self)
            return
        _, fname, data, tipo = res
        ext = "." + (tipo or "dat")
        path = filedialog.asksaveasfilename(
            title="Salvar documento",
            defaultextension=ext,
            initialfile=fname if fname.lower().endswith(ext) else fname + ext,
            parent=self
        )
        if not path:
            return
        try:
            with open(path, "wb") as f:
                f.write(data)
            if messagebox.askyesno("Sucesso", f"Documento salvo em:\n{path}\n\nAbrir agora?", parent=self):
                try:
                    if sys.platform == "win32":
                        os.startfile(path)
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}", parent=self)

    def _remover(self, doc):
        if not messagebox.askyesno("Confirmar", f"Remover '{doc['filename']}'?", parent=self):
            return
        self.employee_repo.delete_doc(doc["id"])
        self._remover_rede(doc["filename"])
        self._refresh()

    def _espelhar(self, filename: str, data: bytes):
        try:
            from src.core import network_sync
            network_sync.run_async(network_sync.sync_doc, filename, data, self.employee)
        except Exception:
            pass

    def _remover_rede(self, filename: str):
        try:
            from src.core import network_sync
            network_sync.run_async(network_sync.remove_doc_network, filename, self.employee)
        except Exception:
            pass
