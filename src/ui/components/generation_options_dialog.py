"""
Tela de Revisao da Emissao de cartoes PPTX.

Abre SEMPRE antes de Gerar e Preview. O usuario confere e pode editar os dados
de cada funcionario (nome, funcao, telefone, foto) — as alteracoes valem SOMENTE
para aquela emissao (trabalha sobre copias transitorias do Employee; nada e
gravado no banco).

Tambem concentra o contexto do lote:
- Setor global (se o template usa {{SETOR}})
- Matricula por funcionario (obrigatoria, preenchida na hora — {{MATRICULA}})
- Papel Lider/Liderado por funcionario ({{PAPEL}})
"""

import re
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Optional

from src.ui.styles import COLORS, get_fonts

LIDER = "LIDER"
LIDERADO = "LIDERADO"


class EmissionReviewDialog(ctk.CTkToplevel):
    """
    Trabalha sobre COPIAS de Employee (nao toca o banco).

    Atributo `selected` apos fechar:
    {"setor": str, "papeis": {id: str}, "matriculas": {id: str},
     "employees": List[Employee]}  — ou None se cancelado.
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

        self.title("Revisao da Emissao")
        w, h = 940, 680
        self.geometry(f"{w}x{h}")
        self.minsize(820, 500)
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)

        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (w // 2)
        y = master.winfo_rooty() + (master.winfo_height() // 2) - (h // 2)
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self._employees = employees  # copias transitorias
        self._papeis_vars = {}
        self._matricula_vars = {}
        self._nome_vars = {}
        self._funcao_vars = {}
        self._tel_vars = {}
        self._foto_override = {}  # emp_id -> bytes
        self._thumb_labels = {}   # emp_id -> label (para atualizar preview)

        fonts = get_fonts()
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=18)
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content, text="Revisao da Emissao",
            font=fonts["heading"], text_color=COLORS["primary"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))

        ctk.CTkLabel(
            content,
            text=(f"Modelo: {template.get('card_code', '')} — {template.get('cliente_nome', '')}  |  "
                  f"{len(employees)} funcionario(s)  |  "
                  "Edicoes validas apenas para esta emissao (nao salvam no cadastro)"),
            font=fonts["small"], text_color=COLORS["muted"], anchor="w", justify="left"
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))

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

        # ── Cabecalho da lista ──
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        header.grid_columnconfigure(0, weight=1)
        row += 1

        ctk.CTkLabel(
            header, text="Dados dos funcionarios (edite se necessario):",
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

        # ── Lista de funcionarios (scroll, expande com a janela) ──
        self._list_frame = ctk.CTkScrollableFrame(
            content, fg_color=COLORS["surface"], corner_radius=8
        )
        self._list_frame.grid(row=row, column=0, sticky="nsew", pady=(2, 8))
        self._list_frame.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(row, weight=1)
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
            btn_frame, text="Confirmar", font=fonts["body_bold"], height=34,
            fg_color=COLORS["success"], hover_color="#256B28",
            command=self._confirm
        ).grid(row=0, column=1, sticky="e")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(50, self.focus_force)

    # ── Construção das linhas ─────────────────────────────────

    def _build_rows(self):
        fonts = get_fonts()
        try:
            from src.utils.photo_utils import bytes_to_pil_image
            from PIL import Image
        except Exception:
            bytes_to_pil_image = None
            Image = None

        for i, emp in enumerate(self._employees):
            bg = COLORS["background"] if i % 2 == 1 else "transparent"
            rowf = ctk.CTkFrame(self._list_frame, fg_color=bg, corner_radius=4)
            rowf.grid(row=i, column=0, sticky="ew", padx=4, pady=2)
            rowf.grid_columnconfigure(2, weight=3)   # nome
            rowf.grid_columnconfigure(3, weight=3)   # funcao
            rowf.grid_columnconfigure(4, weight=2)   # tel
            if self._needs_matricula:
                rowf.grid_columnconfigure(5, weight=2)

            # foto (thumb + trocar)
            foto_frame = ctk.CTkFrame(rowf, fg_color="transparent")
            foto_frame.grid(row=0, column=0, sticky="w", padx=(8, 6), pady=6)

            lbl_foto = ctk.CTkLabel(foto_frame, text="sem\nfoto", font=fonts["tiny"],
                                    text_color=COLORS["muted"], width=34)
            lbl_foto.pack()
            self._thumb_labels[emp.id] = lbl_foto
            self._update_thumb(emp)

            btn_foto = ctk.CTkButton(
                foto_frame, text="Trocar", width=52, height=20,
                font=fonts["tiny"], corner_radius=4,
                fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                command=lambda e=emp: self._trocar_foto(e)
            )
            btn_foto.pack(pady=(2, 0))

            # campos
            var_nome = ctk.StringVar(value=emp.nome or "")
            self._nome_vars[emp.id] = var_nome
            ctk.CTkEntry(rowf, textvariable=var_nome, height=28, corner_radius=4,
                         font=fonts["small"], fg_color=COLORS["surface"],
                         border_color=COLORS["border"], placeholder_text="Nome"
                         ).grid(row=0, column=2, sticky="ew", padx=4)

            var_funcao = ctk.StringVar(value=emp.funcao or "")
            self._funcao_vars[emp.id] = var_funcao
            ctk.CTkEntry(rowf, textvariable=var_funcao, height=28, corner_radius=4,
                         font=fonts["small"], fg_color=COLORS["surface"],
                         border_color=COLORS["border"], placeholder_text="Funcao"
                         ).grid(row=0, column=3, sticky="ew", padx=4)

            tel_display = emp.telefone_formatado() if getattr(emp, "telefone", None) else ""
            var_tel = ctk.StringVar(value=tel_display)
            self._tel_vars[emp.id] = var_tel
            ctk.CTkEntry(rowf, textvariable=var_tel, width=110, height=28, corner_radius=4,
                         font=fonts["small"], fg_color=COLORS["surface"],
                         border_color=COLORS["border"], placeholder_text="Telefone"
                         ).grid(row=0, column=4, sticky="ew", padx=4)

            if self._needs_matricula:
                # campo vazio: matricula tem validade, preenchida na hora da emissao
                var = ctk.StringVar(value="")
                self._matricula_vars[emp.id] = var
                ctk.CTkEntry(rowf, textvariable=var, width=105, height=28, corner_radius=4,
                             font=fonts["small"], fg_color=COLORS["surface"],
                             border_color=COLORS["border"], placeholder_text="Matricula"
                             ).grid(row=0, column=5, sticky="ew", padx=4)

            if self._needs_papel:
                seg = ctk.CTkSegmentedButton(
                    rowf, values=[LIDERADO, LIDER],
                    font=fonts["small"], height=27,
                    selected_color=COLORS["primary"],
                    unselected_color=COLORS["background"],
                    selected_hover_color=COLORS["primary_hover"],
                    unselected_hover_color=COLORS["border"],
                )
                seg.set(LIDERADO)
                seg.grid(row=0, column=6, sticky="e", padx=(6, 8))
                self._papeis_vars[emp.id] = seg

    def _update_thumb(self, emp):
        lbl = self._thumb_labels.get(emp.id)
        if not lbl:
            return
        foto = self._foto_override.get(emp.id) or getattr(emp, "foto", None)
        if foto:
            try:
                from src.utils.photo_utils import bytes_to_pil_image
                from PIL import Image

                pil = bytes_to_pil_image(foto)
                if pil:
                    thumb = pil.copy()
                    thumb.thumbnail((28, 36), Image.LANCZOS)
                    img = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(28, 36))
                    lbl.configure(image=img, text="", width=34)
                    lbl._image_ref = img
                    return
            except Exception:
                pass
        lbl.configure(image=None, text="sem\nfoto", width=34)
        lbl._image_ref = None

    def _trocar_foto(self, emp):
        path = filedialog.askopenfilename(
            title=f"Trocar foto (somente nesta emissao) — {emp.nome}",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Todos", "*.*")],
            parent=self
        )
        if not path:
            return
        try:
            from src.utils.photo_utils import process_photo_3x4

            data = process_photo_3x4(path)
            self._foto_override[emp.id] = data
            self._update_thumb(emp)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao processar foto: {e}", parent=self)

    def _set_all(self, papel: str):
        for seg in self._papeis_vars.values():
            seg.set(papel)

    # ── Confirmacao ───────────────────────────────────────────

    def _confirm(self):
        fonts = get_fonts()

        # 1. nomes obrigatorios
        sem_nome = [
            (i, emp) for i, emp in enumerate(self._employees)
            if not self._nome_vars[emp.id].get().strip()
        ]
        if sem_nome:
            messagebox.showwarning("Aviso", "Todo funcionario precisa de nome preenchido.", parent=self)
            return

        # 2. telefones: digitos; vazio ok; preenchido precisa ter 11 (celular c/ DDD)
        tels_errados = []
        for emp in self._employees:
            raw = re.sub(r"\D", "", self._tel_vars[emp.id].get())
            if raw and len(raw) != 11:
                tels_errados.append(f"{self._nome_vars[emp.id].get().strip()} (telefone incompleto)")
        if tels_errados:
            messagebox.showwarning(
                "Aviso",
                "Telefone deve ter 11 digitos (DDD + numero) ou ficar vazio:\n\n" +
                "\n".join(tels_errados[:10]), parent=self
            )
            return

        # 3. setor obrigatorio
        setor = self._setor_var.get().strip() if self._setor_var is not None else ""
        if self._needs_setor and not setor:
            messagebox.showwarning("Aviso", "Informe o setor/departamento do lote.", parent=self)
            return

        # 4. matricula obrigatoria (validade curta — preenchida na hora)
        matriculas = {emp_id: var.get().strip() for emp_id, var in self._matricula_vars.items()}
        if self._needs_matricula:
            sem_mat = [
                self._nome_vars[emp_id].get().strip()
                for emp_id, val in matriculas.items() if not val
            ]
            if sem_mat:
                messagebox.showwarning(
                    "Aviso",
                    "Matricula obrigatoria (preenchida na emissao, nao fica salva):\n\n" +
                    "\n".join(sem_mat[:15]) + ("\n..." if len(sem_mat) > 15 else ""),
                    parent=self
                )
                return

        # escreve as edicoes nas COPIAS (nao toca o banco)
        for emp in self._employees:
            emp.nome = self._nome_vars[emp.id].get().strip()
            emp.funcao = self._funcao_vars[emp.id].get().strip() or None
            dig = re.sub(r"\D", "", self._tel_vars[emp.id].get())
            emp.telefone = dig if dig else None
            if emp.id in self._foto_override:
                emp.foto = self._foto_override[emp.id]

        papeis = {emp_id: seg.get() for emp_id, seg in self._papeis_vars.items()}
        self.selected = {
            "setor": setor,
            "papeis": papeis,
            "matriculas": matriculas,
            "employees": self._employees,
        }
        self.destroy()
