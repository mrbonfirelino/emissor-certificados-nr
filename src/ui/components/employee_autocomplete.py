import customtkinter as ctk
from typing import Callable, Optional, List
from src.core.models import Employee
from src.core.employee_repo import EmployeeRepository
from src.ui.styles import COLORS, FONTS


class EmployeeAutocomplete(ctk.CTkFrame):
    """Componente de autocomplete para busca de funcionários."""
    
    def __init__(
        self,
        master,
        employee_repo: EmployeeRepository,
        on_select: Callable[[Employee], None] = None,
        placeholder: str = "🔍 Digite nome ou CPF do funcionário...",
        width: int = 400,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.employee_repo = employee_repo
        self.on_select = on_select
        self.selected_employee: Optional[Employee] = None
        self._dropdown_visible = False
        self._dropdown_window = None
        
        # Entry principal
        self.entry_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.entry_var,
            placeholder_text=placeholder,
            width=width,
            height=36,
            font=FONTS["body"],
            corner_radius=6
        )
        self.entry.pack(fill="x")
        
        # Bind events
        self.entry.bind("<KeyRelease>", self._on_keyrelease)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<Down>", self._on_down)
        self.entry.bind("<Up>", self._on_up)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Escape>", lambda e: self._hide_dropdown())
        self.entry.bind("<Button-1>", self._on_click)
        
        # Dropdown listbox (usando CTkScrollableFrame)
        self.dropdown_frame = None
        self.dropdown_buttons: List[ctk.CTkButton] = []
        self._selected_index = -1

    def _on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"):
            return
        query = self.entry_var.get().strip()
        if len(query) >= 2:
            self._show_dropdown(query)
        else:
            self._hide_dropdown()

    def _on_focus_in(self, event):
        query = self.entry_var.get().strip()
        if len(query) >= 2:
            self._show_dropdown(query)

    def _on_focus_out(self, event):
        # Delay para permitir clique no dropdown
        self.after(200, self._check_hide_dropdown)

    def _on_click(self, event):
        if self.entry.cget("state") == "readonly":
            self.clear()

    def _check_hide_dropdown(self):
        if self.dropdown_frame and not self.dropdown_frame.winfo_containing(self.winfo_pointerxy()[0], self.winfo_pointerxy()[1]):
            self._hide_dropdown()

    def _on_down(self, event):
        if self.dropdown_buttons:
            self._selected_index = min(self._selected_index + 1, len(self.dropdown_buttons) - 1)
            self._update_selection()

    def _on_up(self, event):
        if self.dropdown_buttons:
            self._selected_index = max(self._selected_index - 1, 0)
            self._update_selection()

    def _on_return(self, event):
        if self.dropdown_buttons and 0 <= self._selected_index < len(self.dropdown_buttons):
            self._select_employee(self._selected_index)

    def _update_selection(self):
        for i, btn in enumerate(self.dropdown_buttons):
            if i == self._selected_index:
                btn.configure(fg_color=COLORS["primary"])
            else:
                btn.configure(fg_color="transparent")

    def _show_dropdown(self, query: str):
        if self.dropdown_frame:
            self.dropdown_frame.destroy()
        
        employees = self.employee_repo.search(query, limit=10)
        if not employees:
            self._hide_dropdown()
            return
        
        self._selected_index = -1
        
        # Cria frame dropdown posicionado abaixo do entry
        self.dropdown_frame = ctk.CTkToplevel(self)
        self.dropdown_frame.overrideredirect(True)
        self.dropdown_frame.attributes("-topmost", True)
        
        # Posiciona abaixo do entry
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        width = self.entry.winfo_width()
        self.dropdown_frame.geometry(f"{width}x{min(len(employees) * 40 + 10, 300)}+{x}+{y}")
        
        scroll = ctk.CTkScrollableFrame(self.dropdown_frame, fg_color=COLORS["surface"], corner_radius=6)
        scroll.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.dropdown_buttons = []
        for i, emp in enumerate(employees):
            btn = ctk.CTkButton(
                scroll,
                text=f"{emp.nome}  ({emp.cpf})",
                font=FONTS["body"],
                fg_color="transparent",
                text_color=COLORS["text"],
                anchor="w",
                height=36,
                corner_radius=4,
                command=lambda idx=i: self._select_employee(idx)
            )
            btn.pack(fill="x", padx=4, pady=2)
            btn.bind("<Enter>", lambda e, idx=i: self._on_hover(idx))
            self.dropdown_buttons.append(btn)
        
        self._dropdown_visible = True

    def _on_hover(self, index: int):
        self._selected_index = index
        self._update_selection()

    def _select_employee(self, index: int):
        if 0 <= index < len(self.dropdown_buttons):
            employees = self.employee_repo.search(self.entry_var.get().strip(), limit=10)
            if index < len(employees):
                emp = employees[index]
                self.selected_employee = emp
                self.entry_var.set(f"{emp.nome} ({emp.cpf})")
                self.entry.configure(state="readonly")
                self._hide_dropdown()
                if self.on_select:
                    self.on_select(emp)

    def _hide_dropdown(self):
        if self.dropdown_frame:
            try:
                self.dropdown_frame.destroy()
            except Exception:
                pass
            self.dropdown_frame = None
            self.dropdown_buttons = []
            self._dropdown_visible = False
            self._selected_index = -1

    def clear(self):
        """Limpa seleção e permite nova busca."""
        self.selected_employee = None
        self.entry_var.set("")
        self.entry.configure(state="normal")
        self.entry.focus()

    def get_selected(self) -> Optional[Employee]:
        return self.selected_employee

    def set_employee(self, employee: Employee):
        """Define funcionário programaticamente."""
        self.selected_employee = employee
        self.entry_var.set(f"{employee.nome} ({employee.cpf})")
        self.entry.configure(state="readonly")