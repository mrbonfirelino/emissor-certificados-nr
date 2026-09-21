"""Router de Histórico do portal (Fase 2) — consulta com filtros, download
do PDF e gestão do documento assinado (upload manual / baixar / remover).
"""

from pathlib import Path

from fastapi import Request, UploadFile, File
from fastapi.responses import RedirectResponse, Response, FileResponse

from src.core.employee_repo import EmployeeRepository
from src.core.history_repo import HistoryRepository
from src.utils.validators import validar_data
from src.web import auth
from src.web.permissions import pode_escrever

PER_PAGE = 20
_MIME = {"pdf": "application/pdf", "jpg": "image/jpeg", "png": "image/png"}


def register(app, deps: dict):
    users = deps["users"]
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    def _record(numero: str):
        return HistoryRepository().get_by_number(numero)

    # ---------------- lista com filtros ----------------
    @app.get("/historico")
    def historico(request: Request, busca: str = "", nr: str = "",
                  de: str = "", ate: str = "", assinado: str = "", page: int = 1,
                  user: dict = auth.require_permission("historico")):
        hr = HistoryRepository()
        busca = (busca or "").strip()
        nr = (nr or "").strip()
        de = (de or "").strip()
        ate = (ate or "").strip()
        assinado = assinado if assinado in ("sim", "nao") else ""
        de_iso = (validar_data(de).isoformat() if de else None)
        ate_iso = (validar_data(ate).isoformat() if ate else None)
        nr_sel = nr or None
        assinado_sel = assinado or None

        total = hr.count_query(query=busca, nr_code=nr_sel, data_de=de_iso,
                               data_ate=ate_iso, assinado=assinado_sel)
        page = max(1, page)
        paginas = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        page = min(page, paginas)
        itens = hr.query(query=busca, nr_code=nr_sel, data_de=de_iso,
                         data_ate=ate_iso, assinado=assinado_sel,
                         limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
        tem_pdf_map = {r.cert_number: bool(r.pdf_path and Path(r.pdf_path).exists())
                       for r in itens}

        qs = [f"busca={busca}" if busca else "", f"nr={nr}" if nr else "",
              f"de={de}" if de else "", f"ate={ate}" if ate else "",
              f"assinado={assinado}" if assinado else ""]
        qs = "&".join(q for q in qs if q)

        return templates.TemplateResponse(
            request=request, name="historico.html",
            context=ctx(request, itens=itens, total=total, page=page,
                        paginas=paginas, pg_base=("/historico?" + qs) if qs else "/historico",
                        busca=busca, nr=nr, de=de, ate=ate,
                        assinado=assinado, nrs=hr.distinct_nrs(), qs=qs,
                        tem_pdf_map=tem_pdf_map,
                        pode_escrever=pode_escrever(user["papel"], "historico")))

    # ---------------- pdf ----------------
    def _regenerar_ou_motivo(record):
        """2.33.3 — tenta recriar o PDF ausente; devolve (path|None, motivo|None)."""
        from src.core.certificate_service import CertificateService
        try:
            return CertificateService().regenerar_pdf(record), None
        except ValueError as e:
            return None, str(e)
        except Exception:
            from src.utils.error_log import log_error
            log_error("portal-regenerar-pdf")
            return None, "Não foi possível gerar o PDF (detalhes em error.log)."

    @app.get("/historico/{numero}/pdf")
    def pdf(numero: str, request: Request,
            user: dict = auth.require_permission("historico")):
        record = _record(numero)
        if record is None:
            return Response(status_code=404)
        if not (record.pdf_path and Path(record.pdf_path).exists()):
            pdf_path, motivo = _regenerar_ou_motivo(record)
            if pdf_path is None:
                flash(request, erro=motivo)
                return RedirectResponse("/historico", status_code=303)
            users.audit("regenerar-pdf", user["username"], record.nr_code,
                        f"{record.cert_number} — PDF recriado")
            return FileResponse(str(pdf_path), media_type="application/pdf",
                                filename=Path(str(pdf_path)).name)
        return FileResponse(record.pdf_path, media_type="application/pdf",
                            filename=Path(record.pdf_path).name)

    @app.post("/historico/{numero}/regenerar")
    def regenerar(numero: str, request: Request,
                  user: dict = auth.require_permission("historico")):
        """Gera o PDF na hora a partir dos dados do registro (2.33.3)."""
        if not pode_escrever(user["papel"], "historico"):
            flash(request, erro="Seu papel é somente leitura neste módulo.")
            return RedirectResponse("/historico", status_code=303)
        record = _record(numero)
        if record is None:
            flash(request, erro="Certificado não encontrado.")
            return RedirectResponse("/historico", status_code=303)
        pdf_path, motivo = _regenerar_ou_motivo(record)
        if pdf_path is None:
            flash(request, erro=motivo)
        else:
            users.audit("regenerar-pdf", user["username"], record.nr_code,
                        f"{record.cert_number} — PDF recriado")
            flash(request, msg=f"PDF do certificado {numero} gerado com sucesso.")
        return RedirectResponse("/historico", status_code=303)

    # ---------------- documento assinado ----------------
    @app.post("/historico/{numero}/assinado")
    async def assinado_upload(numero: str, request: Request,
                              arquivo: UploadFile = File(None),
                              user: dict = auth.require_permission("historico")):
        if not pode_escrever(user["papel"], "historico"):
            flash(request, erro="Seu papel é somente leitura neste módulo.")
            return RedirectResponse("/historico", status_code=303)
        record = _record(numero)
        if record is None:
            flash(request, erro="Certificado não encontrado.")
            return RedirectResponse("/historico", status_code=303)
        if arquivo is None or not arquivo.filename:
            flash(request, erro="Selecione um arquivo (PDF, JPG ou PNG).")
            return RedirectResponse("/historico", status_code=303)
        data = await arquivo.read()
        tipo = Path(arquivo.filename).suffix.lstrip(".").lower()
        try:
            HistoryRepository().attach_signed_doc(record.id, data, tipo)
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse("/historico", status_code=303)
        try:
            from src.core import network_sync
            emp = EmployeeRepository().get_by_id(record.employee_id)
            network_sync.run_async(network_sync.salvar_assinado, record, data,
                                   tipo if tipo != "jpeg" else "jpg", emp)
        except Exception:
            pass
        flash(request, msg=f"Documento assinado anexado ao certificado {numero}.")
        return RedirectResponse("/historico", status_code=303)

    @app.get("/historico/{numero}/assinado")
    def assinado_download(numero: str):
        record = _record(numero)
        if record is None:
            return Response(status_code=404)
        resultado = HistoryRepository().get_signed_doc(record.id)
        if not resultado:
            return Response(status_code=404)
        data, tipo = resultado
        return Response(content=data, media_type=_MIME.get(tipo, "application/octet-stream"),
                        headers={"Content-Disposition":
                                 f'attachment; filename="{numero}_assinado.{tipo}"'})

    @app.post("/historico/{numero}/assinado/remover")
    def assinado_remover(numero: str, request: Request,
                         user: dict = auth.require_permission("historico")):
        if not pode_escrever(user["papel"], "historico"):
            flash(request, erro="Seu papel é somente leitura neste módulo.")
            return RedirectResponse("/historico", status_code=303)
        record = _record(numero)
        if record is None:
            flash(request, erro="Certificado não encontrado.")
            return RedirectResponse("/historico", status_code=303)
        HistoryRepository().remove_signed_doc(record.id)
        flash(request, msg=f"Documento assinado removido do certificado {numero}.")
        return RedirectResponse("/historico", status_code=303)

    @app.get("/historico/{numero}/ver")
    def ver(numero: str, request: Request,
            user: dict = auth.require_permission("historico")):
        """Abre o PDF inline no navegador (sem download)."""
        record = _record(numero)
        if record is None:
            return Response(status_code=404)
        if not (record.pdf_path and Path(record.pdf_path).exists()):
            pdf_path, motivo = _regenerar_ou_motivo(record)
            if pdf_path is None:
                flash(request, erro=motivo)
                return RedirectResponse("/historico", status_code=303)
            users.audit("regenerar-pdf", user["username"], record.nr_code,
                        f"{record.cert_number} — PDF recriado")
            return FileResponse(str(pdf_path), media_type="application/pdf")
        return FileResponse(record.pdf_path, media_type="application/pdf")
