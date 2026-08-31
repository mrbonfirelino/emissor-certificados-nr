"""
Popup de contexto de geracao de cartoes PPTX.

Exibido quando o template selecionado usa {{SETOR}}, {{PAPEL}} e/ou {{MATRICULA}}:
- Setor: valor global do lote (ex: "Manutencao Mecanica")
- Lista de funcionarios (com scroll, janela redimensionavel):
  - Matricula por funcionario (obrigatoria, preenchida na hora — o numero tem
    validade, portanto nao fica salva no cadastro), se {{MATRICULA}}
  - Switch Lider/Liderado por funcionario (padrao Liderado), se {{PAPEL}}
"""

import customtkinter as ctk
from typing import Optional

from src.ui.styles import COLORS, get_fonts

LIDER = "LIDER"
LIDERADO = "LIDERADO"


class GenerationOptionsDialog(ctk.CTkToplevel):
    """
    Retorna dict no atributo `selected`:
    {"setor": str, "papeis": {emp_id: str}, "matriculas": {emp_id: str}}
    ou None se cancelado.
    """

    def __init__(
        self,
        master,
        employees: list,
        template: dict,
        initial_setor: str = "",
    ):
        super().__init__(master)
        self.selected: Optional[dict] = None

        used_fields = set(template.get("used_fields") or [])
        self._needs_setor = "SETOR" in used_fields
        self._needs_papel = "PAPEL" in used_fields
        self._needs_matricula = "MATRICULA" in used_fields
        self._needs_list = self._needs_papel or self._needs_matricula

        title = "Dados do Lote de Cartoes"
        self.title(title)
        w, h = 620, 660
        self.geometry(f"{w}x{h}")
        self.minsize(560, 480)
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)

        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (w // 2)
        y = master.winfo_rooty() + (master.winfo_height() // 2) - (h // 2)
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self._employees = employees
        self._papeis_vars = {}
        self._matricula_vars = {}

        fonts = get_fonts()
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=20)
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content, text=title,
            font=fonts["heading"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        ctk.CTkLabel(
            content,
            text=f"Modelo: {template.get('card_code', '')} — {template.get('cliente_nome', '')}  |  "
                 f"{len(employees)} funcionario(s)",
            font=fonts["small"], text_color=COLORS["muted"]
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        row = 2

        # ── Setor (global do lote) ──
        self._setor_var = None
        if self._needs_setor:
            ctk.CTkLabel(
                content, text="Setor / Departamento (vale para todos os cartoes deste lote)",
                font=fonts["body_bold"], text_color=COLORS["text"]
            ).grid(row=row, column=0, sticky="w", pady=(0, 4))
            row += 1
            self._setor_var = ctk.StringVar(value=initial_setor)
            ctk.CTkEntry(
                content, textvariable=self._setor_var,
                font=fonts["body"], height=34, corner_radius=6,
                placeholder_text="Ex: Manutencao Mecanica"
            ).grid(row=row, column=0, sticky="ew", pady=(0, 12))
            row += 1

        # ── Lista de funcionarios (com scroll) ──
        self._list_frame = None
        if self._needs_list:
            header = ctk.CTkFrame(content, fg_color="transparent")
            header.grid(row=row, column=0, sticky="ew", pady=(0, 4))
            header.grid_columnconfigure(0, weight=1)
            row += 1

            titulo_lista = "Papel e/ou matricula de cada funcionario neste servico:"
            ctk.CTkLabel(
                header, text=titulo_lista,
                font=fonts["body_bold"], text_color=COLORS["text"]
            ).grid(row=0, column=0, sticky="w")

            if self._needs_papel:
                quick = ctk.CTkFrame(header, fg_color="transparent")
                quick.grid(row=0, column=1, sticky="e")
                ctk.CTkButton(
                    quick, text="Todos Liderados", width=110, height=26,
                    font=fonts["small"], fg_color=COLORS["secondary"],
                    hover_color=COLORS["primary"],
                    command=lambda: self._set_all(LIDERADO)
                ).pack(side="left", padx=(0, 6))
                ctk.CTkButton(
                    quick, text="Todos Lideres", width=100, height=26,
                    font=fonts["small"], fg_color=COLORS["secondary"],
                    hover_color=COLORS["primary"],
                    command=lambda: self._set_all(LIDER)
                ).pack(side="left")

            # cabecalho das colunas
            if self._needs_matricula:
                cols_hdr = ctk.CTkFrame(content, fg_color="transparent")
                cols_hdr.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 2))
                cols_hdr.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(cols_hdr, text="Funcionario", font=fonts["small_bold"],
                             text_color=COLORS["muted"], anchor="w").grid(row=0, column=0, sticky="w")
                ctk.CTkLabel(cols_hdr, text="Matricula", font=fonts["small_bold"],
                             text_color=COLORS["muted"]).grid(row=0, column=1, sticky="e", padx=(0, 132 if self._needs_papel else 8))
                row += 1

            self._list_frame = ctk.CTkScrollableFrame(
                content, fg_color=COLORS["surface"], corner_radius=8
            )
            self._list_frame.grid(row=row, column=0, sticky="nsew", pady=(2, 8))
            self._list_frame.grid_columnconfigure(0, weight=1)
            content.grid_rowconfigure(row, weight=1)  # lista expande com a janela
            row += 1

            self._build_rows()

        # ── Botoes ──
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew", pady=(6, 0))
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame, text="Cancelar", font=fonts["body_bold"], height=34,
            fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
            command=self.destroy
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            btn_frame, text="Gerar Cartoes", font=fonts["body_bold"], height=34,
            fg_color=COLORS["success"], hover_color="#256B28",
            command=self._confirm
        ).grid(row=0, column=1, sticky="e")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(50, self.focus_force)

    def _build_rows(self):
        fonts = get_fonts()
        for i, emp in enumerate(self._employees):
            bg = COLORS["background"] if i % 2 == 1 else "transparent"
            row = ctk.CTkFrame(self._list_frame, fg_color=bg, corner_radius=4)
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=1)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row, text=emp.nome, font=fonts["body"],
                text_color=COLORS["text"], anchor="w"
            ).grid(row=0, column=0, sticky="ew", padx=(10, 8), pady=6)

            right = ctk.CTkFrame(row, fg_color="transparent")
            right.grid(row=0, column=1, sticky="e", padx=(8, 10), pady=4)

            if self._needs_matricula:
                # campo vazio: matricula tem validade, preenchida na hora da emissao
                var = ctk.StringVar(value="")
                self._matricula_vars[emp.id] = var
                ctk.CTkEntry(
                    right, textvariable=var, width=118, height=27,
                    font=fonts["small"], corner_radius=4,
                    fg_color=COLORS["surface"], border_color=COLORS["border"],
                    placeholder_text="Matricula"
                ).pack(side="left", padx=(0, 8))

            if self._needs_papel:
                seg = ctk.CTkSegmentedButton(
                    right,
                    values=[LIDERADO, LIDER],
                    font=fonts["small"], height=27,
                    selected_color=COLORS["primary"],
                    unselected_color=COLORS["background"],
                    selected_hover_color=COLORS["primary_hover"],
                    unselected_hover_color=COLORS["border"],
                )
                seg.set(LIDERADO)
                seg.pack(side="left")
                self._papeis_vars[emp.id] = seg

    def _set_all(self, papel: str):
        for seg in self._papeis_vars.values():
            seg.set(papel)

    def _confirm(self):
        setor = self._setor_var.get().strip() if self._setor_var is not None else ""
        if self._needs_setor and not setor:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "Informe o setor/departamento do lote.", parent=self)
            return
        matriculas = {emp_id: var.get().strip() for emp_id, var in self._matricula_vars.items()}
        if self._needs_matricula:
            sem_matricula = [
                next((e.nome for e in self._employees if e.id == emp_id), str(emp_id))
                for emp_id, val in matriculas.items() if not val
            ]
            if sem_matricula:
                from tkinter import messagebox
                messagebox.showwarning(
                    "Aviso",
                    "Matricula obrigatoria (o numero tem validade e e preenchido na emissao).\n"
                    "Preencha a matricula de:\n\n" + "\n".join(sem_matricula[:15]) +
                    ("\n..." if len(sem_matricula) > 15 else ""),
                    parent=self
                )
                return
        papeis = {emp_id: seg.get() for emp_id, seg in self._papeis_vars.items()}
        self.selected = {
            "setor": setor,
            "papeis": papeis,
            "matriculas": matriculas,
        }
        self.destroy()
