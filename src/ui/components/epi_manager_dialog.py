"""Gestao de Fichas de EPI por funcionario (roadmap 2.16).

EpiManagerDialog: lista fichas (nº, data, status, anexos) + Nova Ficha.
EpiItemsDialog: edicao dos itens de entrega + devolucao.
"""

import os
from datetime import date
from tkinter import messagebox, filedialog

import customtkinter as ctk

from src.ui.styles import COLORS, get_fonts


def _br(iso: str) -> str:
    if iso and len(iso) == 10 and iso[4] == "-":
        return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
    return iso or "-"


def _pasta_funcionario(employee) -> str:
    from src.utils.folder_utils import employee_folder_name
    from src.core.employee_repo import EmployeeRepository
    repo = EmployeeRepository()
    return employee_folder_name(employee, repo.get_all(limit=1000000))


class EpiManagerDialog(ctk.CTkToplevel):

    def __init__(self, master, employee):
        super().__init__(master)
        self.employee = employee
        self.title(f"Fichas de EPI — {employee.nome}")
        self.geometry("780x560")
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        fonts = get_fonts()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=f"Fichas de EPI — {employee.nome}",
                     font=fonts["heading"], text_color=COLORS["primary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Cada ficha tem codigo proprio e pode receber varias digitalizacoes (devolucoes parciais).",
                     font=fonts["small"], text_color=COLORS["text_secondary"]).grid(row=1, column=0, sticky="w")

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.list_frame.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 16))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(footer, text="+ Nova Ficha", height=34, font=fonts["body_bold"],
                      fg_color=COLORS["success"], hover_color="#256B28",
                      command=self._nova_ficha).pack(side="left")
        ctk.CTkButton(footer, text="Fechar", height=34, font=fonts["body_bold"],
                      fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
                      command=self.destroy).pack(side="right")

        self._refresh()

    def _repo(self):
        from src.core.epi_repo import EpiRepository
        return EpiRepository()

    def _refresh(self):
        fonts = get_fonts()
        for w in self.list_frame.winfo_children():
            w.destroy()
        repo = self._repo()
        fichas = repo.get_by_employee(self.employee.id)
        if not fichas:
            ctk.CTkLabel(self.list_frame, text="Nenhuma ficha de EPI registrada para este funcionario.",
                         font=fonts["body"], text_color=COLORS["muted"]).grid(row=0, column=0, pady=30)
            return
        for i, ficha in enumerate(fichas):
            self._criar_linha(ficha, i + 1, repo)

    def _criar_linha(self, ficha, idx, repo):
        fonts = get_fonts()
        row = ctk.CTkFrame(self.list_frame, fg_color="transparent", corner_radius=0)
        row.grid(row=idx, column=0, sticky="ew", padx=8, pady=2)
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text=ficha["epi_number"], font=fonts["small_bold"],
                     text_color=COLORS["primary"], width=90).grid(row=0, column=0, padx=(8, 4))
        ctk.CTkLabel(row, text=_br(ficha["data_emissao"]), font=fonts["small"],
                     text_color=COLORS["text_secondary"], width=80).grid(row=0, column=1, sticky="w")

        fechado = ficha["status"] == "fechado"
        badge = ctk.CTkLabel(row, text="FECHADO" if fechado else "ABERTO", font=fonts["tiny"],
                             text_color=COLORS["muted"] if fechado else COLORS["warning"],
                             fg_color=COLORS["border"] if fechado else "#FDF3E3", corner_radius=4)
        badge.grid(row=0, column=2, padx=6)

        n_docs = repo.count_docs(ficha["id"])
        n_items = len(ficha.get("items") or [])
        ctk.CTkLabel(row, text=f"{n_items} item(ns) | {n_docs} anexo(s)", font=fonts["small"],
                     text_color=COLORS["text_secondary"]).grid(row=0, column=3, padx=6)

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=4, sticky="e", padx=8)
        ctk.CTkButton(btns, text="PDF", width=40, height=24, font=fonts["small"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                      command=lambda f=ficha: self._abrir_pdf(f)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Itens", width=46, height=24, font=fonts["small"],
                      fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
                      command=lambda f=ficha: self._editar_itens(f)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Anexar", width=52, height=24, font=fonts["small"],
                      fg_color=COLORS["warning"], hover_color="#BF5300",
                      command=lambda f=ficha: self._anexar(f)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text=f"Anexos", width=52, height=24, font=fonts["small"],
                      fg_color=COLORS["success"], hover_color="#256B28",
                      command=lambda f=ficha: self._listar_anexos(f)).pack(side="left", padx=2)
        txt_toggle = "Fechar" if not fechado else "Reabrir"
        ctk.CTkButton(btns, text=txt_toggle, width=56, height=24, font=fonts["small"],
                      fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
                      command=lambda f=ficha: self._toggle(f)).pack(side="left", padx=2)

    # ── Acoes ──────────────────────────────────────────────────

    def _abrir_pdf(self, ficha):
        if ficha.get("pdf_path") and os.path.exists(ficha["pdf_path"]):
            try:
                os.startfile(ficha["pdf_path"])
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao abrir PDF: {e}", parent=self)
        else:
            messagebox.showwarning("Aviso", "PDF da ficha nao encontrado.", parent=self)

    def _toggle(self, ficha):
        novo = self._repo().toggle_status(ficha["id"])
        messagebox.showinfo("Status", f"Ficha {ficha['epi_number']} agora esta {novo.upper()}.", parent=self)
        self._refresh()

    def _anexar(self, ficha):
        path = filedialog.askopenfilename(
            title=f"Anexar digitalizacao a {ficha['epi_number']}",
            filetypes=[("Documentos", "*.pdf *.jpg *.jpeg *.png"), ("Todos", "*.*")],
            parent=self
        )
        if not path:
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
            from src.utils.paths import get_data_dir
            # nomeia com prefixo do numero p/ multiplas versoes convivarem
            nome = f"{ficha['epi_number']}_{os.path.basename(path)}"
            doc_id = self._repo().add_doc(ficha["id"], nome, data, path.rsplit('.', 1)[-1].lower())
            try:
                from src.core.network_sync import run_async, sync_epi_doc
                run_async(sync_epi_doc, ficha["id"], doc_id)
            except Exception:
                pass
            messagebox.showinfo("Sucesso", "Digitalizacao anexada (as anteriores foram mantidas).", parent=self)
            self._refresh()
        except ValueError as e:
            messagebox.showerror("Erro", str(e), parent=self)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("epi-anexar", e)
            messagebox.showerror("Erro", f"Erro ao anexar: {e}", parent=self)

    def _listar_anexos(self, ficha):
        _EpiDocsDialog(self, ficha, self._repo(), on_change=self._refresh)

    def _editar_itens(self, ficha):
        EpiItemsDialog(self, self.employee, ficha=ficha, on_save=self._refresh)

    def _nova_ficha(self):
        EpiItemsDialog(self, self.employee, ficha=None, on_save=self._refresh)


class EpiItemsDialog(ctk.CTkToplevel):
    """Nova ficha (ficha=None) ou edicao de itens/devolucao (ficha dict)."""

    def __init__(self, master, employee, ficha=None, on_save=None):
        super().__init__(master)
        self.employee = employee
        self.ficha = ficha
        self.on_save = on_save
        self.title("Editar Itens da Ficha" if ficha else "Nova Ficha de EPI")
        self.geometry("860x560")
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        fonts = get_fonts()

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 2))
        header.grid_columnconfigure(0, weight=1)
        titulo = f"{ficha['epi_number']} — {employee.nome}" if ficha else f"Nova ficha — {employee.nome}"
        ctk.CTkLabel(header, text=titulo, font=fonts["heading"],
                     text_color=COLORS["primary"]).grid(row=0, column=0, sticky="w")

        # cabecalho das colunas
        cab = ctk.CTkFrame(self, fg_color=COLORS["primary"], corner_radius=6, height=30)
        cab.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 0))
        cab.pack_propagate(False)
        for texto, col, w in [("C.A.", 0, 90), ("Descricao do Material", 1, 250),
                              ("Qtde", 2, 50), ("Data Entrega", 3, 95),
                              ("Dev. Qtde", 4, 55), ("Dev. Data", 5, 95)]:
            ctk.CTkLabel(cab, text=texto, font=fonts["small_bold"],
                         text_color=COLORS["surface"], width=w).grid(row=0, column=col, padx=4)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=6)
        for col in range(6):
            self.scroll.grid_columnconfigure(col, weight=0)

        self.linhas = []  # [{vars..., frame}]

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=3, column=0, sticky="ew", padx=20, pady=(2, 14))
        rodape.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(rodape, text="+ Adicionar Item", height=30, font=fonts["body"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                      command=self._add_linha).pack(side="left")
        ctk.CTkButton(rodape, text="Cancelar", height=30, font=fonts["body_bold"],
                      fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
                      command=self.destroy).pack(side="right")
        ctk.CTkButton(rodape, text="Salvar", height=30, font=fonts["body_bold"],
                      fg_color=COLORS["success"], hover_color="#256B28",
                      command=self._salvar).pack(side="right", padx=6)

        itens = ficha["items"] if ficha else []
        if not itens:
            self._add_linha()
        else:
            for it in itens:
                self._add_linha(it)

    def _add_linha(self, item=None):
        fonts = get_fonts()
        idx = len(self.linhas)
        frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["surface"] if idx % 2 == 0 else "transparent",
                             corner_radius=4)
        frame.grid(row=idx, column=0, sticky="ew", pady=1, columnspan=7)

        hoje = date.today().strftime("%d/%m/%Y")
        item = item or {}
        ca_var = ctk.StringVar(value=item.get("ca", ""))
        desc_var = ctk.StringVar(value=item.get("descricao", ""))
        qtde_var = ctk.StringVar(value=item.get("quantidade", ""))
        ent_var = ctk.StringVar(value=_br(item.get("data_entrega", "")) or hoje)
        devq_var = ctk.StringVar(value=item.get("dev_quantidade", ""))
        devd_var = ctk.StringVar(value=_br(item.get("dev_data", "")))

        ctk.CTkEntry(frame, textvariable=ca_var, width=84, height=28, font=fonts["small"]).grid(row=0, column=0, padx=3, pady=2)
        ctk.CTkEntry(frame, textvariable=desc_var, width=244, height=28, font=fonts["small"]).grid(row=0, column=1, padx=3, pady=2)
        ctk.CTkEntry(frame, textvariable=qtde_var, width=44, height=28, font=fonts["small"]).grid(row=0, column=2, padx=3, pady=2)
        ctk.CTkEntry(frame, textvariable=ent_var, width=88, height=28, font=fonts["small"]).grid(row=0, column=3, padx=3, pady=2)
        ctk.CTkEntry(frame, textvariable=devq_var, width=48, height=28, font=fonts["small"]).grid(row=0, column=4, padx=3, pady=2)
        ctk.CTkEntry(frame, textvariable=devd_var, width=88, height=28, font=fonts["small"]).grid(row=0, column=5, padx=3, pady=2)
        ctk.CTkButton(frame, text="X", width=28, height=28, font=fonts["small"],
                      fg_color=COLORS["error"], hover_color="#B71C1C",
                      command=lambda f=frame: self._remove_linha(f)).grid(row=0, column=6, padx=3, pady=2)

        self.linhas.append({"frame": frame, "ca": ca_var, "descricao": desc_var,
                            "quantidade": qtde_var, "data_entrega": ent_var,
                            "dev_quantidade": devq_var, "dev_data": devd_var})

    def _remove_linha(self, frame):
        self.linhas = [l for l in self.linhas if l["frame"] != frame]
        frame.destroy()

    def _coletar(self):
        from datetime import date as _date
        itens = []
        for l in self.linhas:
            desc = l["descricao"].get().strip()
            if not desc:
                continue  # linhas sem descricao sao ignoradas
            def _iso(val):
                val = val.strip()
                if not val:
                    return ""
                dia, mes, ano = val.split("/")
                _date(int(ano), int(mes), int(dia))
                return f"{ano}-{mes}-{dia}"
            try:
                itens.append({
                    "ca": l["ca"].get().strip(),
                    "descricao": desc,
                    "quantidade": l["quantidade"].get().strip(),
                    "data_entrega": _iso(l["data_entrega"]),
                    "dev_quantidade": l["dev_quantidade"].get().strip(),
                    "dev_data": _iso(l["dev_data"]),
                })
            except ValueError:
                raise ValueError(f"Data invalida no item '{desc}' (use dd/mm/aaaa)")
        return itens

    def _salvar(self):
        from src.core.epi_repo import EpiRepository
        from src.core.epi_pdf_generator import generate_epi_pdf
        from src.utils.paths import get_data_dir
        repo = EpiRepository()
        try:
            itens = self._coletar()
        except ValueError as e:
            messagebox.showerror("Erro", str(e), parent=self)
            return
        if not itens and not self.ficha:
            messagebox.showerror("Erro", "Adicione pelo menos um item com descricao.", parent=self)
            return

        pasta = _pasta_funcionario(self.employee)
        try:
            if self.ficha:
                repo.update_items(self.ficha["id"], itens)
                ficha = repo.get_by_id(self.ficha["id"])
                pdf_path = ficha["pdf_path"]
                if not pdf_path or not os.path.exists(os.path.dirname(pdf_path or "")):
                    destino = get_data_dir() / "epis" / pasta
                    destino.mkdir(parents=True, exist_ok=True)
                    d = _br(ficha["data_emissao"]).replace("/", "-")
                    pdf_path = str(destino / f"Ficha de EPI - {d} ({ficha['epi_number']}).pdf")
                generate_epi_pdf(pdf_path, ficha["epi_number"], self.employee,
                                 ficha["data_emissao"], itens)
                repo.update_pdf_path(ficha["id"], pdf_path)
            else:
                epi_number = repo.next_epi_number()
                hoje = date.today().isoformat()
                destino = get_data_dir() / "epis" / pasta
                destino.mkdir(parents=True, exist_ok=True)
                d = date.today().strftime("%d-%m-%Y")
                pdf_path = str(destino / f"Ficha de EPI - {d} ({epi_number}).pdf")
                generate_epi_pdf(pdf_path, epi_number, self.employee, hoje, itens)
                epi_id = repo.save(epi_number, self.employee.id, hoje, itens, pdf_path)
                ficha = repo.get_by_id(epi_id)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("epi-salvar", e)
            messagebox.showerror("Erro", f"Erro ao salvar ficha: {e}", parent=self)
            return

        try:
            from src.core.network_sync import run_async, sync_epi
            run_async(sync_epi, repo.get_by_id(ficha["id"]), self.employee)
        except Exception:
            pass

        messagebox.showinfo("Sucesso", f"Ficha {ficha['epi_number']} salva.", parent=self)
        self.destroy()
        if self.on_save:
            self.on_save()


