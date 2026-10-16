"""Configurações do portal (admin) — espelho da tela Configurações do desktop.

Seções: Dados da Empresa, Segurança (senha de restauração), Backups
(periódico/duplo/rede/tarefa agendada do Windows), Documentos em Rede
(sincronizar) e Diagnóstico (log de erros). Aparência/Notificações ficam
só no desktop (fonte e toasts não se aplicam ao navegador).
"""

from fastapi import Request, Form
from fastapi.responses import FileResponse, RedirectResponse

from src.web import auth


def register(app, deps):
    ctx, flash, templates = deps["ctx"], deps["flash"], deps["templates"]
    users = deps["users"]

    def _carregar_tudo():
        from src.core.config import load_company_config, has_restore_password
        from src.core.app_settings import load_app_settings
        from src.utils.error_log import read_log_tail
        cfg = load_company_config()
        settings = load_app_settings()
        try:
            log_tail = read_log_tail()
        except Exception:
            log_tail = ""
        try:
            from src.core.scheduled_task import is_active
            task_ativa = is_active()
        except Exception:
            task_ativa = False
        return cfg, settings, has_restore_password(), log_tail, task_ativa

    @app.get("/configuracoes")
    def configuracoes_form(request: Request,
                           user: dict = auth.require_permission("config")):
        cfg, settings, tem_senha, log_tail, task_ativa = _carregar_tudo()
        return templates.TemplateResponse(
            request=request, name="configuracoes.html",
            context=ctx(request,
                        cfg=cfg, s=settings, tem_senha=tem_senha,
                        log_tail=log_tail, task_ativa=task_ativa))

    @app.post("/configuracoes/salvar")
    def configuracoes_salvar(request: Request,
                             empresa: str = Form(""),
                             cnpj: str = Form(""),
                             local: str = Form(""),
                             instrutor: str = Form(""),
                             registro: str = Form(""),
                             senha_restore: str = Form(""),
                             senha_confirm: str = Form(""),
                             backup_intervalo: str = Form("15"),
                             backup_duplo: str = Form(""),
                             backup_rede: str = Form(""),
                             backup_rede_caminho: str = Form(""),
                             rede_docs: str = Form(""),
                             rede_docs_caminho: str = Form(""),
                             tarefa_ativa: str = Form(""),
                             tarefa_hora: str = Form("12:00"),
                             smtp_host: str = Form(""),
                             smtp_porta: str = Form("587"),
                             smtp_usuario: str = Form(""),
                             smtp_senha: str = Form(""),
                             smtp_seguranca: str = Form("tls"),
                             smtp_remetente: str = Form(""),
                             report_ativo: str = Form(""),
                             report_destinatarios: str = Form(""),
                             report_periodicidade: str = Form("mensal"),
                              pdf_data_hora: str = Form(""),
                              abast_duas_vias: str = Form(""),
                             user: dict = auth.require_permission("config")):
        from src.core.app_settings import load_app_settings, save_app_settings
        from src.utils.validators import (formatar_cnpj, validar_cnpj,
                                          formatar_registro_mte,
                                          validar_registro_mte)

        vals = {"empresa": empresa.strip(), "cnpj": cnpj.strip(),
                "local": local.strip(), "instrutor": instrutor.strip(),
                "registro": registro.strip(), "backup_intervalo": backup_intervalo,
                "backup_duplo": bool(backup_duplo), "backup_rede": bool(backup_rede),
                "backup_rede_caminho": backup_rede_caminho,
                "rede_docs": bool(rede_docs),
                "rede_docs_caminho": rede_docs_caminho,
                "tarefa_ativa": bool(tarefa_ativa), "tarefa_hora": tarefa_hora}
        request.session["cfg_form"] = vals

        empresa = empresa.strip()
        cnpj_fmt = formatar_cnpj(cnpj.strip())
        local = local.strip()
        instrutor = instrutor.strip()
        registro_fmt = formatar_registro_mte(registro.strip())

        if not empresa:
            return _erro_form(request, user, "Nome da empresa é obrigatório")
        if not cnpj_fmt or not validar_cnpj(cnpj_fmt):
            return _erro_form(request, user, "CNPJ inválido")
        if not local:
            return _erro_form(request, user, "Local do treinamento é obrigatório")
        if not instrutor:
            return _erro_form(request, user, "Nome do instrutor é obrigatório")
        if not registro_fmt or not validar_registro_mte(registro_fmt):
            return _erro_form(request, user,
                              "Registro MTE inválido (formato: 44633/RJ)")

        senha_restore = senha_restore or ""
        senha_confirm = senha_confirm or ""
        if senha_restore:
            if senha_restore != senha_confirm:
                return _erro_form(request, user, "Senhas não conferem")
            if len(senha_restore) < 6:
                return _erro_form(request, user,
                                  "Senha deve ter pelo menos 6 caracteres")

        try:
            intervalo = int(backup_intervalo.strip())
        except (TypeError, ValueError):
            return _erro_form(request, user,
                              "Intervalo de backup deve ser um número inteiro (minutos)")
        if not (1 <= intervalo <= 720):
            return _erro_form(request, user,
                              "Intervalo de backup deve ficar entre 1 e 720 minutos")

        tarefa_hora = (tarefa_hora or "").strip() or "12:00"
        tarefa_on = bool(tarefa_ativa)
        if tarefa_on:
            from src.core.scheduled_task import validar_hora
            if not validar_hora(tarefa_hora):
                return _erro_form(request, user,
                                  "Horário da tarefa agendada inválido (use HH:MM, 24h)")

        # preserva chaves não editadas (ex.: migracao_pastas_v2)
        settings = load_app_settings()
        settings["backup_intervalo_min"] = intervalo
        settings["backup_duplo"] = bool(backup_duplo)
        settings["backup_rede_ativo"] = bool(backup_rede)
        settings["backup_rede_caminho"] = (backup_rede_caminho.strip()
                                           or r"Z:\SEGURANÇA\NORMATECH-BACKUP")
        settings["rede_documentos_ativo"] = bool(rede_docs)
        settings["rede_documentos_caminho"] = rede_docs_caminho.strip()
        settings["tarefa_agendada_ativo"] = tarefa_on
        settings["tarefa_agendada_hora"] = tarefa_hora
        settings["pdf_data_hora_emissao"] = bool(pdf_data_hora)
        settings["abast_pdf_duas_vias"] = bool(abast_duas_vias)
        save_app_settings(settings)

        try:
            from src.core import scheduled_task
            if tarefa_on:
                if not scheduled_task.register(tarefa_hora):
                    flash(request, erro="Não foi possível registrar a tarefa agendada do Windows.")
            elif scheduled_task.is_active():
                scheduled_task.remove()
        except Exception:
            flash(request, erro="Erro ao aplicar a tarefa agendada.")

        from src.core.config import (save_company_config, set_restore_password)
        from src.core.models import CompanyConfig
        try:
            config = CompanyConfig(
                empresa_nome=empresa,
                empresa_cnpj=cnpj_fmt,
                local_treinamento=local,
                instrutor_nome=instrutor,
                instrutor_registro_mte=registro_fmt)
        except Exception as e:
            return _erro_form(request, user, f"Erro nos dados: {e}")

        if not save_company_config(config):
            return _erro_form(request, user, "Erro ao salvar configuração")
        from src.core.app_settings import (load_app_settings,
                                                save_app_settings)
        _smtp = load_app_settings()
        _smtp["smtp_host"] = smtp_host.strip()
        try:
            _smtp["smtp_porta"] = max(1, min(65535, int(smtp_porta)))
        except (TypeError, ValueError):
            _smtp["smtp_porta"] = 587
        _smtp["smtp_usuario"] = smtp_usuario.strip()
        if smtp_senha:
            _smtp["smtp_senha"] = smtp_senha
        _smtp["smtp_seguranca"] = (smtp_seguranca
                                   if smtp_seguranca in ("tls", "ssl", "none")
                                   else "tls")
        _smtp["smtp_remetente"] = smtp_remetente.strip()
        _smtp["report_ativo"] = bool(report_ativo)
        _smtp["report_destinatarios"] = report_destinatarios.strip()
        _smtp["report_periodicidade"] = (report_periodicidade
                                         if report_periodicidade in
                                         ("mensal", "trimestral",
                                          "semestral", "anual")
                                         else "mensal")
        save_app_settings(_smtp)
        if senha_restore:
            set_restore_password(senha_restore)
        if not request.session.get("flash", {}).get("erro"):
            users.audit("salvar-config", user["username"])
            flash(request, msg="Configuração salva!")
        return RedirectResponse("/configuracoes", status_code=303)

    def _erro_form(request: Request, user: dict, mensagem: str):
        """Re-renderiza a página com o erro e os valores digitados (sessão)."""
        from src.core.config import has_restore_password
        cfg, settings, tem_senha, log_tail, task_ativa = _carregar_tudo()
        form = request.session.pop("cfg_form", None) or {}
        return templates.TemplateResponse(
            request=request, name="configuracoes.html",
            context=ctx(request, cfg=cfg, s=settings, tem_senha=tem_senha,
                        log_tail=log_tail, task_ativa=task_ativa,
                        erro=mensagem, form=form), status_code=200)

    @app.post("/configuracoes/sincronizar")
    def configuracoes_sincronizar(request: Request,
                                  user: dict = auth.require_permission("config")):
        from src.core.app_settings import get_setting
        if not get_setting("rede_documentos_ativo", False):
            flash(request, erro="Ative o salvamento em rede antes de sincronizar.")
            return RedirectResponse("/configuracoes", status_code=303)
        caminho = (get_setting("rede_documentos_caminho", "") or "").strip()
        if not caminho:
            flash(request, erro="Informe o caminho na rede.")
            return RedirectResponse("/configuracoes", status_code=303)

        from starlette.background import BackgroundTask
        from src.core import network_sync

        flash(request, msg="Sincronização iniciada em segundo plano.")
        response = RedirectResponse("/configuracoes", status_code=303)
        response.background = BackgroundTask(network_sync.sync_all, notify_success=False)
        return response

    @app.post("/configuracoes/testar-caminho")
    def configuracoes_testar_caminho(request: Request, caminho: str = Form(""),
                                     user: dict = auth.require_permission("config")):
        """Testa acesso a um caminho de rede/pasta (v1.67.1)."""
        from pathlib import Path as _P
        caminho = (caminho or "").strip()
        if not caminho:
            flash(request, erro="Informe o caminho para testar.")
            return RedirectResponse("/configuracoes", status_code=303)
        try:
            p = _P(caminho)
            if p.is_dir():
                n = sum(1 for _ in p.iterdir())
                flash(request, msg=f"Caminho acessivel ({n} item(ns)).")
                users.audit("testar-caminho", user["username"], caminho)
            else:
                flash(request, erro="Caminho nao encontrado ou sem acesso.")
        except Exception as e:
            flash(request, erro=f"Sem acesso ao caminho: {e}")
        return RedirectResponse("/configuracoes", status_code=303)

    @app.post("/configuracoes/email-testar")
    def configuracoes_email_testar(request: Request,
                                   user: dict = auth.require_permission("config")):
        """Testa login/conexao SMTP com os dados salvos (v1.67.1)."""
        from src.utils.email_report import testar_conexao
        ok, msg = testar_conexao()
        if ok:
            users.audit("email-testar", user["username"], "ok")
            flash(request, msg=msg)
        else:
            flash(request, erro=msg)
        return RedirectResponse("/configuracoes", status_code=303)

    @app.post("/configuracoes/email-testar-envio")
    def configuracoes_email_testar_envio(request: Request,
                                         user: dict = auth.require_permission("config")):
        """Envia um e-mail de teste para os destinatarios salvos (v1.67.1)."""
        from src.core.app_settings import load_app_settings
        from src.utils.email_report import enviar_email
        cfg = load_app_settings()
        ok, msg = enviar_email(cfg, "NormaTech - e-mail de teste",
                               "<p>Este \u00e9 um e-mail de teste do portal NormaTech.</p>")
        if ok:
            users.audit("email-testar-envio", user["username"], "ok")
        if ok:
            flash(request, msg=msg)
        else:
            flash(request, erro=msg)
        return RedirectResponse("/configuracoes", status_code=303)

    @app.post("/configuracoes/log/limpar")
    def configuracoes_log_limpar(request: Request,
                                 user: dict = auth.require_permission("config")):
        from src.utils.error_log import clear_log
        clear_log()
        flash(request, msg="Log de erros limpo.")
        return RedirectResponse("/configuracoes", status_code=303)

    @app.get("/configuracoes/log/download")
    def configuracoes_log_download(request: Request,
                                   user: dict = auth.require_permission("config")):
        from pathlib import Path
        from src.utils.error_log import ERROR_LOG
        log_path = Path(ERROR_LOG)
        if not log_path.exists():
            flash(request, erro="Nenhum log de erros ainda.")
            return RedirectResponse("/configuracoes", status_code=303)
        return FileResponse(
            str(log_path), media_type="text/plain; charset=utf-8",
            filename="normatech-error.log")
