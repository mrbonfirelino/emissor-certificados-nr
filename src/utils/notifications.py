"""
Notificacoes Windows (toast) com fallback silencioso.

Se `windows-toasts` nao estiver disponivel, a notificacao falhar ou estiver
desativada nas preferencias, a chamada simplesmente nao faz nada — o
comportamento do app (messagebox/status) permanece inalterado.
"""

_LAST_TOAST = {"t": 0.0}


def notify(title: str, body: str = "") -> bool:
    """
    Exibe um toast do Windows (Win10/11). Retorna True se exibiu.
    Segura contra qualquer erro (nunca quebra o fluxo do chamador).
    """
    try:
        from src.core.app_settings import get_setting

        if not get_setting("notificacoes_ativas", True):
            return False

        import time

        # evita rajada de toasts em sequencia (Win limita)
        now = time.time()
        if now - _LAST_TOAST["t"] < 1.0:
            return False
        _LAST_TOAST["t"] = now

        from windows_toasts import InteractableWindowsToaster, Toast

        toaster = InteractableWindowsToaster("Certificados NR")
        toast = Toast(text_fields=[title, body] if body else [title])
        toaster.show_toast(toast)
        return True
    except Exception:
        return False