class _EpiDocsDialog(ctk.CTkToplevel):
    """Lista de digitalizacoes anexadas a uma ficha (multiplas versoes)."""

    def __init__(self, master, ficha, repo, on_change=None):
        super().__init__(master)
        self.ficha = ficha
        self.repo = repo
        self.on_change = on_change
        self.title(f"Anexos — {ficha['epi_number']}")
        self.geometry("620x420")
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(self, text="Fechar", height=30, font=get_fonts()["body_bold"],
                      fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
                      command=self.destroy).grid(row=1, column=0, pady=(0, 14))
        self._refresh()

    def _refresh(self):
        fonts = get_fonts()
        for w in self.scroll.winfo_children():
            w.destroy()
        docs = self.repo.list_docs(self.ficha["id"])
        if not docs:
            ctk.CTkLabel(self.scroll, text="Nenhuma digitalizacao anexada.",
                         font=fonts["body"], text_color=COLORS["muted"]).grid(row=0, column=0, pady=24)
            return
        for i, doc in enumerate(docs):
            row = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=6, pady=2)
            row.grid_columnconfigure(0, weight=1)
            kb = max(doc["tamanho"] // 1024, 1)
            ctk.CTkLabel(row, text=f"{doc['filename']}  ({kb} KB)",
                         font=fonts["small"], text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
            ctk.CTkButton(row, text="Baixar", width=56, height=24, font=fonts["small"],
                          fg_color=COLORS["success"], hover_color="#256B28",
                          command=lambda d=doc: self._baixar(d)).pack(side="left", padx=4)
            ctk.CTkButton(row, text="Remover", width=64, height=24, font=fonts["small"],
                          fg_color=COLORS["error"], hover_color="#B71C1C",
                          command=lambda d=doc: self._remover(d)).pack(side="left", padx=4)

    def _baixar(self, doc):
        result = self.repo.get_doc(doc["id"])
        if not result:
            return
        _, filename, data, tipo = result
        ext = {"pdf": ".pdf", "jpg": ".jpg", "jpeg": ".jpg", "png": ".png"}.get(tipo, ".pdf")
        path = filedialog.asksaveasfilename(title="Salvar anexo", defaultextension=ext,
                                            initialfile=filename + ext if not filename.lower().endswith(ext) else filename,
                                            parent=self)
        if not path:
            return
        try:
            with open(path, "wb") as f:
                f.write(data)
            if messagebox.askyesno("Sucesso", f"Salvo em:\n{path}\n\nAbrir agora?", parent=self):
                try:
                    os.startfile(path)
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}", parent=self)

    def _remover(self, doc):
        if messagebox.askyesno("Confirmar", f"Remover o anexo '{doc['filename']}'?", parent=self):
            self.repo.delete_doc(doc["id"])
            self._refresh()
            if self.on_change:
                self.on_change()
