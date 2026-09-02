"""
Tela de digitalizacao e insercao direta de certificados assinados (roadmap 2.9).

Fluxo:
1. Origem da pagina: escanear (WIA) ou escolher arquivo (foto do celular, JPG/PNG/PDF)
2. Ajustes (so para imagens): girar +-90, brilho, contraste, recorte por arraste
3. Multi-pagina: cada pagina adicionada entra na lista; ao confirmar, imagens
   viram UM unico PDF anexado ao registro (PDF original entra como pagina unica)
"""

import io
import tkinter as tk
from tkinter import messagebox, filedialog

import customtkinter as ctk

from src.ui.styles import COLORS, get_fonts


class ScanDialog(ctk.CTkToplevel):
    """Atributo `resultado` apos fechar: (pdf_bytes, tipo) ou None."""

    def __init__(self, master, cert):
        super().__init__(master)
        self.cert = cert
        self.resultado = None

        self._paginas = []      # list[dict]: {"kind": "image"|"pdf", "pil": Image | bytes}
        self._pil = None        # PIL da pagina em edicao
        self._pil_original = None
        self._crop_rect = None  # (x0,y0,x1,y1) em coords da imagem original
        self._brilho = ctk.DoubleVar(value=1.0)
        self._contraste = ctk.DoubleVar(value=1.0)
        self._arrasto = None    # id do retangulo do canvas
        self._sel_ini = None

        self.title(f"Digitalizar — {cert.cert_number}")
        w, h = 880, 700
        self.geometry(f"{w}x{h}")
        self.minsize(780, 560)
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (w // 2)
        y = master.winfo_rooty() + (master.winfo_height() // 2) - (h // 2)
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        fonts = get_fonts()
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=14)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(2, weight=1)

        # ── Cabecalho + origem ──
        topo = ctk.CTkFrame(content, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(topo, text=f"Digitalizar certificado assinado — {cert.funcionario_nome}",
                     font=fonts["heading"], text_color=COLORS["primary"]).pack(side="left")

        acoes = ctk.CTkFrame(content, fg_color="transparent")
        acoes.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(acoes, text="Escanear no scanner", font=fonts["body_bold"], height=32,
                      fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                      command=self._escanear).pack(side="left", padx=(0, 8))
        ctk.CTkButton(acoes, text="Escolher arquivo / foto", font=fonts["body_bold"], height=32,
                      fg_color=COLORS["accent"], hover_color=COLORS["secondary"],
                      command=self._escolher_arquivo).pack(side="left", padx=(0, 8))
        self.lbl_paginas = ctk.CTkLabel(acoes, text="Nenhuma pagina", font=fonts["small"],
                                        text_color=COLORS["muted"])
        self.lbl_paginas.pack(side="left", padx=10)
        self.btn_remover = ctk.CTkButton(acoes, text="Remover ultima", width=110, height=30,
                                         font=fonts["small"], fg_color=COLORS["muted"],
                                         hover_color=COLORS["text_secondary"],
                                         state="disabled", command=self._remover_ultima)
        self.btn_remover.pack(side="right")

        # ── Preview (canvas) ──
        prev_frame = ctk.CTkFrame(content, fg_color=COLORS["surface"], corner_radius=8)
        prev_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        prev_frame.grid_rowconfigure(0, weight=1)
        prev_frame.grid_columnconfigure(0, weight=1)
        self._canvas = tk.Canvas(prev_frame, bg="#F0F4F8", highlightthickness=0,
                                 cursor="crosshair")
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._canvas.bind("<ButtonPress-1>", self._sel_inicio)
        self._canvas.bind("<B1-Motion>", self._sel_arrasto)
        self._canvas.bind("<ButtonRelease-1>", self._sel_fim)
        self._bind_wheel()

        # ── Ajustes ──
        ajustes = ctk.CTkFrame(content, fg_color="transparent")
        ajustes.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkButton(ajustes, text="Girar \u2190", width=70, height=28, font=fonts["small"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                      command=lambda: self._girar(-90)).pack(side="left", padx=2)
        ctk.CTkButton(ajustes, text="Girar \u2192", width=70, height=28, font=fonts["small"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
                      command=lambda: self._girar(90)).pack(side="left", padx=2)
        ctk.CTkLabel(ajustes, text="  Brilho:", font=fonts["small"],
                     text_color=COLORS["text"]).pack(side="left", padx=(10, 2))
        self._slider_brilho = ctk.CTkSlider(ajustes, from_=0.5, to=1.5, number_of_steps=20,
                                            variable=self._brilho, width=110,
                                            command=lambda _v: self._render())
        self._slider_brilho.pack(side="left", padx=2)
        ctk.CTkLabel(ajustes, text="  Contraste:", font=fonts["small"],
                     text_color=COLORS["text"]).pack(side="left", padx=(8, 2))
        self._slider_contraste = ctk.CTkSlider(ajustes, from_=0.5, to=2.0, number_of_steps=30,
                                               variable=self._contraste, width=110,
                                               command=lambda _v: self._render())
        self._slider_contraste.pack(side="left", padx=2)
        self.btn_crop = ctk.CTkButton(ajustes, text="Recortar selecao", width=120, height=28,
                                      font=fonts["small"], fg_color=COLORS["warning"],
                                      hover_color="#BF5300", state="disabled",
                                      command=self._aplicar_crop)
        self.btn_crop.pack(side="left", padx=10)
        self.btn_reset = ctk.CTkButton(ajustes, text="Desfazer ajustes", width=110, height=28,
                                       font=fonts["small"], fg_color=COLORS["muted"],
                                       hover_color=COLORS["text_secondary"],
                                       state="disabled", command=self._reset_ajustes)
        self.btn_reset.pack(side="left", padx=2)
        self.lbl_hint = ctk.CTkLabel(ajustes, text="arraste no preview para recortar",
                                     font=fonts["tiny"], text_color=COLORS["muted"])
        self.lbl_hint.pack(side="right")

        # ── Rodape ──
        rodape = ctk.CTkFrame(content, fg_color="transparent")
        rodape.grid(row=4, column=0, sticky="ew")
        ctk.CTkButton(rodape, text="Cancelar", font=fonts["body_bold"], height=34,
                      fg_color=COLORS["muted"], hover_color=COLORS["text_secondary"],
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(rodape, text="Confirmar Insercao", font=fonts["body_bold"], height=34,
                      fg_color=COLORS["success"], hover_color="#256B28",
                      command=self._confirmar).pack(side="right")

        self._mostrar_placeholder()
        self.after(50, self.focus_force)

    # ── Origens ──────────────────────────────────────────────

    def _escanear(self):
        try:
            from src.utils.scanner_wia import scan_one_page, ScanError
        except Exception as e:
            messagebox.showerror("Digitalizar", f"{e}", parent=self)
            return
        try:
            data = scan_one_page()
        except ScanError as e:
            from src.utils.error_log import log_error
            log_error("scan-wia", e)
            messagebox.showerror("Digitalizar",
                                 f"{e}\n\nUse 'Escolher arquivo / foto' como alternativa.", parent=self)
            return
        if not data:
            return  # cancelou no dialogo do scanner
        self._adicionar_pagina_imagem(data)

    def _escolher_arquivo(self):
        path = filedialog.askopenfilename(
            title="Escolher foto/documento do certificado assinado",
            filetypes=[("Imagens e PDF", "*.jpg *.jpeg *.png *.bmp *.webp *.pdf"), ("Todos", "*.*")],
            parent=self,
        )
        if not path:
            return
        try:
            if path.lower().endswith(".pdf"):
                with open(path, "rb") as f:
                    self._paginas.append({"kind": "pdf", "data": f.read()})
                self._atualizar_estado(f"pagina PDF adicionada ({len(self._paginas)} pag)")
            else:
                with open(path, "rb") as f:
                    self._adicionar_pagina_imagem(f.read(), origem=path)
        except Exception as e:
            messagebox.showerror("Digitalizar", f"Erro ao abrir arquivo: {e}", parent=self)

    def _adicionar_pagina_imagem(self, data: bytes, origem: str = "scanner"):
        from PIL import Image

        try:
            pil = Image.open(io.BytesIO(data))
            pil.load()
        except Exception as e:
            messagebox.showerror("Digitalizar", f"Imagem invalida ({origem}): {e}", parent=self)
            return
        # pagina anterior em edicao vira finalizada "como esta"
        self._finalizar_edicao()
        self._pil_original = pil
        self._pil = pil.copy()
        self._paginas.append({"kind": "image", "pil": self._pil})
        self._brilho.set(1.0)
        self._contraste.set(1.0)
        self._crop_rect = None
        self._atualizar_estado(f"pagina {len(self._paginas)} em edicao ({origem})")
        self._render()

    # ── Edicao / ajustes ─────────────────────────────────────

    def _finalizar_edicao(self):
        """Aplica brilho/contraste pendentes na PIL da pagina em edicao."""
        if self._pil is None:
            return
        try:
            b, c = self._brilho.get(), self._contraste.get()
            if b != 1.0 or c != 1.0:
                from PIL import ImageEnhance
                img = self._pil
                if b != 1.0:
                    img = ImageEnhance.Brightness(img).enhance(b)
                if c != 1.0:
                    img = ImageEnhance.Contrast(img).enhance(c)
                self._pil = img
        except Exception:
            pass

    def _girar(self, graus: int):
        if self._pil is None:
            return
        # gira a base (original ja com crop aplicado) e re-renderiza com brilho/contraste
        self._finalizar_edicao()
        self._pil = self._pil.rotate(-graus, expand=True)
        self._pil_original = self._pil
        self._brilho.set(1.0)
        self._contraste.set(1.0)
        self._crop_rect = None
        self._render()

    def _aplicar_crop(self):
        if self._pil is None or not self._crop_rect:
            return
        x0, y0, x1, y1 = self._crop_rect
        self._finalizar_edicao()
        self._pil = self._pil.crop((x0, y0, x1, y1))
        self._pil_original = self._pil
        self._brilho.set(1.0)
        self._contraste.set(1.0)
        self._crop_rect = None
        self._canvas.delete("sel")
        self.btn_crop.configure(state="disabled")
        self._render()

    def _reset_ajustes(self):
        if self._pil_original is None:
            return
        self._pil = self._pil_original.copy()
        self._brilho.set(1.0)
        self._contraste.set(1.0)
        self._crop_rect = None
        self._canvas.delete("sel")
        self.btn_crop.configure(state="disabled")
        self._render()

    # ── Preview (canvas) ─────────────────────────────────────

    def _mostrar_placeholder(self):
        self._canvas.delete("all")
        self._canvas.create_text(
            self._canvas.winfo_width() // 2 or 400, self._canvas.winfo_height() // 2 or 250,
            text="Nenhuma pagina.\nUse 'Escanear no scanner' ou 'Escolher arquivo / foto'.",
            fill="#999999", font=("Segoe UI", 12), justify="center",
        )

    def _img_p_display(self):
        """PIL a exibir = original-da-pagina com brilho/contraste atuais (nao muta a pagina)."""
        from PIL import ImageEnhance

        img = self._pil_original
        if img is None:
            return None
        b, c = self._brilho.get(), self._contraste.get()
        if b != 1.0:
            img = ImageEnhance.Brightness(img).enhance(b)
        if c != 1.0:
            img = ImageEnhance.Contrast(img).enhance(c)
        return img

    def _render(self):
        self._canvas.delete("all")
        img = self._img_p_display()
        if img is None:
            self._mostrar_placeholder()
            self._reset_enabled()
            return
        self._reset_enabled(True)
        cw = max(self._canvas.winfo_width(), 100)
        ch = max(self._canvas.winfo_height(), 100)
        iw, ih = img.size
        escala = min(cw / iw, ch / ih, 1.0)
        dw, dh = int(iw * escala), int(ih * escala)
        ox, oy = (cw - dw) // 2, (ch - dh) // 2
        disp = img.resize((dw, dh))
        from PIL import ImageTk
        self._tkimg = ImageTk.PhotoImage(disp)
        self._canvas.create_image(ox, oy, anchor="nw", image=self._tkimg)
        self._offset = (ox, oy, escala)

    def _reset_enabled(self, on: bool = False):
        estado = "normal" if on else "disabled"
        self._slider_brilho.configure(state=estado)
        self._slider_contraste.configure(state=estado)
        self.btn_reset.configure(state=estado)
        if not on:
            self.btn_crop.configure(state="disabled")

    # selecao de recorte
    def _sel_inicio(self, e):
        if self._pil_original is None:
            return
        self._canvas.delete("sel")
        self._sel_ini = (e.x, e.y)
        self._arrasto = self._canvas.create_rectangle(
            e.x, e.y, e.x, e.y, outline="#E65100", width=2, dash=(4, 2), tags="sel")

    def _sel_arrasto(self, e):
        if self._arrasto is None:
            return
        x0, y0 = self._sel_ini
        self._canvas.coords(self._arrasto, x0, y0, e.x, e.y)

    def _sel_fim(self, e):
        if self._arrasto is None:
            return
        x0, y0 = self._sel_ini
        self._sel_ini = None
        self._arrasto = None
        ox, oy, esc = self._offset
        # converte coords do canvas -> coords da imagem original
        ix0, iy0 = int((min(x0, e.x) - ox) / esc), int((min(y0, e.y) - oy) / esc)
        ix1, iy1 = int((max(x0, e.x) - ox) / esc), int((max(y0, e.y) - oy) / esc)
        iw, ih = self._pil_original.size
        ix0, iy0 = max(0, ix0), max(0, iy0)
        ix1, iy1 = min(iw, ix1), min(ih, iy1)
        if ix1 - ix0 < 10 or iy1 - iy0 < 10:
            self._canvas.delete("sel")
            self._crop_rect = None
            self.btn_crop.configure(state="disabled")
            return
        self._crop_rect = (ix0, iy0, ix1, iy1)
        self.btn_crop.configure(state="normal")

    def _bind_wheel(self):
        def _redim(e=None):
            self._render()
        self._canvas.bind("<Configure>", lambda e: self._after_render(e))
        self._after_cb = None

    def _after_render(self, _e):
        if self._after_cb:
            try:
                self.after_cancel(self._after_cb)
            except Exception:
                pass
        self._after_cb = self.after(80, self._render)

    # ── Estado / confirmacao ─────────────────────────────────

    def _remover_ultima(self):
        if not self._paginas:
            return
        self._paginas.pop()
        self._pil = None
        self._pil_original = None
        self._crop_rect = None
        if self._paginas and self._paginas[-1]["kind"] == "image":
            self._pil_original = self._paginas[-1]["pil"]
            self._pil = self._pil_original.copy()
            self._atualizar_estado(f"pagina {len(self._paginas)} em edicao")
        else:
            self._atualizar_estado()
        self._render()

    def _atualizar_estado(self, msg: str = ""):
        n = len(self._paginas)
        self.lbl_paginas.configure(text=f"{n} pagina(s)" + (f" — {msg}" if msg else ""))
        self.btn_remover.configure(state="normal" if n else "disabled")

    def _confirmar(self):
        if not self._paginas:
            messagebox.showwarning("Digitalizar", "Adicione ao menos uma pagina.", parent=self)
            return
        self._finalizar_edicao()
        try:
            if len(self._paginas) == 1 and self._paginas[0]["kind"] == "pdf":
                data = self._paginas[0]["data"]
                tipo = "pdf"
            else:
                from src.utils.scanner_wia import pages_to_pdf_bytes

                bufs = []
                for p in self._paginas:
                    if p["kind"] == "pdf":
                        messagebox.showwarning(
                            "Digitalizar",
                            "Nao e possivel combinar um PDF com imagens na mesma digitalizacao.\n"
                            "Use o PDF sozinho ou converta as demais paginas em fotos.",
                            parent=self)
                        return
                    b = io.BytesIO()
                    p["pil"].convert("RGB").save(b, format="PNG")
                    bufs.append(b.getvalue())
                data = pages_to_pdf_bytes(bufs)
                tipo = "pdf"
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("scan-confirmar", e)
            messagebox.showerror("Digitalizar", f"Erro ao montar o documento: {e}", parent=self)
            return
        self.resultado = (data, tipo)
        self.destroy()
