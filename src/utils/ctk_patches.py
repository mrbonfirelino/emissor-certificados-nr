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
