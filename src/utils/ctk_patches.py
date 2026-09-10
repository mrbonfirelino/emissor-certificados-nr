"""Correcoes de comportamento do CustomTkinter usadas pelo NormaTech.

1. Placeholder em CTkEntry com textvariable: o CTk 5.2.2 tem um bug em
   CTkEntry._activate_placeholder — a condicao `self._textvariable == ""`
   compara um objeto StringVar com string e nunca e verdadeira, logo o
   placeholder nunca aparece em campos com textvariable (todas as buscas do
   app). A correcao e opt-in por campo via enable_placeholder(entry).
   Enquanto o placeholder estiver ativo, leia o valor com search_query(entry, var),
   que devolve "" em vez do texto de dica gravado dentro do campo.

2. fit_dialog: geometria de dialogos corrigida pelo widget scaling do CTk.
   Sem isso, maquinas com scaling de 125%-200% (padrao em notebooks) abrem
   os dialogos com o conteudo cortado (botões fora da janela).
"""

import tkinter

import customtkinter as ctk

_INSTALLED = False
_ORIG_ACTIVATE = ctk.CTkEntry._activate_placeholder


def install() -> None:
    """Instala os patches (idempotente). Chamar antes de criar a UI."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    def _activate_placeholder(self):
        if not getattr(self, "_norma_placeholder", False):
            return _ORIG_ACTIVATE(self)
        try:
            if str(self.focus_get()) == str(self._entry):
                return  # campo com foco: usuário digitando — nao poluir a variavel
        except Exception:
            pass
        if (
            self._entry.get() == ""
            and self._placeholder_text is not None
            and not self._placeholder_text_active
        ):
            self._placeholder_text_active = True
            self._pre_placeholder_arguments = {"show": self._entry.cget("show")}
            cor = self._apply_appearance_mode(self._placeholder_text_color)
            self._entry.config(fg=cor, disabledforeground=cor, show="")
            self._entry.delete(0, tkinter.END)
            self._entry.insert(0, self._placeholder_text)

    ctk.CTkEntry._activate_placeholder = _activate_placeholder


def enable_placeholder(entry) -> None:
    """Ativa o placeholder corrigido em um CTkEntry de busca (opt-in)."""
    install()
    entry._norma_placeholder = True
    entry.after(0, entry._activate_placeholder)


def search_query(entry, var) -> str:
    """Valor real da busca: "" enquanto o placeholder estiver visivel."""
    if getattr(entry, "_placeholder_text_active", False):
        return ""
    return var.get()


def fit_dialog(dlg, w: int, h: int) -> None:
    """Aplica a geometria de um dialogo corrigida pelo widget scaling.

    Limita ao tamanho da tela para nao estourar em monitores pequenos.
    CTkToplevel nao expoe _get_widget_scaling de forma confiavel; usa o
    ScalingTracker como fallback.
    """
    s = 1.0
    try:
        s = dlg._get_widget_scaling()
    except Exception:
        try:
            s = ctk.ScalingTracker.get_widget_scaling(dlg)
        except Exception:
            s = 1.0
    largura, altura = int(w * s), int(h * s)
    try:
        largura = min(largura, dlg.winfo_screenwidth() - 40)
        altura = min(altura, dlg.winfo_screenheight() - 80)
    except Exception:
        pass
    dlg.geometry(f"{largura}x{altura}")
    try:
        dlg.resizable(True, True)
    except Exception:
        pass


def open_modal(dlg, delay_ms: int = 250) -> None:
    """Torna o dialogo modal de forma segura no CustomTkinter 5.2.2.

    O CTkToplevel (Windows) esconde e reexibe a propria janela nos
    primeiros milissegundos de vida (_windows_set_titlebar_color, agendado
    pelo __init__ e pelo resizable). Um grab_set imediato nesse intervalo
    deixa o grab preso em uma janela invisivel e o app inteiro para de
    receber cliques. Aqui o grab so e aplicado depois que a janela esta
    estavel, ja com lift/focus para nao ficar atras da janela principal.
    """
    try:
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
    except Exception:
        pass

    def _ativar():
        if not dlg.winfo_exists():
            return
        try:
            # A danca do CTk pode gravar o estado ANTES da janela ser mapeada
            # (state_before='withdrawn') e o "revert" re-aplica oculto para
            # sempre: dialogo invisivel segurando o grab. Reexibir aqui.
            estado = dlg.state()
            if estado in ("withdrawn", "iconic"):
                dlg.deiconify()
            dlg.lift()
            dlg.focus_force()
            dlg.grab_set()
        except Exception:
            pass

    dlg.after(delay_ms, _ativar)


def release_modal(dlg) -> None:
    """Solta o grab com seguranca (chamar antes de destroy do dialogo)."""
    try:
        dlg.grab_release()
    except Exception:
        pass
