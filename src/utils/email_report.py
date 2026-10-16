"""Relatórios por e-mail e limpeza de previews (v1.67.1).

Usa as chaves SMTP/report de src/core/app_settings.py (preenchidas em
/configuracoes). O agendador diário fica no create_app (src/web/app.py).
"""

from __future__ import annotations

import smtplib
import ssl
import time
from datetime import date
from email.message import EmailMessage
from typing import Any, Dict, List, Optional, Tuple

from src.core.app_settings import load_app_settings, save_app_settings
from src.utils.error_log import log_error
from src.utils.paths import get_data_dir

_PRAZO_DIAS = {"mensal": 30, "trimestral": 91, "semestral": 182, "anual": 365}


def _destinos(cfg: Dict[str, Any]) -> List[str]:
    brutos = (cfg.get("report_destinatarios") or cfg.get("smtp_remetente") or "")
    return [d.strip() for d in brutos.split(",") if d.strip()]


def _conectar(cfg: Dict[str, Any]):
    """Abre SMTP (SSL/TLS/none), faz login se houver usuario; propaga erro."""
    seg = (cfg.get("smtp_seguranca") or "tls").lower()
    host = (cfg.get("smtp_host") or "").strip()
    porta = int(cfg.get("smtp_porta") or 587)
    if seg == "ssl":
        srv = smtplib.SMTP_SSL(host, porta, timeout=15)
    else:
        srv = smtplib.SMTP(host, porta, timeout=15)
    try:
        srv.ehlo()
        if seg == "tls":
            srv.starttls(context=ssl.create_default_context())
            srv.ehlo()
        usuario = (cfg.get("smtp_usuario") or "").strip()
        senha = cfg.get("smtp_senha") or ""
        if usuario:
            srv.login(usuario, senha)
        return srv
    except Exception:
        try:
            srv.quit()
        except Exception:
            pass
        raise


def testar_conexao(cfg: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    cfg = cfg or load_app_settings()
    if not (cfg.get("smtp_host") or "").strip():
        return False, "Informe o servidor SMTP e salve antes de testar."
    try:
        srv = _conectar(cfg)
        try:
            srv.quit()
        except Exception:
            pass
        return True, "Conexao com o servidor de e-mail OK."
    except Exception as e:
        log_error("email-testar-conexao", e)
        return False, f"Falha na conexao SMTP: {e}"


def enviar_email(cfg: Optional[Dict[str, Any]] = None, assunto: str = "",
                 corpo_html: str = "",
                 destinos: Optional[List[str]] = None) -> Tuple[bool, str]:
    cfg = cfg or load_app_settings()
    if not (cfg.get("smtp_host") or "").strip():
        return False, "Servidor SMTP nao configurado (salva em /configuracoes)."
    to = destinos or _destinos(cfg)
    if not to:
        return False, "Nenhum destinatario informado."
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = (cfg.get("smtp_remetente") or cfg.get("smtp_usuario") or "normatech").strip()
    msg["To"] = ", ".join(to)
    msg.set_content("Seu leitor de e-mail nao exibe HTML.")
    msg.add_alternative(corpo_html, subtype="html")
    try:
        srv = _conectar(cfg)
        try:
            srv.send_message(msg)
            srv.quit()
        except Exception:
            try:
                srv.quit()
            except Exception:
                pass
            raise
        return True, f"E-mail enviado para {', '.join(to)}."
    except Exception as e:
        log_error("email-enviar", e)
        return False, f"Falha ao enviar: {e}"


def _coletar_vencimentos() -> Tuple[List[dict], List[dict]]:
    from src.web.routers.vencimentos import _carregar_frota, _carregar_items
    itens = list(_carregar_items()) + list(_carregar_frota())
    vencidos = [c for c in itens if c.get("dias_para_vencer", 0) < 0]
    proximos = [c for c in itens if 0 <= c.get("dias_para_vencer", 0) <= 30]
    vencidos.sort(key=lambda c: c.get("dias_para_vencer", 0))
    proximos.sort(key=lambda c: c.get("dias_para_vencer", 0))
    return vencidos, proximos


def _tabela(itens: List[dict]) -> str:
    if not itens:
        return "<p>Nenhum item.</p>"
    linhas = []
    for c in itens:
        quem = c.get("funcionario_nome") or c.get("veiculo") or "-"
        doc = c.get("nr_code") or c.get("documento") or ""
        num = c.get("cert_number") or c.get("numero") or ""
        valid = c.get("data_validade") or c.get("validade") or "-"
        dias = c.get("dias_para_vencer", c.get("dias", "-"))
        linhas.append(
            f"<tr><td>{num}</td><td>{doc}</td><td>{quem}</td>"
            f"<td>{valid}</td><td>{dias}</td><td>{c.get('status', '')}</td></tr>")
    return ("<table border='1' cellpadding='4' cellspacing='0' "
            "style='border-collapse:collapse;font-family:Arial;font-size:13px;'>"
            "<tr style='background:#eee;'><th>Numero</th><th>Doc</th><th>Item</th>"
            "<th>Validade</th><th>Dias</th><th>Status</th></tr>"
            + "".join(linhas) + "</table>")


def gerar_relatorio_vencimentos_html() -> str:
    vencidos, proximos = _coletar_vencimentos()
    hoje = date.today().strftime("%d/%m/%Y")
    return (
        "<html><body style='font-family:Arial'>"
        f"<h2>NormaTech - Relatório de vencimentos ({hoje})</h2>"
        f"<h3>Vencidos ({len(vencidos)})</h3>{_tabela(vencidos)}"
        f"<h3>Vencem em até 30 dias ({len(proximos)})</h3>{_tabela(proximos)}"
        "<p style='color:#888;font-size:12px;'>"
        "Enviado automaticamente pelo portal NormaTech.</p>"
        "</body></html>")


def deve_enviar_hoje(cfg: Optional[Dict[str, Any]] = None) -> bool:
    cfg = cfg or load_app_settings()
    if not cfg.get("report_ativo"):
        return False
    if not (cfg.get("smtp_host") or "").strip():
        return False
    if not _destinos(cfg):
        return False
    ultimo = (cfg.get("report_ultimo_envio") or "").strip()
    if not ultimo:
        return True
    try:
        d_ult = date.fromisoformat(ultimo[:10])
    except ValueError:
        return True
    prazo = _PRAZO_DIAS.get(cfg.get("report_periodicidade") or "mensal", 30)
    return (date.today() - d_ult).days >= prazo


def enviar_relatorio_se_houver() -> str:
    """Envia o relatorio se ativo e periodo vencido. Retorna msg ou ''."""
    cfg = load_app_settings()
    if not deve_enviar_hoje(cfg):
        return ""
    ok, msg = enviar_email(cfg, "NormaTech - Relatório de vencimentos",
                           gerar_relatorio_vencimentos_html())
    if ok:
        cfg["report_ultimo_envio"] = date.today().isoformat()
        save_app_settings(cfg)
    return msg


def limpar_previews(max_dias: int = 7) -> int:
    """Apaga arquivos de data/_previews mais velhos que max_dias dias."""
    pasta = get_data_dir() / "_previews"
    if not pasta.is_dir():
        return 0
    corte = time.time() - max_dias * 86400
    n = 0
    for f in pasta.iterdir():
        try:
            if f.is_file() and f.stat().st_mtime < corte:
                f.unlink()
                n += 1
        except Exception:
            pass
    return n


def tarefas_diarias() -> str:
    n = limpar_previews()
    msg = enviar_relatorio_se_houver()
    out = f"previews_limpos={n}"
    if msg:
        out += f"; relatorio: {msg}"
    return out
