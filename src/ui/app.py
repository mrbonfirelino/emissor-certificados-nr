import customtkinter as ctk
import sys
from src.ui.pages.home import WelcomePage
from src.ui.pages.certificates import CertificatesPage
from src.ui.pages.employees import EmployeesPage
from src.ui.pages.history import HistoryPage
from src.ui.pages.backup import BackupPage
from src.ui.pages.batch_import import BatchImportPage
from src.ui.styles import setup_theme, COLORS, get_fonts, load_font_scale
from src.core.certificate_service import CertificateService
from src.core.employee_repo import EmployeeRepository
from src.core.history_repo import HistoryRepository
from src.core.backup_manager import BackupManager
from src.core.config import is_configured, load_company_config, ensure_default_restore_password
from src.utils.paths import get_data_dir

SIDEBAR_WIDTH_EXPANDED = 150
SIDEBAR_WIDTH_COLLAPSED = 42


class NormaTechApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        load_font_scale()
        setup_theme()

        self.title("NormaTech")
        self.geometry("1280x720")
        self.minsize(1024, 600)

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (1280 // 2)
        y = (self.winfo_screenheight() // 2) - (720 // 2)
        self.geometry(f"+{x}+{y}")

        try:
            from src.utils.paths import get_icon_path
            icon_path = get_icon_path()
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        self.certificate_service = CertificateService()
        self.employee_repo = EmployeeRepository()
        self.history_repo = HistoryRepository()
        self.backup_manager = BackupManager()
        self.sidebar_expanded = True

        ensure_default_restore_password()
        self.certificate_service.refresh_config()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        fonts = get_fonts()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === SIDEBAR ===
        self.sidebar = ctk.CTkFrame(self, fg_color=COLORS["primary"], corner_radius=0, width=SIDEBAR_WIDTH_EXPANDED)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(13, weight=1)

        # Toggle button
        self.btn_toggle = ctk.CTkButton(
            self.sidebar, text="\u2630", font=("Segoe UI", 18),
            width=36, height=36, fg_color="transparent",
            text_color=COLORS["surface"], hover_color=COLORS["secondary"],
            command=self._toggle_sidebar
        )
        self.btn_toggle.grid(row=0, column=0, padx=6, pady=(8, 4), sticky="w")

        # Logo/Title
        self.logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.logo_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 6))

        self.lbl_title = ctk.CTkLabel(
            self.logo_frame, text="NormaTech",
            font=fonts["sidebar_title"], text_color=COLORS["surface"]
        )
        self.lbl_title.pack(anchor="w")

        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["secondary"])
        sep.grid(row=2, column=0, sticky="ew", padx=8, pady=4)

        # Nav items: (key, icon, label, command)
        self.nav_buttons = {}
        self.nav_labels = {}
        self.nav_frames = {}
        nav_items = [
            ("home", "\U0001F3E0", "Inicio", self._show_home),
            ("certificates", "\U0001F393", "Certificados", self._show_certificates),
            ("employees", "\U0001F465", "Funcionarios", self._show_employees),
            ("history", "\U0001F4CB", "Historico", self._show_history),
            ("funcoes", "\U0001F4DD", "Funcoes", self._show_funcoes),
            ("vencimentos", "\U0001F4C5", "Vencimentos", self._show_vencimentos),
            ("blocking_cards", "\U0001F4C3", "Cartoes", self._show_blocking_cards),
            ("batch_import", "\U0001F4DD", "Import Lote", self._show_batch_import),
        ]

        for i, (key, icon, label, cmd) in enumerate(nav_items):
            # Frame clicavel que contem icone + label
            nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=42, cursor="hand2")
            nav_frame.grid(row=i + 3, column=0, sticky="ew", padx=4, pady=2)
            nav_frame.grid_propagate(False)
            nav_frame.columnconfigure(1, weight=1)

            def on_frame_click(e, c=cmd):
                c()

            nav_frame.bind("<Button-1>", on_frame_click)

            btn = ctk.CTkButton(
                nav_frame, text=icon, font=("Segoe UI", 14),
                width=30, height=34, fg_color="transparent",
                text_color=COLORS["surface"], corner_radius=6,
                hover_color=COLORS["secondary"], command=cmd
            )
            btn.grid(row=0, column=0, padx=4, pady=3, sticky="w")

            lbl = ctk.CTkLabel(
                nav_frame, text=label,
                font=fonts["sidebar_nav"], text_color=COLORS["surface"],
                cursor="hand2"
            )
            lbl.grid(row=0, column=1, padx=2, pady=3, sticky="w")
            lbl.bind("<Button-1>", on_frame_click)

            self.nav_buttons[key] = btn
            self.nav_labels[key] = lbl
            self.nav_frames[key] = nav_frame

        # Separador antes do Backup
        sep_bottom = ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["secondary"])
        sep_bottom.grid(row=11, column=0, sticky="ew", padx=8, pady=4)

        # Backup (positioned below separator, above version)
        backup_key = "backup"
        backup_icon = "\U0001F4BE"
        backup_label = "Backup"
        backup_cmd = self._show_backup

        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=42, cursor="hand2")
        nav_frame.grid(row=12, column=0, sticky="ews", padx=4, pady=2)
        nav_frame.grid_propagate(False)
        nav_frame.columnconfigure(1, weight=1)

        def on_backup_frame_click(e, c=backup_cmd):
            c()

        nav_frame.bind("<Button-1>", on_backup_frame_click)

        btn = ctk.CTkButton(
            nav_frame, text=backup_icon, font=("Segoe UI", 14),
            width=30, height=34, fg_color="transparent",
            text_color=COLORS["surface"], corner_radius=6,
            hover_color=COLORS["secondary"], command=backup_cmd
        )
        btn.grid(row=0, column=0, padx=4, pady=3, sticky="w")

        lbl = ctk.CTkLabel(
            nav_frame, text=backup_label,
            font=fonts["sidebar_nav"], text_color=COLORS["surface"],
            cursor="hand2"
        )
        lbl.grid(row=0, column=1, padx=2, pady=3, sticky="w")
        lbl.bind("<Button-1>", on_backup_frame_click)

        self.nav_buttons[backup_key] = btn
        self.nav_labels[backup_key] = lbl
        self.nav_frames[backup_key] = nav_frame

        # Configuracoes (abaixo do Backup)
        config_key = "config"
        config_icon = "\u2699"
        config_label = "Config"
        config_cmd = self._show_config

        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=42, cursor="hand2")
        nav_frame.grid(row=13, column=0, sticky="ews", padx=4, pady=2)
        nav_frame.grid_propagate(False)
        nav_frame.columnconfigure(1, weight=1)

        def on_config_frame_click(e, c=config_cmd):
            c()

        nav_frame.bind("<Button-1>", on_config_frame_click)

        btn = ctk.CTkButton(
            nav_frame, text=config_icon, font=("Segoe UI", 14),
            width=30, height=34, fg_color="transparent",
            text_color=COLORS["surface"], corner_radius=6,
            hover_color=COLORS["secondary"], command=config_cmd
        )
        btn.grid(row=0, column=0, padx=4, pady=3, sticky="w")

        lbl = ctk.CTkLabel(
            nav_frame, text=config_label,
            font=fonts["sidebar_nav"], text_color=COLORS["surface"],
            cursor="hand2"
        )
        lbl.grid(row=0, column=1, padx=2, pady=3, sticky="w")
        lbl.bind("<Button-1>", on_config_frame_click)

        self.nav_buttons[config_key] = btn
        self.nav_labels[config_key] = lbl
        self.nav_frames[config_key] = nav_frame

        # Version
        self.lbl_version = ctk.CTkLabel(
            self.sidebar, text="v1.1.0",
            font=fonts["sidebar_version"], text_color=COLORS["muted"]
        )
        self.lbl_version.grid(row=14, column=0, sticky="s", pady=8)

        # === CONTENT ===
        self.content_frame = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.pages = {}
        self.current_page = None
        self._show_home()

    def _toggle_sidebar(self):
        if self.sidebar_expanded:
            self._collapse_sidebar()
        else:
            self._expand_sidebar()

    def _collapse_sidebar(self):
        self.sidebar_expanded = False
        self.sidebar.configure(width=SIDEBAR_WIDTH_COLLAPSED)
        for lbl in self.nav_labels.values():
            lbl.grid_remove()
        self.logo_frame.grid_remove()
        self.lbl_version.grid_remove()

    def _expand_sidebar(self):
        self.sidebar_expanded = True
        self.sidebar.configure(width=SIDEBAR_WIDTH_EXPANDED)
        self.logo_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 6))
        self.lbl_title.pack(anchor="w")
        for key, lbl in self.nav_labels.items():
            lbl.grid(row=0, column=1, padx=2, pady=3, sticky="w")
        self.lbl_version.grid(row=14, column=0, sticky="s", pady=8)

    def _set_active_nav(self, key: str):
        for k, frame in self.nav_frames.items():
            if k == key:
                frame.configure(fg_color=COLORS["secondary"])
            else:
                frame.configure(fg_color="transparent")

    def _show_page(self, page_key: str, page_class, *args, **kwargs):
        # evita duplo clique (command + bind) — se ja esta ativa, so atualiza destaque
        if page_key in self.pages and self.pages[page_key] is self.current_page:
            self._set_active_nav(page_key)
            return
        if self.current_page:
            self.current_page.grid_remove()

        if page_key not in self.pages:
            try:
                page = page_class(self.content_frame, *args, **kwargs)
            except Exception as e:
                import traceback
                traceback.print_exc()
                # restaura pagina anterior visivel
                if self.current_page:
                    self.current_page.grid(row=0, column=0, sticky="nsew")
                from tkinter import messagebox
                messagebox.showerror("Erro ao abrir pagina", f"{page_key}: {e}")
                return
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[page_key] = page
        else:
            page = self.pages[page_key]
            page.grid(row=0, column=0, sticky="nsew")

        self.current_page = page
        self._set_active_nav(page_key)

    def _show_home(self):
        self._show_page("home", WelcomePage, self.employee_repo, self.history_repo, self._navigate)
        if "home" in self.pages:
            self.pages["home"].refresh()

    def _navigate(self, key: str):
        handlers = {
            "certificates": self._show_certificates,
            "employees": self._show_employees,
            "history": self._show_history,
        }
        handler = handlers.get(key)
        if handler:
            handler()

    def _show_certificates(self):
        self._show_page("certificates", CertificatesPage, self.certificate_service, self.employee_repo)

    def _show_employees(self):
        self._show_page("employees", EmployeesPage, self.employee_repo)
        if "employees" in self.pages:
            self.pages["employees"].refresh()

    def _show_history(self):
        self._show_page("history", HistoryPage, self.history_repo)
        if "history" in self.pages:
            self.pages["history"].refresh()

    def _show_funcoes(self):
        from src.ui.pages.funcoes import FuncoesPage
        self._show_page("funcoes", FuncoesPage)
        if "funcoes" in self.pages:
            self.pages["funcoes"].refresh()

    def _show_vencimentos(self):
        from src.ui.pages.vencimentos import VencimentosPage
        self._show_page("vencimentos", VencimentosPage, self.history_repo)
        if "vencimentos" in self.pages:
            self.pages["vencimentos"].refresh()

    def _show_blocking_cards(self):
        from src.ui.pages.blocking_cards import BlockingCardsPage
        self._show_page("blocking_cards", BlockingCardsPage, self.employee_repo)
        if "blocking_cards" in self.pages:
            self.pages["blocking_cards"].refresh()

    def _show_backup(self):
        self._show_page("backup", BackupPage, self.backup_manager)
        if "backup" in self.pages:
            self.pages["backup"].refresh()

    def _show_config(self):
        from src.ui.pages.config import ConfigPage
        self._show_page("config", ConfigPage, on_config_saved=self._on_config_saved)

    def _on_config_saved(self):
        """Aplica configuracoes salvas: empresa (certificados) e backup (intervalo)."""
        self.certificate_service.refresh_config()
        try:
            self.backup_manager.reschedule()
        except Exception:
            pass

    def _show_batch_import(self):
        self._show_page("batch_import", BatchImportPage, self.employee_repo, self.certificate_service)

    def _on_closing(self):
        self.backup_manager.shutdown()
        self.destroy()
        sys.exit(0)


def main():
    app = NormaTechApp()
    app.mainloop()


if __name__ == "__main__":
    main()
