"""
Revisao da emissao de CRACHAS (template_type 'cracha').

- Data de emissao global (default: hoje), editavel
- Por funcionario: NRs disponiveis (somente certificados existentes,
  vigentes por NR) com checkbox — pre-marcadas as MAX_NRS mais recentes;
  NRs VENCIDAS aparecem desabilitadas e nunca sao incluidas (v1.15.1)
- ASO vigente exibido (numero + validade)
- Funcionario BLOQUEADO (sem foto / sem NR valida / ASO vencido) fica com
  card vermelho e é excluido da emissao (v1.15.1); .blocked_msgs lista os
  motivos no formato "Nome: motivo e motivo"
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

        # v1.15.1: motivos de bloqueio (sem foto / sem NR valida / ASO vencido)
        from src.core.badge_service import cracha_block_reasons
        self._blocked = {}
        self.blocked_msgs: list = []
        for emp in employees:
            motivos = cracha_block_reasons(
                emp, self._certs_por_emp.get(emp.id, []), self._aso_por_emp.get(emp.id)
            )
            if motivos:
                self._blocked[emp.id] = motivos
                self.blocked_msgs.append(f"{emp.nome}: " + " e ".join(motivos))

        self._nrs_sel = {}      # emp_id -> {nr_code: BooleanVar}
        self._build_ui()

        self.after(150, lambda: self.focus_force())

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        fonts = get_fonts()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # topo: data de emissao global + tamanho do cartao
        top = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        row_data = ctk.CTkFrame(top, fg_color="transparent")
        row_data.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            row_data, text="Data de Emissão do Crachá (dd/mm/aaaa):",
            font=fonts["body_bold"], text_color=COLORS["text"]
        ).pack(side="left", padx=(0, 8))

        self._emissao_var = ctk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        ctk.CTkEntry(
            row_data, textvariable=self._emissao_var, width=120, font=fonts["body"]
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            row_data,
            text=(f"Marque até {self.max_nrs} NRs por funcionário "
                  "(somente treinamentos válidos — NRs vencidas não entram)"),
            font=fonts["small"], text_color=COLORS["muted"]
        ).pack(side="left", padx=(0, 16))

        row_tam = ctk.CTkFrame(top, fg_color="transparent")
        row_tam.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkLabel(
            row_tam, text="Tamanho do cartão:",
            font=fonts["body_bold"], text_color=COLORS["text"]
        ).pack(side="left", padx=(0, 8))

        self._tamanho_var = ctk.StringVar(value="Tamanho real")
        ctk.CTkSegmentedButton(
            row_tam,
            values=["Tamanho real", "Reduzido 86x54mm"],
            variable=self._tamanho_var,
            font=fonts["small"],
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["secondary"],
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            row_tam, text="Impressão em folha A4 com guia de corte (vários por folha)",
            font=fonts["small"], text_color=COLORS["muted"]
        ).pack(side="left")

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
        from src.core.badge_service import _dias_ok
        fonts = get_fonts()

        bloqueado = emp.id in self._blocked
        card = ctk.CTkFrame(
            self._scroll, fg_color=COLORS["surface"], corner_radius=10,
            border_width=1 if bloqueado else 0,
            border_color=COLORS["error"] if bloqueado else None,
        )
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

        # coluna direita
        right = ctk.CTkFrame(card, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nw", padx=(8, 12), pady=10)

        if bloqueado:
            # v1.15.1: funcionario bloqueado nao gera cracha
            self._nrs_sel[emp.id] = {}
            ctk.CTkLabel(
                right, text="BLOQUEADO — " + " e ".join(self._blocked[emp.id]),
                font=fonts["body_bold"], text_color=COLORS["error"],
                wraplength=420, justify="left"
            ).pack(anchor="w", pady=6)
            return

        certs = self._certs_por_emp.get(emp.id, [])
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

        validas = 0  # pre-marca somente entre as NRs validas
        for i, cert in enumerate(certs):
            valida = _dias_ok(cert.get("dias_para_vencer"))
            if valida:
                pre = validas < self.max_nrs
                validas += 1
            else:
                pre = False
            var = ctk.BooleanVar(value=pre)
            if valida:
                cb = ctk.CTkCheckBox(
                    grid, text=f"{cert['nr_code']} (vence {self._br(cert.get('data_validade'))[:5]})",
                    variable=var, font=fonts["small"],
                    command=lambda e=emp.id, v=var: self._nr_toggled(e, v)
                )
            else:
                # v1.15.1: NR vencida nunca entra no cracha
                cb = ctk.CTkCheckBox(
                    grid, text=f"{cert['nr_code']} (vencida)",
                    variable=var, font=fonts["small"],
                    text_color=COLORS["muted"], state="disabled"
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

        # v1.15.1: bloqueados ficam de fora da emissao
        elegiveis = [emp for emp in self.employees if emp.id not in self._blocked]
        if not elegiveis:
            messagebox.showerror(
                "Todos bloqueados",
                "Nenhum funcionário selecionado pode gerar crachá:\n\n"
                + "\n".join(self.blocked_msgs),
                parent=self
            )
            return

        nrs = {}
        sem_nr = []
        for emp in elegiveis:
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
            "employees": elegiveis,
            "tamanho": "reduzido" if self._tamanho_var.get() == "Reduzido 86x54mm" else "real",
        }
        self.destroy()

    @staticmethod
    def _br(iso: str) -> str:
        if not iso or len(iso) < 10:
            return "—"
        return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
