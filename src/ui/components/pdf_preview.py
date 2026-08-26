import customtkinter as ctk
from typing import Optional
from src.ui.styles import COLORS, FONTS


class PDFPreview(ctk.CTkFrame):
    """Preview do certificado (placeholder - mostra texto formatado)."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["surface"], corner_radius=8, **kwargs)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=12)
        
        ctk.CTkLabel(
            header,
            text="📄 Preview do Certificado",
            font=FONTS["heading"],
            text_color=COLORS["primary"]
        ).pack(side="left")
        
        self.btn_generate = ctk.CTkButton(
            header,
            text="Gerar PDF",
            font=FONTS["body_bold"],
            height=32,
            width=120,
            fg_color=COLORS["success"],
            hover_color="#256B28",
            command=self._on_generate
        )
        self.btn_generate.pack(side="right")
        
        # Área de preview (scrollable text)
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
        
        self.on_generate_callback = None

    def _on_generate(self):
        if self.on_generate_callback:
            self.on_generate_callback()

    def set_content(self, text: str):
        """Define conteúdo do preview."""
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        self.textbox.configure(state="disabled")

    def set_on_generate(self, callback):
        self.on_generate_callback = callback