"""Portal Web — Crachás de identificação (emissão em lote A4).

Reaproveita badge_service (bloqueios, geração ReportLab, numeração) e
cracha_repo. Consulta vê a lista; emissão exige admin/emissor.
"""

from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import FileResponse, RedirectResponse, Response

from src.web import auth

_MIME = "application/pdf"


def _br(iso) -> str:
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return "—"


def _hoje_br() -> str:
    return date.today().strftime("%d/%m/%Y")


def register(app, deps):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    def _templates_cracha() -> list:
        from src.core.blocking_card_service import load_card_templates
        tpls = [t for t in load_card_templates().values()
                if t.get("template_type") == "cracha"]
        tpls.sort(key=lambda t: t.get("card_code", ""))
        return tpls

    @app.get("/crachas")
    def crachas_lista(request: Request,
                      user: dict = auth.require_permission("crachas")):
        from src.core.cracha_repo import CrachaRepository
        repo = CrachaRepository()
        todos = repo.get_all(limit=500)
        todos.sort(key=lambda c: (c.get("created_at") or "", c.get("id") or 0),
                   reverse=True)
        linhas = [{"id": c.get("id"), "numero": c.get("cracha_number"),
                   "funcionario": c.get("employee_nome") or "—",
                   "data": _br(c.get("data_emissao")),
                   "nrs": len(c.get("nrs") or []),
                   "tem_pdf": bool(c.get("pdf_path"))
                   and Path(c["pdf_path"]).exists()}
                  for c in todos]
        return templates.TemplateResponse(
            request=request, name="crachas.html",
            context=ctx(request, linhas=linhas, total=len(linhas),
                        pode_escrever=auth.pode_escrever(user["papel"], "crachas")))

    @app.get("/crachas/novo")
    def crachas_novo_form(request: Request,
                          user: dict = auth.require_permission("crachas")):
        if not auth.pode_escrever(user["papel"], "crachas"):
            return templates.TemplateResponse(
                request=request, name="crachas_novo.html",
                context=ctx(request, erro="Somente administrador ou emissor "
                                          "podem emitir crachás."))
        from src.core.employee_repo import EmployeeRepository
        from src.core.badge_service import (_expiration_maps, _vencido,
                                            cracha_block_reasons)
        er = EmployeeRepository()
        funcionarios = sorted(er.get_all(limit=1000000), key=lambda e: e.nome.lower())
        certs_by_emp, asos = _expiration_maps()
        elegiveis, bloqueados = [], []
        for emp in funcionarios:
            disp = certs_by_emp.get(emp.id, {})
            motivos = cracha_block_reasons(emp, list(disp.values()),
                                           asos.get(emp.id))
            nrs_validas = [nr for nr, c in sorted(
                disp.items(), key=lambda kv: kv[1]["data_fim"], reverse=True)
                if not _vencido(c["data_validade"])]
            item = {"id": emp.id, "nome": emp.nome, "cpf": emp.cpf or "—",
                    "nrs": nrs_validas}
            if motivos:
                bloqueados.append({**item, "motivos": " e ".join(motivos)})
            else:
                elegiveis.append(item)
        tpls = [{"code": t.get("card_code"),
                 "nome": f"{t.get('card_code')}"
                         f" ({t.get('card_width_mm')}x{t.get('card_height_mm')}mm)"}
                for t in _templates_cracha()]
        return templates.TemplateResponse(
            request=request, name="crachas_novo.html",
            context=ctx(request, elegiveis=elegiveis, bloqueados=bloqueados,
                        tpls=tpls, hoje=_hoje_br()))

    @app.post("/crachas/emitir")
    async def crachas_emitir(request: Request,
                             user: dict = auth.require_permission("crachas"),
                             template_code: str = Form(""),
                             tamanho: str = Form("real"),
                             data_emissao: str = Form("")):
        if not auth.pode_escrever(user["papel"], "crachas"):
            flash(request, erro="Somente administrador ou emissor podem emitir crachás.")
            return RedirectResponse("/crachas", status_code=303)
        form = await request.form()
        from src.core.employee_repo import EmployeeRepository
        from src.core.badge_service import (_expiration_maps, _vencido,
                                            cracha_block_reasons,
                                            generate_badges)
        from src.core.blocking_card_service import load_card_templates
        tpls = _templates_cracha()
        template = next((t for t in tpls
                         if t.get("card_code") == template_code), None)
        if template is None:
            flash(request, erro="Selecione um modelo de crachá válido.")
            return RedirectResponse("/crachas/novo", status_code=303)
        try:
            data_iso = datetime.strptime(
                (data_emissao or "").strip(), "%d/%m/%Y").date().isoformat()
        except ValueError:
            flash(request, erro="Data de emissão inválida (use dd/mm/aaaa).")
            return RedirectResponse("/crachas/novo", status_code=303)

        er = EmployeeRepository()
        todos = er.get_all(limit=1000000)
        certs_by_emp, asos = _expiration_maps()
        sel_ids = {int(k.split("_")[1]) for k in form.keys()
                   if k.startswith("sel_")}
        if not sel_ids:
            flash(request, erro="Selecione pelo menos um funcionário elegível.")
            return RedirectResponse("/crachas/novo", status_code=303)
        max_nrs = int(template.get("max_nrs") or 8)
        elegiveis, faltantes_pre = [], []
        for emp in todos:
            if emp.id not in sel_ids:
                continue
            disp = certs_by_emp.get(emp.id, {})
            motivos = cracha_block_reasons(emp, list(disp.values()),
                                           asos.get(emp.id))
            if motivos:
                faltantes_pre.append(f"{emp.nome}: " + " e ".join(motivos))
                continue
            nrs_top = [nr for nr, c in sorted(
                disp.items(), key=lambda kv: kv[1]["data_fim"], reverse=True)
                if not _vencido(c["data_validade"])][:max_nrs]
            elegiveis.append(emp)
        if not elegiveis:
            flash(request, erro="Nenhum funcionário elegível (todos bloqueados).")
            return RedirectResponse("/crachas/novo", status_code=303)

        options = {"data_emissao": data_iso, "tamanho": tamanho,
                   "nrs": {emp.id: [nr for nr, c in sorted(
                       certs_by_emp.get(emp.id, {}).items(),
                       key=lambda kv: kv[1]["data_fim"], reverse=True)
                       if not _vencido(c["data_validade"])][:max_nrs]
                       for emp in elegiveis}}
        try:
            paths, faltantes = generate_badges(
                elegiveis, template, single_pdf=True, options=options)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-crachas-emitir", e)
            flash(request, erro="Falha ao gerar os crachás.")
            return RedirectResponse("/crachas/novo", status_code=303)
        faltantes = list(faltantes_pre) + list(faltantes or [])
        session_paths = list(request.session.get("cracha_pdfs") or [])
        gerados = []
        for p in (paths or []):
            session_paths.append(str(p))
            gerados.append({"nome": Path(p).name, "idx": len(session_paths) - 1})
        request.session["cracha_pdfs"] = session_paths[-20:]
        return templates.TemplateResponse(
            request=request, name="crachas_resultado.html",
            context=ctx(request, gerados=gerados, faltantes=faltantes,
                        total=len(gerados)))

    def _pdf_da_sessao(request: Request, idx: int, attachment: bool):
        caminhos = request.session.get("cracha_pdfs") or []
        if idx < 0 or idx >= len(caminhos):
            return Response("PDF não encontrado.", status_code=404)
        path = Path(caminhos[idx])
        if not path.exists():
            return Response("PDF não encontrado.", status_code=404)
        if attachment:
            return FileResponse(str(path), media_type=_MIME,
                                filename=path.name)
        return FileResponse(str(path), media_type=_MIME)

    @app.get("/crachas/ver/{idx}")
    def crachas_ver(request: Request, idx: int,
                    user: dict = auth.require_permission("crachas")):
        return _pdf_da_sessao(request, idx, attachment=False)

    @app.get("/crachas/baixar/{idx}")
    def crachas_baixar(request: Request, idx: int,
                       user: dict = auth.require_permission("crachas")):
        return _pdf_da_sessao(request, idx, attachment=True)

    @app.get("/crachas/{numero}/pdf")
    def cracha_pdf(request: Request, numero: str,
                   user: dict = auth.require_permission("crachas")):
        from src.core.cracha_repo import CrachaRepository
        for c in CrachaRepository().get_all(limit=500):
            if c.get("cracha_number") == numero and c.get("pdf_path"):
                path = Path(c["pdf_path"])
                if path.exists():
                    return FileResponse(str(path), media_type=_MIME)
        return Response("PDF não encontrado.", status_code=404)

    @app.get("/crachas/{numero}/pdf/download")
    def cracha_pdf_download(request: Request, numero: str,
                            user: dict = auth.require_permission("crachas")):
        from src.core.cracha_repo import CrachaRepository
        for c in CrachaRepository().get_all(limit=500):
            if c.get("cracha_number") == numero and c.get("pdf_path"):
                path = Path(c["pdf_path"])
                if path.exists():
                    return FileResponse(str(path), media_type=_MIME,
                                        filename=path.name)
        return Response("PDF não encontrado.", status_code=404)
