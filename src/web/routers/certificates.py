"""Router de Certificados do portal (Fase 2) — emissão pelo navegador,
detalhe e download do PDF. Reusa CertificateService (número sequencial,
PDF em data/certificados/{Func}/{NR}, registro e espelhamento em rede).
"""

from datetime import date
from pathlib import Path

from fastapi import Request, Response
from fastapi.responses import RedirectResponse, FileResponse

from src.core.employee_repo import EmployeeRepository
from src.core.history_repo import HistoryRepository
from src.core.template_loader import load_all_templates
from src.utils.validators import validar_data
from src.web import auth
from src.web.permissions import pode_escrever


def register(app, deps: dict):
    users = deps["users"]
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    def _templates_ordenados() -> dict:
        return {k: v for k, v in sorted(load_all_templates().items())}

    # ---------------- formulário de emissão ----------------
    @app.get("/certificados")
    def form(request: Request, nr: str = "",
             user: dict = auth.require_permission("certificados")):
        er = EmployeeRepository()
        funcs = sorted(er.get_all(limit=1_000_000), key=lambda e: e.nome.lower())
        templates_nr = _templates_ordenados()
        nr_sel = nr if nr in templates_nr else (next(iter(templates_nr), None))
        tmpl = templates_nr.get(nr_sel)
        return templates.TemplateResponse(
            request=request, name="certificados.html",
            context=ctx(request, funcionarios=funcs, templates_nr=templates_nr,
                        nr_sel=nr_sel, tmpl=tmpl,
                        hoje_br=date.today().strftime("%d/%m/%Y"),
                        pode_escrever=pode_escrever(user["papel"], "certificados")))

    # ---------------- emissão ----------------
    @app.post("/certificados/emitir")
    async def emitir(request: Request,
                     user: dict = auth.require_permission("certificados")):
        if not pode_escrever(user["papel"], "certificados"):
            flash(request, erro="Seu papel é somente leitura neste módulo.")
            return RedirectResponse("/certificados", status_code=303)
        form = await request.form()
        er = EmployeeRepository()
        emp = er.get_by_id(int(form.get("funcionario_id") or 0))
        if emp is None:
            flash(request, erro="Selecione o funcionário.")
            return RedirectResponse("/certificados", status_code=303)
        if not (emp.cpf or "").strip():
            flash(request, erro="Funcionário sem CPF cadastrado. Edite o funcionário antes de emitir.")
            return RedirectResponse("/certificados", status_code=303)
        templates_nr = _templates_ordenados()
        nr = form.get("nr") or ""
        tmpl = templates_nr.get(nr)
        if tmpl is None:
            flash(request, erro="Selecione uma NR válida.")
            return RedirectResponse("/certificados", status_code=303)
        data_treino = validar_data((form.get("data") or "").strip())
        if data_treino is None:
            flash(request, erro="Data inválida (use dd/mm/aaaa).")
            return RedirectResponse("/certificados", status_code=303)
        try:
            carga = int(form.get("carga") or 0)
        except ValueError:
            carga = 0
        if carga < tmpl.carga_horaria_minima:
            flash(request, erro=f"Carga horária mínima para {nr}: {tmpl.carga_horaria_minima}h.")
            return RedirectResponse("/certificados", status_code=303)
        descricao = (form.get("descricao") or "").strip()
        if not descricao:
            flash(request, erro="Informe a descrição do treinamento.")
            return RedirectResponse("/certificados", status_code=303)
        validade_txt = (form.get("validade") or "").strip()
        validade = None
        if validade_txt:
            try:
                validade = int(validade_txt)
                if not 1 <= validade <= 120:
                    raise ValueError
            except ValueError:
                flash(request, erro="Validade inválida (meses entre 1 e 120).")
                return RedirectResponse("/certificados", status_code=303)
        campos = {}
        faltando = []
        for extra in tmpl.campos_extra:
            valor = (form.get(f"campo_{extra.id}") or "").strip()
            if extra.obrigatorio and not valor:
                faltando.append(extra.label)
            if valor:
                campos[extra.id] = valor
        if faltando:
            flash(request, erro="Preencha: " + ", ".join(faltando) + ".")
            return RedirectResponse("/certificados", status_code=303)

        from src.core.certificate_service import CertificateService
        try:
            service = CertificateService()
            pdf_path = service.generate_certificate(
                nr_code=nr, employee=emp, data_treinamento=data_treino,
                carga_horaria=carga, descricao_treinamento=descricao,
                campos_extra=campos, validade_meses=validade)
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse("/certificados", status_code=303)
        except Exception:
            flash(request, erro="Não foi possível gerar o certificado.")
            return RedirectResponse("/certificados", status_code=303)

        try:
            todos = HistoryRepository().get_by_employee(emp.id)
            numero = max(todos, key=lambda r: r.id).cert_number
        except Exception:
            numero = None
        flash(request, msg=f"Certificado {numero or ''} emitido para {emp.nome}.")
        return RedirectResponse(f"/certificados/{numero}", status_code=303) \
            if numero else RedirectResponse("/historico", status_code=303)

    # ---------------- detalhe + pdf ----------------
    @app.get("/certificados/{numero}")
    def detalhe(numero: str, request: Request,
                user: dict = auth.require_permission("certificados")):
        record = HistoryRepository().get_by_number(numero)
        if record is None:
            flash(request, erro="Certificado não encontrado.")
            return RedirectResponse("/historico", status_code=303)
        return templates.TemplateResponse(
            request=request, name="certificado_detalhe.html",
            context=ctx(request, cert=record,
                        tem_pdf=bool(record.pdf_path and Path(record.pdf_path).exists())))

    @app.get("/certificados/{numero}/pdf")
    def pdf(numero: str):
        record = HistoryRepository().get_by_number(numero)
        if record is None or not record.pdf_path or not Path(record.pdf_path).exists():
            return Response(status_code=404)
        return FileResponse(record.pdf_path, media_type="application/pdf",
                            filename=Path(record.pdf_path).name)

    @app.get("/certificados/{numero}/ver")
    def ver(numero: str, user: dict = auth.require_permission("certificados")):
        """Abre o PDF inline no navegador (sem download)."""
        record = HistoryRepository().get_by_number(numero)
        if record is None or not record.pdf_path or not Path(record.pdf_path).exists():
            return Response(status_code=404)
        return FileResponse(record.pdf_path, media_type="application/pdf")

    # ---------------- prévia antes de emitir ----------------
    @app.post("/certificados/preview")
    async def preview(request: Request,
                      user: dict = auth.require_permission("certificados")):
        """Gera o PDF de prévia (número PREVIEW-, não grava registro) e abre inline."""
        form = await request.form()
        er = EmployeeRepository()
        emp = er.get_by_id(int(form.get("funcionario_id") or 0))
        if emp is None:
            return Response("Selecione o funcionário para visualizar a prévia.",
                            status_code=400)
        templates_nr = _templates_ordenados()
        nr = form.get("nr") or ""
        tmpl = templates_nr.get(nr)
        if tmpl is None:
            return Response("Selecione uma NR válida.", status_code=400)
        data_treino = validar_data((form.get("data") or "").strip()) \
            or date.today()
        try:
            carga = int(form.get("carga") or 0) or tmpl.carga_horaria_minima
        except ValueError:
            carga = tmpl.carga_horaria_minima
        descricao = (form.get("descricao") or "").strip() or tmpl.descricao_padrao
        campos = {}
        for extra in tmpl.campos_extra:
            valor = (form.get(f"campo_{extra.id}") or "").strip()
            if valor:
                campos[extra.id] = valor

        from src.core.certificate_service import CertificateService
        try:
            from src.utils.paths import get_data_dir
            prev_dir = get_data_dir() / "_previews"
            prev_dir.mkdir(exist_ok=True)
            alvo = prev_dir / f"web_preview_{emp.id}_{nr}.pdf"
            service = CertificateService()
            service.generate_preview_pdf(
                nr_code=nr, employee=emp, data_treinamento=data_treino,
                carga_horaria=carga, descricao_treinamento=descricao,
                campos_extra=campos, output_path=alvo)
        except Exception:
            return Response("Não foi possível gerar a prévia.", status_code=500)
        if not alvo.exists():
            return Response("Não foi possível gerar a prévia.", status_code=500)
        return FileResponse(alvo, media_type="application/pdf")
