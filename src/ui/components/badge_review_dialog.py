"""
Revisao da emissao de CRACHAS (template_type 'cracha').

- Data de emissao global (default: hoje), editavel
- Por funcionario: NRs disponiveis (somente certificados existentes,
  vigentes por NR) com checkbox — pre-marcadas as MAX_NRS mais recentes
- ASO vigente exibido (numero + validade)
Retorna em .selected: {'data_emissao': ISO, 'nrs': {emp_id: [nr,...]}, 'employees': [...]}
ou None se cancelado.
"""

from datetime import date, datetime
import customtkinter as ctk
from tkinter import messagebox

from src.ui.styles import COLORS, get_fonts


class BadgeReviewDialog(ctk.CTkToplevel):

    def __init__(self, master, employees: list, template: dict):
        super().__init__(master)
        self.title("Revisão — Emissão de Crachás")
        self.geometry("920x660")
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)

        self.employees = employees
        self.template = template
        self.max_nrs = int(template.get("max_nrs", 8))
        self.selected = None

        # dados de certificados/ASO (vigentes por NR / por funcionario)
        from src.core.history_repo import HistoryRepository
        from src.core.aso_repo import AsoRepository
        try:
            certs = HistoryRepository().get_certificates_with_expiration(only_latest=True)
        except Exception:
            certs = []
        try:
            asos = AsoRepository().get_asos_with_expiration(only_latest=True)
        except Exception:
            asos = []

        self._certs_por_emp = {}
        for c in certs:
            self._certs_por_emp.setdefault(c["employee_id"], []).append(c)
        for lst in self._certs_por_emp.values():
            lst.sort(key=lambda c: (c.get("data_fim") or "", c.get("cert_number") or ""), reverse=True)

        self._aso_por_emp = {a["employee_id"]: a for a in asos}

        self._nrs_sel = {}      # emp_id -> {nr_code: BooleanVar}
        self._build_ui()

        self.after(150, lambda: self.focus_force())

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        fonts = get_fonts()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # topo: data de emissao global
        top = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            top, text="Data de Emissão do Crachá (dd/mm/aaaa):",
            font=fonts["body_bold"], text_color=COLORS["text"]
        ).pack(side="left", padx=(16, 8), pady=12)

        self._emissao_var = ctk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        ctk.CTkEntry(
            top, textvariable=self._emissao_var, width=120, font=fonts["body"]
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            top, text=f"Marque até {self.max_nrs} NRs por funcionário (somente treinamentos existentes)",
            font=fonts["small"], text_color=COLORS["muted"]
        ).pack(side="left", padx=(0, 16))

        # meio: cards por funcionario
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)
        self._scroll.grid_columnconfigure(0, weight=1)

        for i, emp in enumerate(self.employees):
            self._create_emp_card(emp, i)

        # rodape
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 16))

        ctk.CTkLabel(
            foot, text="A emissão definitiva grava o número do crachá no histórico.",
            font=fonts["small"], text_color=COLORS["muted"]
        ).pack(side="left")

        ctk.CTkButton(
            foot, text="Cancelar", width=100, height=34, font=fonts["body"],
            fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            foot, text="Gerar", width=100, height=34, font=fonts["body_bold"],
            fg_color=COLORS["success"], hover_color="#256B28",
            command=self._confirmar
        ).pack(side="right")

    def _create_emp_card(self, emp, idx: int):
        fonts = get_fonts()
        card = ctk.CTkFrame(self._scroll, fg_color=COLORS["surface"], corner_radius=10)
        card.grid(row=idx, column=0, sticky="ew", pady=4)
        card.grid_columnconfigure(1, weight=1)

        # coluna esquerda: foto + nome + ASO
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nw", padx=(12, 8), pady=10)

        lbl_foto = ctk.CTkLabel(left, text="sem\nfoto", width=34)
        lbl_foto.grid(row=0, column=0, rowspan=3, padx=(0, 8))
        self._render_thumb(emp, lbl_foto)

        ctk.CTkLabel(
            left, text=emp.nome, font=fonts["body_bold"],
            text_color=COLORS["primary"], wraplength=200, justify="left"
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            left, text=emp.funcao or "—", font=fonts["small"],
            text_color=COLORS["text_secondary"]
        ).grid(row=1, column=1, sticky="w")

        aso = self._aso_por_emp.get(emp.id)
        if aso:
            aso_txt = f"ASO {aso['cert_number']} — vence {self._br(aso.get('data_validade'))}"
        else:
            aso_txt = "sem ASO"
        ctk.CTkLabel(
            left, text=aso_txt, font=fonts["small"],
            text_color=COLORS["text_secondary"]
        ).grid(row=2, column=1, sticky="w")

        # coluna direita: checkboxes das NRs
        certs = self._certs_por_emp.get(emp.id, [])
        right = ctk.CTkFrame(card, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nw", padx=(8, 12), pady=10)

        if not certs:
            ctk.CTkLabel(
                right, text="nenhuma NR encontrada para este funcionário",
                font=fonts["small"], text_color=COLORS["muted"]
            ).pack(anchor="w", pady=6)
            self._nrs_sel[emp.id] = {}
            return

        sel = {}
        self._nrs_sel[emp.id] = sel
        grid = ctk.CTkFrame(right, fg_color="transparent")
        grid.pack(anchor="w")
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1)

        for i, cert in enumerate(certs):
            var = ctk.BooleanVar(value=i < self.max_nrs)
            cb = ctk.CTkCheckBox(
                grid, text=f"{cert['nr_code']} (vence {self._br(cert.get('data_validade'))[:5]})",
                variable=var, font=fonts["small"],
                command=lambda e=emp.id, v=var: self._nr_toggled(e, v)
            )
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 14), pady=3)
            sel[cert["nr_code"]] = var

    def _render_thumb(self, emp, lbl):
        foto = getattr(emp, "foto", None)
        if not foto:
            return
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
        except Exception:
            pass

    # ── interacao ─────────────────────────────────────────────

    def _nr_toggled(self, emp_id: int, var: ctk.BooleanVar):
        if not var.get():
            return
        sel = self._nrs_sel.get(emp_id, {})
        marcadas = [nr for nr, v in sel.items() if v.get()]
        if len(marcadas) > self.max_nrs:
            var.set(False)
            messagebox.showwarning(
                "Limite de NRs",
                f"Este crachá comporta no máximo {self.max_nrs} NRs.\n"
                "Desmarque uma para marcar outra.",
                parent=self
            )

    def _confirmar(self):
        fonts = get_fonts()

        bruto = self._emissao_var.get().strip()
        try:
            emissao_iso = datetime.strptime(bruto, "%d/%m/%Y").date().isoformat()
        except ValueError:
            messagebox.showerror("Data inválida", "Data de emissão inválida (use dd/mm/aaaa).", parent=self)
            return

        nrs = {}
        sem_nr = []
        for emp in self.employees:
            sel = self._nrs_sel.get(emp.id, {})
            marcadas = [nr for nr, v in sel.items() if v.get()]
            nrs[emp.id] = marcadas
            if not marcadas:
                sem_nr.append(emp.nome)

        if sem_nr:
            resp = messagebox.askyesno(
                "Funcionários sem NR",
                "Sem NR marcada (o crachá sairá sem tabela de capacitações) para:\n\n"
                + "\n".join(sem_nr) + "\n\nContinuar mesmo assim?",
                parent=self
            )
            if not resp:
                return

        self.selected = {
            "data_emissao": emissao_iso,
            "nrs": nrs,
            "employees": list(self.employees),
        }
        self.destroy()

    @staticmethod
    def _br(iso: str) -> str:
        if not iso or len(iso) < 10:
            return "—"
        return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
