import customtkinter as ctk
import tkinter
from PIL import Image, ImageTk
from typing import Optional, Callable, List
from src.ui.styles import COLORS, FONTS


class PDFPreview(ctk.CTkFrame):
    """Preview do certificado - texto formatado com opção de visualizar PDF real."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["surface"], corner_radius=8, **kwargs)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.on_pdf_preview_callback: Optional[Callable] = None
        self._pdf_images: List = []

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=12)

        ctk.CTkLabel(
            header,
            text="Preview do Certificado",
            font=FONTS["heading"],
            text_color=COLORS["primary"]
        ).pack(side="left")

        self.btn_pdf = ctk.CTkButton(
            header,
            text="Ver PDF",
            font=FONTS["body_bold"],
            height=32,
            width=100,
            fg_color=COLORS["accent"],
            hover_color=COLORS["secondary"],
            command=self._on_pdf_preview
        )
        self.btn_pdf.pack(side="right")

        # Text preview (default)
        self.textbox = ctk.CTkTextbox(
            self,
            font=FONTS["body"],
            fg_color=COLORS["background"],
            text_color=COLORS["text"],
            corner_radius=6,
            wrap="word",
            activate_scrollbars=True
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.textbox.configure(state="disabled")

        # PDF canvas preview (hidden by default)
        self.pdf_container = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=6)
        self.pdf_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.pdf_container.grid_remove()
        self.pdf_container.grid_rowconfigure(0, weight=1)
        self.pdf_container.grid_columnconfigure(0, weight=1)

        self.pdf_canvas = tkinter.Canvas(
            self.pdf_container, bg="#F0F4F8",
            highlightthickness=0, bd=0
        )
        self.pdf_canvas.grid(row=0, column=0, sticky="nsew")
        self.pdf_canvas.bind("<MouseWheel>", lambda e: self.pdf_canvas.yview_scroll(int(-1 * (e.delta / 120) * 2.5), "units"))

        self.scrollbar_v = ctk.CTkScrollbar(
            self.pdf_container, orientation="vertical",
            command=self.pdf_canvas.yview
        )
        self.scrollbar_v.grid(row=0, column=1, sticky="ns")

        self.scrollbar_h = ctk.CTkScrollbar(
            self.pdf_container, orientation="horizontal",
            command=self.pdf_canvas.xview
        )
        self.scrollbar_h.grid(row=1, column=0, sticky="ew")

        self.pdf_canvas.configure(yscrollcommand=self._on_scroll_v, xscrollcommand=self.scrollbar_h.set)
        self.pdf_canvas.bind("<Configure>", self._on_canvas_configure)

        self.btn_voltar = ctk.CTkButton(
            self, text="Voltar ao texto",
            font=FONTS["body_bold"], height=28, width=120,
            fg_color=COLORS["secondary"], hover_color=COLORS["primary"],
            command=self._show_text
        )

        self._current_mode = "text"
        self._pdf_photo_images = []

    def _on_scroll_v(self, *args):
        self.scrollbar_v.set(*args)
        self.pdf_canvas.yview(*args)

    def _on_canvas_configure(self, event):
        self.pdf_canvas.configure(scrollregion=self.pdf_canvas.bbox("all"))

    def set_content(self, text: str):
        self._show_text()
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        self.textbox.configure(state="disabled")

    def show_pdf_image(self, pdf_path: str):
        if self._current_mode == "pdf":
            return

        try:
            import fitz

            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            canvas_width = self.pdf_canvas.winfo_width()
            if canvas_width < 100:
                canvas_width = 700

            self._pdf_images = []
            self._pdf_photo_images = []

            self.pdf_canvas.delete("all")
            y_offset = 10

            for page_num in range(total_pages):
                page = doc[page_num]
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                ratio = canvas_width / img.width
                new_width = int(img.width * ratio)
                new_height = int(img.height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)

                photo = ImageTk.PhotoImage(img)
                self._pdf_photo_images.append(photo)

                if total_pages > 1:
                    self.pdf_canvas.create_text(
                        10, y_offset,
                        text=f"Página {page_num + 1}/{total_pages}",
                        anchor="nw",
                        font=("Segoe UI", 9),
                        fill="#999999"
                    )
                    y_offset += 18

                self.pdf_canvas.create_image(10, y_offset, anchor="nw", image=photo)
                y_offset += new_height + 15

            doc.close()

            self.pdf_canvas.configure(scrollregion=self.pdf_canvas.bbox("all"))
            self.textbox.grid_remove()
            self.pdf_container.grid()
            self.btn_voltar.grid(row=2, column=0, pady=(0, 8))
            self._current_mode = "pdf"
        except Exception as e:
            self.set_content(f"Erro ao renderizar PDF: {e}")

    def _show_text(self):
        if self._current_mode == "pdf":
            self.pdf_container.grid_remove()
            self.btn_voltar.grid_forget()
            self.pdf_canvas.delete("all")
            self._pdf_images.clear()
            self._pdf_photo_images.clear()
            self.textbox.grid()
            self._current_mode = "text"

    def _on_pdf_preview(self):
        if self.on_pdf_preview_callback:
            self.on_pdf_preview_callback()

    def set_on_pdf_preview(self, callback: Callable):
        self.on_pdf_preview_callback = callback
