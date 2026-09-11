"""Portal Web — módulo ASO (Fase 3): lista, ficha, novo ASO e documento.

Reaproveita aso_repo, aso_pdf_generator e network_sync (desktop puro).
Rotas de leitura para todos com acesso ao módulo; operações exigem
pode_escrever('aso') — consulta só vê (matriz docs/PORTAL/01 §6).
"""

from datetime import date, datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, RedirectResponse, Response

from src.utils.paths import get_asos_dir
from src.web import auth

PER_PAGE = 20
_MIME = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
         "png": "image/png", "gif": "image/gif", "txt": "text/plain"}


def _br(iso: str) -> str:
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(iso or "—")


def _hoje_br() -> str:
    return date.today().strftime("%d/%m/%Y")


def _status_e_classe(data_exame_iso: str, meses: int) -> tuple:
    try:
        de = date.fromisoformat(str(data_exame_iso)[:10])
        valido = de + relativedelta(months=int(meses or 12))
        dias = (valido - date.today()).days
    except Exception:
        return "—", "", ""
    if dias < 0:
        st, cls = "vencido", "b-vermelho"
    elif dias <= 7:
        st, cls = "urgente", "b-vermelho"
    elif dias <= 15:
        st, cls = "critico", "b-vermelho"
    elif dias <= 30:
        st, cls = "atencao", "b-amarelo"
    elif dias <= 90:
        st, cls = "proximo", "b-verde"
    else:
        st, cls = "ok", "b-verde"
    return valido, st, cls


