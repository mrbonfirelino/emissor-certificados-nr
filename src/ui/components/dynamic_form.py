import customtkinter as ctk
from typing import Dict, Callable, Optional, List, Any
from src.core.models import NRTemplate, NRTemplateExtraField
from src.ui.styles import COLORS, FONTS


class DynamicForm(ctk.CTkFrame):
    """Formulário dinâmico colapsável baseado nos campos extras do template do NR."""
    
    def __init__(
        self,
        master,
        template: NRTemplate = None,
        on_change: Callable[[Dict[str, Any]], None] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.template = template
        self.on_change = on_change
        self.field_widgets: Dict[str, ctk.CTkBaseClass] = {}
        self.field_vars: Dict[str, ctk.StringVar] = {}
        self._expanded = False
        self._build_form()

    def _build_form(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.field_widgets.clear()
        self.field_vars.clear()
        
        fonts = FONTS

        # Botão toggle
        self._toggle_btn = ctk.CTkButton(
            self,
            text="▶ Campos Específicos da NR (Opcionais)",
            font=fonts["heading"],
            text_color=COLORS["primary"],
            fg_color="transparent",
            hover_color=COLORS["background"],
            anchor="w",
            height=32,
            command=self._toggle
        )
        self._toggle_btn.pack(anchor="w", pady=(0, 4))

        # Container dos campos (inicialmente oculto)
        self._fields_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        if not self.template or not self.template.campos_extra:
            label = ctk.CTkLabel(
                self._fields_frame,
                text="Nenhum campo extra para este NR",
                font=fonts["small"],
                text_color=COLORS["muted"]
            )
            label.pack(pady=10)

    def _toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._fields_frame.pack(fill="x", pady=(0, 8))
            self._toggle_btn.configure(text="▼ Campos Específicos da NR (Opcionais)")
            # Cria campos apenas na primeira expansão
            if not self._fields_frame.winfo_children() or (
                len(self._fields_frame.winfo_children()) == 1 and 
                isinstance(self._fields_frame.winfo_children()[0], ctk.CTkLabel)
            ):
                self._create_fields()
        else:
            self._fields_frame.pack_forget()
            self._toggle_btn.configure(text="▶ Campos Específicos da NR (Opcionais)")

    def _create_fields(self):
        for widget in self._fields_frame.winfo_children():
            widget.destroy()
        
        if not self.template or not self.template.campos_extra:
            label = ctk.CTkLabel(
                self._fields_frame,
                text="Nenhum campo extra para este NR",
                font=FONTS["small"],
                text_color=COLORS["muted"]
            )
            label.pack(pady=10)
            return

        for field in self.template.campos_extra:
            self._create_field(field)

    def _create_field(self, field: NRTemplateExtraField):
        frame = ctk.CTkFrame(self._fields_frame, fg_color="transparent")
        frame.pack(fill="x", pady=6)
        
        label_text = f"{field.label}"
        if field.obrigatorio:
            label_text += " *"
        label = ctk.CTkLabel(frame, text=label_text, font=FONTS["body_bold"], text_color=COLORS["text"])
        label.pack(anchor="w")
        
        var = ctk.StringVar()
        self.field_vars[field.id] = var
        
        if field.tipo == "select" and field.opcoes:
            widget = ctk.CTkComboBox(
                frame,
                values=field.opcoes,
                variable=var,
                font=FONTS["body"],
                height=36,
                corner_radius=6,
                dropdown_font=FONTS["body"],
                command=lambda v, fid=field.id: self._on_change(fid, v)
            )
            widget.set(field.opcoes[0] if field.opcoes else "")
        elif field.tipo == "number":
            widget = ctk.CTkEntry(
                frame,
                textvariable=var,
                font=FONTS["body"],
                height=36,
                corner_radius=6,
                placeholder_text=field.placeholder
            )
            widget.bind("<KeyRelease>", lambda e, fid=field.id: self._validate_number(fid))
        else:
            widget = ctk.CTkEntry(
                frame,
                textvariable=var,
                font=FONTS["body"],
                height=36,
                corner_radius=6,
                placeholder_text=field.placeholder
            )
        
        widget.pack(fill="x", pady=(4, 0))
        self.field_widgets[field.id] = widget
        
        var.trace_add("write", lambda *args, fid=field.id: self._on_change(fid, var.get()))

    def _validate_number(self, field_id: str):
        var = self.field_vars[field_id]
        value = var.get()
        if value and not value.isdigit():
            var.set(''.join(c for c in value if c.isdigit()))

    def _on_change(self, field_id: str, value: str):
        if self.on_change:
            self.on_change(self.get_values())

    def set_template(self, template: NRTemplate):
        self.template = template
        self._expanded = False
        self._build_form()

    def get_values(self) -> Dict[str, Any]:
        values = {}
        for field_id, var in self.field_vars.items():
            values[field_id] = var.get()
        return values

    def set_values(self, values: Dict[str, Any]):
        for field_id, value in values.items():
            if field_id in self.field_vars:
                self.field_vars[field_id].set(str(value))

    def validate(self) -> tuple[bool, List[str]]:
        errors = []
        if not self.template:
            return True, errors
        
        for field in self.template.campos_extra:
            if field.obrigatorio:
                value = self.field_vars.get(field.id, ctk.StringVar()).get().strip()
                if not value:
                    errors.append(f"Campo obrigatório: {field.label}")
        return len(errors) == 0, errors

    def clear(self):
        for var in self.field_vars.values():
            var.set("")
