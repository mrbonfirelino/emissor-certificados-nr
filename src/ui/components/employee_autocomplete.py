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
        self._employees_cache: List[Employee] = []
        self._watchdog_id = None

        # dropdown nunca fica orfao: fecha ao minimizar e acompanha a janela ao mover
        try:
            top = self.winfo_toplevel()
            top.bind("<Unmap>", self._on_root_unmap, add="+")
            top.bind("<Configure>", self._on_root_configure, add="+")
        except Exception:
            pass

        # clique FORA do campo/dropdown fecha a lista.
        # NOTA: CTk proibe bind_all nos widgets dele ("could result in undefined
        # behavior"), entao usamos binding direto no Tcl com %W (caminho do widget
        # clicado) — permanente e inerte quando a lista esta fechada.
        try:
            cb = self.register(self._on_global_click)
            self.tk.call("bind", "all", "<Button-1>", f"+{cb} %W")
        except Exception:
            pass

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
        # revalida apos pausa curta: clicar num item muda o foco por um instante
        self.after(250, self._check_focus)

    def _check_focus(self):
        if self.dropdown_frame and not self._focus_inside() and not self._pointer_inside():
            self._hide_dropdown()

    def _on_click(self, event):
        if self.entry.cget("state") == "readonly":
            self.clear()

    def _check_hide_dropdown(self):
        if self.dropdown_frame and not self._focus_inside() and not self._pointer_inside():
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
                btn.configure(fg_color="#FFF3CD", text_color="#1A1A2E")
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["text"])

    def _show_dropdown(self, query: str):
        if self.dropdown_frame:
            self.dropdown_frame.destroy()

        employees = self.employee_repo.search(query, limit=10)
        if not employees:
            self._hide_dropdown()
            return

        self._selected_index = -1
        self._employees_cache = employees
        
        # Cria frame dropdown posicionado abaixo do entry
        self.dropdown_frame = ctk.CTkToplevel(self)
        self.dropdown_frame.overrideredirect(True)
        self.dropdown_frame.attributes("-topmost", True)
        
        # Posiciona abaixo do entry
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()

        # Calcula largura máxima baseada no container pai visível
        max_width = self.entry.winfo_width()
        parent = self.master
        while parent is not None:
            pw = parent.winfo_width()
            if pw > 1 and pw < 5000:
                max_width = min(max_width, pw)
                break
            parent = getattr(parent, 'master', None)

        width = max_width
        entry_h = self.entry.winfo_height()
        height = entry_h * 6
        self.dropdown_frame.tk.call('wm', 'geometry', self.dropdown_frame._w, f"{width}x{height}+{x}+{y}")
        
        scroll = ctk.CTkScrollableFrame(self.dropdown_frame, fg_color=COLORS["surface"], corner_radius=6)
        scroll.pack(fill="both", expand=True, padx=2, pady=2)

        scroll._parent_frame.configure(width=width - 8)
        self.dropdown_frame.update_idletasks()
        self.dropdown_frame.tk.call('wm', 'geometry', self.dropdown_frame._w, f"{width}x{height}+{x}+{y}")
        
        self.dropdown_buttons = []
        for i, emp in enumerate(employees):
            btn = ctk.CTkButton(
                scroll,
                text=f"{emp.nome}  ({emp.cpf})",
                font=FONTS["body"],
                fg_color="transparent",
                text_color=COLORS["text"],
                hover_color="#FFF3CD",
                anchor="w",
                height=36,
                corner_radius=4,
                command=lambda idx=i: self._select_employee(idx)
            )
            btn.pack(fill="x", padx=4, pady=2)
            btn.bind("<Enter>", lambda e, idx=i: self._on_hover(idx))
            self.dropdown_buttons.append(btn)

        self._dropdown_visible = True
        self._start_watchdog()

    def _on_hover(self, index: int):
        self._selected_index = index
        self._update_selection()

    def _select_employee(self, index: int):
        # usa o cache da lista EXIBIDA (garante o item certo sem re-buscar)
        if 0 <= index < len(self._employees_cache):
            emp = self._employees_cache[index]
            self.selected_employee = emp
            self.entry_var.set(f"{emp.nome} ({emp.cpf})" if emp.cpf else emp.nome)
            self.entry.configure(state="readonly")
            self._hide_dropdown()
            if self.on_select:
                self.on_select(emp)

    def _hide_dropdown(self):
        if self._watchdog_id:
            try:
                self.after_cancel(self._watchdog_id)
            except Exception:
                pass
            self._watchdog_id = None
        if self.dropdown_frame:
            try:
                self.dropdown_frame.destroy()
            except Exception:
                pass
            self.dropdown_frame = None
            self.dropdown_buttons = []
            self._dropdown_visible = False
            self._selected_index = -1

    # ── Anti-orfao: watchdog + eventos da janela principal ────

    def _on_root_unmap(self, _event=None):
        """Janela principal minimizou -> fecha o dropdown na hora."""
        self._hide_dropdown()

    def _on_root_configure(self, event=None):
        """Janela principal moveu/redimensionou -> dropdown acompanha o campo."""
        if self.dropdown_frame and event is not None and event.widget is self.winfo_toplevel():
            self._position_dropdown()

    def _position_dropdown(self):
        if not self.dropdown_frame:
            return
        try:
            x = self.entry.winfo_rootx()
            y = self.entry.winfo_rooty() + self.entry.winfo_height()
            w = self.dropdown_frame.winfo_width()
            h = self.dropdown_frame.winfo_height()
            self.dropdown_frame.tk.call("wm", "geometry", self.dropdown_frame._w, f"{w}x{h}+{x}+{y}")
        except Exception:
            self._hide_dropdown()

    def _on_global_click(self, widget_path: str = ""):
        """Clique em qualquer lugar (via Tcl %W): fora do campo/dropdown, fecha."""
        if not self.dropdown_frame:
            return
        try:
            ws = widget_path or ""
            if ws.startswith(str(self.entry)):
                return
            if self.dropdown_frame and ws.startswith(str(self.dropdown_frame)):
                return
            self._hide_dropdown()
        except Exception:
            self._hide_dropdown()

    def _start_watchdog(self):
        if self._watchdog_id:
            try:
                self.after_cancel(self._watchdog_id)
            except Exception:
                pass
        self._watchdog_id = self.after(300, self._watchdog_tick)

    def _watchdog_tick(self):
        """
        Mantem o dropdown aberto enquanto o foco estiver no campo/dropdown OU o
        mouse estiver sobre eles; fecha quando o usuario tira o foco (inclusive
        para outro programa) ou a janela minimiza. Rede de seguranca a cada 300ms.
        """
        self._watchdog_id = None
        if not self.dropdown_frame:
            return
        try:
            root = self.winfo_toplevel()
            if not root.viewable() or root.state() != "normal":
                self._hide_dropdown()
                return
            if not self._focus_inside() and not self._pointer_inside():
                self._hide_dropdown()
                return
        except Exception:
            self._hide_dropdown()
            return
        self._watchdog_id = self.after(300, self._watchdog_tick)

    def _focus_inside(self) -> bool:
        """Foco dentro do campo de busca ou do dropdown."""
        try:
            w = self.focus_get()
            if w is None:
                return False
            ws = str(w)
            if ws.startswith(str(self.entry)):
                return True
            if self.dropdown_frame and ws.startswith(str(self.dropdown_frame)):
                return True
            return False
        except Exception:
            return False

    def _pointer_inside(self) -> bool:
        """Mouse sobre o dropdown ou sobre o campo de busca."""
        try:
            px, py = self.winfo_pointerxy()
            if self.dropdown_frame and self.dropdown_frame.winfo_containing(px, py):
                return True
            if self.winfo_containing(px, py):
                return True
            return False
        except Exception:
            return False

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