def register(app, deps) -> None:
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]
    rotas = APIRouter()

    def _repos():
        from src.core.aso_repo import AsoRepository
        from src.core.employee_repo import EmployeeRepository
        return AsoRepository(), EmployeeRepository()

    def _pode_escrever(request: Request):
        user = auth.current_user(request)
        from src.web.permissions import pode_escrever
        return user and pode_escrever(user["papel"], "aso")

    @rotas.get("/aso")
    def lista(request: Request, busca: str = "", page: int = 1,
              user: dict = auth.require_permission("aso")):
        from src.web.permissions import pode_escrever
        aso_repo, _ = _repos()
        busca = (busca or "").strip()
        if busca:
            total = aso_repo.count_search(busca)
            itens = aso_repo.search(busca, limit=PER_PAGE,
                                    offset=(max(page, 1) - 1) * PER_PAGE)
        else:
            total = aso_repo.count_all()
            itens = aso_repo.get_all(limit=PER_PAGE,
                                     offset=(max(page, 1) - 1) * PER_PAGE)
        linhas = []
        for a in itens:
            valido, status, cls = _status_e_classe(a["data_exame"],
                                                   a.get("validade_meses") or 12)
            linhas.append({
                "id": a["id"], "numero": a["aso_number"],
                "funcionario": a.get("funcionario_nome") or "—",
                "tipo": a["tipo_aso"], "exame": _br(a["data_exame"]),
                "valido": valido.strftime("%d/%m/%Y") if valido else "—",
                "status": status, "classe": cls, "anexado": bool(a.get("has_doc")),
            })
        total_paginas = max(1, -(-total // PER_PAGE))
        return templates.TemplateResponse(request=request, name="aso.html",
            context=ctx(request, linhas=linhas, busca=busca, page=max(page, 1),
                        total_paginas=total_paginas, total=total,
                        pode_escrever=pode_escrever(user["papel"], "aso")))

    @rotas.get("/aso/novo")
    def novo_form(request: Request, user: dict = auth.require_permission("aso")):
        from src.core.aso_repo import ASO_TIPOS
        _, er = _repos()
        funcionarios = sorted(er.get_all(limit=1000000), key=lambda e: e.nome.lower())
        return templates.TemplateResponse(request=request, name="aso_form.html",
            context=ctx(request, funcionarios=funcionarios, tipos=ASO_TIPOS,
                        hoje=_hoje_br(), erro="" if _pode_escrever(request)
                        else "Somente administrador ou emissor podem cadastrar ASO."))

    @rotas.post("/aso/novo")
    async def novo(request: Request, funcionario_id: int = Form(0),
                   tipo_aso: str = Form(""), data_exame: str = Form(""),
                   validade_meses: str = Form("12")):
        if not _pode_escrever(request):
            flash(request, erro="Somente administrador ou emissor podem cadastrar ASO.")
            return RedirectResponse("/aso", status_code=303)
        from src.core.aso_pdf_generator import generate_aso_pdf
        from src.utils.date_utils import hoje as hoje_dt
        from src.utils.folder_utils import employee_folder_name
        from src.utils.validators import validar_data
        from src.core import network_sync

        aso_repo, er = _repos()
        employee = er.get_by_id(funcionario_id)
        if employee is None:
            flash(request, erro="Selecione o funcionário.")
            return RedirectResponse("/aso/novo", status_code=303)
        if tipo_aso not in ("Admissional", "Periódico", "Mudança de Função",
                            "Retorno ao Trabalho", "Demissional"):
            flash(request, erro="Tipo de ASO inválido.")
            return RedirectResponse("/aso/novo", status_code=303)
        try:
            meses = int(validade_meses or "12")
        except ValueError:
            meses = 0
        if not 1 <= meses <= 120:
            flash(request, erro="Validade deve ser entre 1 e 120 meses.")
            return RedirectResponse("/aso/novo", status_code=303)
        data_iso = (date.today().isoformat() if not (data_exame or "").strip()
                    else _iso_br(data_exame))
        if data_iso is None:
            flash(request, erro="Data do exame inválida (use dd/mm/aaaa).")
            return RedirectResponse("/aso/novo", status_code=303)
        numero = aso_repo.next_aso_number()
        pasta = get_asos_dir() / employee_folder_name(
            employee, er.get_all(limit=1000000))
        pasta.mkdir(parents=True, exist_ok=True)
        path = pasta / f"{numero}.pdf"
        generate_aso_pdf(str(path), numero, employee, tipo_aso, data_iso, meses)
        novo_id = aso_repo.save(numero, employee.id, tipo_aso, data_iso,
                                validade_meses=meses, pdf_path=str(path))
        try:
            salvo = aso_repo.get_by_id(novo_id)
            if salvo:
                network_sync.run_async(network_sync.sync_aso, salvo, employee)
        except Exception:
            pass
        flash(request, msg=f"ASO {numero} cadastrado.")
        return RedirectResponse(f"/aso/{novo_id}", status_code=303)

    def _iso_br(valor: str):
        try:
            d = datetime.strptime(valor.strip(), "%d/%m/%Y")
            return d.date().isoformat()
        except Exception:
            return None

    @rotas.get("/aso/{aso_id}")
    def ficha(request: Request, aso_id: int,
              user: dict = auth.require_permission("aso")):
        from src.web.permissions import pode_escrever
        aso_repo, er = _repos()
        a = aso_repo.get_by_id(aso_id)
        if a is None:
            return RedirectResponse("/aso", status_code=303)
        valido, status, cls = _status_e_classe(a["data_exame"],
                                               a.get("validade_meses") or 12)
        return templates.TemplateResponse(request=request, name="aso_ficha.html",
            context=ctx(request, aso=a, funcionario=a.get("funcionario_nome") or "—",
                        cpf=a.get("funcionario_cpf") or "",
                        exame_br=_br(a["data_exame"]),
                        valido_br=valido.strftime("%d/%m/%Y") if valido else "—",
                        meses=a.get("validade_meses") or 12,
                        status=status, classe=cls, anexado=bool(a.get("has_doc")),
                        tem_pdf=bool(a.get("pdf_path")),
                        pode_escrever=pode_escrever(user["papel"], "aso")))

    @rotas.get("/aso/{aso_id}/pdf")
    def ver_pdf(request: Request, aso_id: int,
                user: dict = auth.require_permission("aso")):
        aso_repo, _ = _repos()
        a = aso_repo.get_by_id(aso_id)
        if a is None or not a.get("pdf_path") or not Path(a["pdf_path"]).exists():
            return Response("PDF não encontrado.", status_code=404)
        return FileResponse(a["pdf_path"], media_type="application/pdf")

    @rotas.get("/aso/{aso_id}/pdf/download")
    def baixar_pdf(request: Request, aso_id: int,
                   user: dict = auth.require_permission("aso")):
        aso_repo, _ = _repos()
        a = aso_repo.get_by_id(aso_id)
        if a is None or not a.get("pdf_path") or not Path(a["pdf_path"]).exists():
            return Response("PDF não encontrado.", status_code=404)
        nome = Path(a["pdf_path"]).name
        return FileResponse(a["pdf_path"], media_type="application/pdf",
                            filename=nome)

    @rotas.post("/aso/{aso_id}/doc")
    async def anexar_doc(request: Request, aso_id: int, arquivo: UploadFile = File(...)):
        if not _pode_escrever(request):
            flash(request, erro="Somente administrador ou emissor podem anexar documentos.")
            return RedirectResponse(f"/aso/{aso_id}", status_code=303)
        from src.core.aso_pdf_generator import rebuild_aso_pdf
        from src.core import network_sync
        import fitz  # noqa: F401  (garante dependência carregada p/ rebuild)

        aso_repo, er = _repos()
        dados = await arquivo.read()
        if not dados:
            flash(request, erro="Arquivo vazio.")
            return RedirectResponse(f"/aso/{aso_id}", status_code=303)
        try:
            aso_repo.attach_doc(aso_id, dados, arquivo.filename)
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/aso/{aso_id}", status_code=303)
        aso = aso_repo.get_by_id(aso_id)
        employee = er.get_by_id(aso["employee_id"]) if aso else None
        try:
            rebuild_aso_pdf(aso, employee, dados, aso["aso_doc_tipo"])
        except PermissionError:
            flash(request, erro="O PDF está aberto em outro programa. "
                                "Feche-o e anexe novamente.")
            return RedirectResponse(f"/aso/{aso_id}", status_code=303)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-aso-rebuild", e)
        try:
            network_sync.run_async(network_sync.sync_aso_doc, aso_id)
        except Exception:
            pass
        flash(request, msg="Documento anexado e embutido no PDF do ASO.")
        return RedirectResponse(f"/aso/{aso_id}", status_code=303)

    @rotas.get("/aso/{aso_id}/doc")
    def baixar_doc(request: Request, aso_id: int,
                   user: dict = auth.require_permission("aso")):
        aso_repo, _ = _repos()
        doc = aso_repo.get_doc(aso_id)
        if doc is None:
            return Response("Nenhum documento anexado.", status_code=404)
        dados, tipo = doc
        return Response(content=dados, media_type=_MIME.get(tipo, "application/octet-stream"),
                        headers={"Content-Disposition":
                                 f'attachment; filename="aso_documento.{tipo}"'})

    @rotas.post("/aso/{aso_id}/doc/remover")
    def remover_doc(request: Request, aso_id: int):
        if not _pode_escrever(request):
            flash(request, erro="Somente administrador ou emissor podem remover documentos.")
            return RedirectResponse(f"/aso/{aso_id}", status_code=303)
        from src.core.aso_pdf_generator import rebuild_aso_pdf_sem_doc
        from src.core import network_sync

        aso_repo, er = _repos()
        aso = aso_repo.get_by_id(aso_id)
        if aso is None:
            return RedirectResponse("/aso", status_code=303)
        aso_repo.remove_doc(aso_id)
        employee = er.get_by_id(aso["employee_id"])
        try:
            rebuild_aso_pdf_sem_doc(aso, employee)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-aso-rebuild-sem-doc", e)
        try:
            network_sync.run_async(network_sync.sync_aso, aso_repo.get_by_id(aso_id),
                                   employee)
        except Exception:
            pass
        flash(request, msg="Documento removido (PDF volta ao modo esparso).")
        return RedirectResponse(f"/aso/{aso_id}", status_code=303)

    app.include_router(rotas)
