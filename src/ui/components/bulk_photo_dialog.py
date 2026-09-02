"""
Dialogo de conferencia da importacao de fotos em massa.

Lista cada foto casada com um funcionario (miniatura 3x4, arquivo, funcionario,
status adicionar/substituir) com checkbox pre-marcado; fotos nao casadas ficam
em secao separada sem checkbox. Importacao aplica process_photo_3x4 e grava
via EmployeeRepository.update_foto.
"""

import customtkinter as ctk
from tkinter import messagebox

from src.ui.styles import COLORS, get_fonts


class BulkPhotoDialog(ctk.CTkToplevel):
    """Ao fechar, atributo `importados` = quantidade de fotos aplicadas."""

    def __init__(self, master, employee_repo, casados: list, nao_casados: list,
                 on_done=None):
        super().__init__(master)
        self.importados = 0
        self.employee_repo = employee_repo
        self._casados = casados
        self._on_done = on_done
        self._checks = {}  # emp_id -> (BooleanVar, path)

        self.title("Importar Fotos 3x4")
        w, h = 760, 640
        self.geometry(f"{w}x{h}")
        self.minsize(680, 480)
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (w // 2)
        y = master.winfo_rooty() + (master.winfo_height() // 2) - (h // 2)
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        fonts = get_fonts()
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=16)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(content, text=f"Importar Fotos — {len(casados)} casada(s), "
                                   f"{len(nao_casados)} sem match",
                     font=fonts["heading"], text_color=COLORS["primary"]
                     ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        lista = ctk.CTkScrollableFrame(content, fg_color=COLORS["surface"], corner_radius=8)
        lista.grid(row=1, column=0, sticky="nsew")
        lista.grid_columnconfigure(1, weight=1)

        r = 0
        for item in casados:
            r = self._row(lista, r, item)

        if nao_casados:
            ctk.CTkLabel(lista, text="Nao encontradas no cadastro (serao ignoradas):",
                         font=fonts["small_bold"], text_color=COLORS["warning"], anchor="w"
                         ).grid(row=r, column=0, columnspan=4, sticky="w", padx=10, pady=(12, 4))
            r += 1
            for item in nao_casados:
                ctk.CTkLabel(lista, text=f"{item['path'].name}  —  {item['motivo']}",
                             font=fonts["small"], text_color=COLORS["muted"], anchor="w"
                             ).grid(row=r, column=0, columnspan=4, sticky="w", padx=24)
                r += 1

        btns = ctk.CTkFrame(content, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        btns.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(btns, text="Cancelar", font=fonts["body_bold"], height=34,
                      fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
                      command=self.destroy).grid(row=0, column=0, sticky="w")
        self._btn_importar = ctk.CTkButton(
            btns, text="Importar Selecionados", font=fonts["body_bold"], height=34,
            fg_color=COLORS["success"], hover_color="#256B28",
            command=self._importar
        )
        self._btn_importar.grid(row=0, column=1, sticky="e")

    def _row(self, lista, r: int, item: dict) -> int:
        fonts = get_fonts()
        emp = item["employee"]
        path = item["path"]

        # miniatura
        try:
            from PIL import Image

            pil = Image.open(str(path))
            pil.thumbnail((38, 50), Image.LANCZOS)
            img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(38, 50))
            lbl = ctk.CTkLabel(lista, image=img, text="")
            lbl.grid(row=r, column=0, padx=(10, 6), pady=4)
            lbl._image_ref = img
        except Exception:
            ctk.CTkLabel(lista, text="?", font=fonts["small"],
                         text_color=COLORS["muted"]).grid(row=r, column=0, padx=10, pady=4)

        nome_txt = f"{emp.nome}  ({emp.cpf})" if emp.cpf else emp.nome
        status = "SUBSTITUIR foto atual" if emp.foto else "adicionar foto"
        cor = COLORS["warning"] if emp.foto else COLORS["success"]
        ctk.CTkLabel(lista, text=nome_txt, font=fonts["body"], text_color=COLORS["text"],
                     anchor="w").grid(row=r, column=1, sticky="w", padx=6, pady=4)
        ctk.CTkLabel(lista, text=status, font=fonts["small"], text_color=cor,
                     anchor="w").grid(row=r, column=2, sticky="e", padx=6)
        ctk.CTkLabel(lista, text=path.name, font=fonts["tiny"], text_color=COLORS["muted"],
                     anchor="e").grid(row=r, column=3, sticky="e", padx=(6, 10))

        var = ctk.BooleanVar(value=True)
        chk = ctk.CTkCheckBox(lista, text="", variable=var, width=24,
                              fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
                              checkbox_height=18, checkbox_width=18)
        chk.grid(row=r, column=4, padx=(4, 10), pady=4)
        self._checks[emp.id] = (var, path)
        return r + 1

    def _importar(self):
        from src.utils.photo_utils import process_photo_3x4

        selecionados = [(emp_id, path) for emp_id, (var, path) in self._checks.items() if var.get()]

        if not selecionados:
            messagebox.showwarning("Aviso", "Nenhuma foto selecionada.", parent=self)
            return

        self._btn_importar.configure(state="disabled", text="Importando...")
        self.update_idletasks()

        ok, erros = 0, []
        for emp_id, path in selecionados:
            try:
                data = process_photo_3x4(str(path))
                if self.employee_repo.update_foto(emp_id, data):
                    ok += 1
                else:
                    erros.append(path.name)
            except Exception as e:
                erros.append(f"{path.name}: {e}")

        self.importados = ok
        msg = f"{ok} foto(s) importada(s) com sucesso."
        if erros:
            msg += "\n\nFalhas:\n" + "\n".join(erros[:10])
        if self._on_done:
            try:
                self._on_done()
            except Exception:
                pass
        messagebox.showinfo("Importar Fotos", msg, parent=self)
        self.destroy()
