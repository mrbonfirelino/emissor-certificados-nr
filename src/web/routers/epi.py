"""Portal Web — EPI (fichas de entrega, devolução e anexos).

Reaproveita epi_repo/epi_pdf_generator/network_sync. Consulta vê tudo;
ações (POST) exigem admin/emissor (matriz docs/PORTAL/01 §6).
"""

import io
from datetime import date, datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, RedirectResponse, Response

from src.utils.paths import get_epis_dir
from src.web import auth

PER_PAGE = 20
_MIME = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
         "png": "image/png", "gif": "image/gif", "txt": "text/plain"}


def _br(iso: str) -> str:
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return "—"


def _hoje_br() -> str:
    return date.today().strftime("%d/%m/%Y")


def _iso_br(valor: str):
    """dd/mm/aaaa -> ISO (ano com 4 dígitos obrigatório) ou None."""
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        d = datetime.strptime(valor, "%d/%m/%Y")
    except ValueError:
        raise ValueError("Data inválida (use dd/mm/aaaa).")
    return d.date().isoformat()


def _estado(item: dict) -> str:
    """'' | 'Total' | 'Parcial' (mesma regra do gerador desktop)."""
    dev = str(item.get("dev_quantidade") or "").strip()
    if not dev.isdigit():
        return ""
    qtd = str(item.get("quantidade") or "").strip()
    if dev == qtd:
        return "Total"
    return "Parcial"


def _resolver_devolucao(items, escolhas, data_iso):
    """Cópia da lógica do desktop (epi_manager_dialog) — sem customtkinter.

    escolhas: {indice: (modo, qtde_texto)}; modos: pendente/total/parcial.
    """
    novos = []
    for i, it in enumerate(items):
        novo = dict(it)
        modo, qtxt = escolhas.get(i) or ("pendente", "")
        qtxt = (qtxt or "").strip()
        qtd_base = str(novo.get("quantidade") or "").strip()
        if modo == "total":
            novo["dev_quantidade"] = qtd_base
            novo["dev_data"] = data_iso
        elif modo == "parcial":
            if not qtxt.isdigit() or int(qtxt) <= 0:
                raise ValueError(f"Quantidade devolvida inválida no item {i + 1}.")
            if qtd_base.isdigit() and int(qtxt) > int(qtd_base):
                raise ValueError(
                    f"Devolvida maior que a entregue no item {i + 1}.")
            novo["dev_quantidade"] = str(int(qtxt))
            novo["dev_data"] = data_iso
        else:  # pendente
            novo["dev_quantidade"] = ""
            novo["dev_data"] = ""
        novos.append(novo)
    return novos


def register(app, deps):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    @app.get("/epi")
    def epi_lista(request: Request, user: dict = auth.require_permission("epi"),
                  page: int = 1, busca: str = ""):
        from src.core.epi_repo import EpiRepository
        repo = EpiRepository()
        todas = repo.get_all(limit=1000000)
        termo = (busca or "").strip().lower()
        if termo:
            todas = [f for f in todas
                     if termo in (f.get("funcionario_nome") or "").lower()
                     or termo in (f.get("epi_number") or "").lower()]
        todas.sort(key=lambda f: (f.get("created_at") or "", f.get("id") or 0),
                   reverse=True)
        total = len(todas)
        total_paginas = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        page = min(max(1, page), total_paginas)
        fatia = todas[(page - 1) * PER_PAGE: page * PER_PAGE]
        linhas = [{"id": f["id"], "numero": f["epi_number"],
                   "funcionario": f.get("funcionario_nome") or "—",
                   "data": _br(f.get("data_emissao")),
                   "status": f.get("status") or "aberto",
                   "itens": len(f.get("items") or [])}
                  for f in fatia]
        return templates.TemplateResponse(
            request=request, name="epi.html",
            context=ctx(request, linhas=linhas, busca=busca or "", page=page,
                        total_paginas=total_paginas, total=total,
                        pode_escrever=auth.pode_escrever(user["papel"], "epi")))

    @app.get("/epi/nova")
    def epi_nova_form(request: Request,
                      user: dict = auth.require_permission("epi")):
        from src.core.employee_repo import EmployeeRepository
        funcs = sorted(EmployeeRepository().get_all(limit=1000000),
                       key=lambda e: e.nome.lower())
        return templates.TemplateResponse(
            request=request, name="epi_form.html",
            context=ctx(request, funcionarios=funcs, hoje=_hoje_br()))

    @app.post("/epi/nova")
    async def epi_nova(request: Request,
                       user: dict = auth.require_permission("epi"),
                       funcionario_id: int = Form(0), data_emissao: str = Form(""),
                       item_desc: str = Form("")):
        papel = user["papel"]
        if not auth.pode_escrever(papel, "epi"):
            flash(request, erro="Somente administrador ou emissor podem abrir fichas de EPI.")
            return RedirectResponse("/epi", status_code=303)
        form = await request.form()
        from src.core.employee_repo import EmployeeRepository
        from src.core.epi_repo import EpiRepository
        from src.core.epi_pdf_generator import generate_epi_pdf
        er = EmployeeRepository()
        employee = er.get_by_id(funcionario_id)
        if employee is None:
            flash(request, erro="Selecione o funcionário.")
            return RedirectResponse("/epi/nova", status_code=303)

        # itens: linhas item_{ca,desc,qtd,data}_{i} — ignora sem descrição
        itens = []
        for i in range(20):
            ca = (form.get(f"item_ca_{i}") or "").strip()
            desc = (form.get(f"item_desc_{i}") or "").strip()
            qtd = (form.get(f"item_qtd_{i}") or "").strip()
            dta = (form.get(f"item_data_{i}") or "").strip()
            if not desc and not ca:
                continue
            try:
                data_iso = _iso_br(dta) or date.today().isoformat()
            except ValueError as e:
                flash(request, erro=f"Item {i + 1}: {e}")
                return RedirectResponse("/epi/nova", status_code=303)
            itens.append({"ca": ca, "descricao": desc,
                          "quantidade": qtd or "1", "data_entrega": data_iso,
                          "dev_quantidade": "", "dev_data": ""})
        if not itens:
            flash(request, erro="Informe pelo menos um item (C.A. ou descrição).")
            return RedirectResponse("/epi/nova", status_code=303)

        try:
            data_iso = _iso_br(data_emissao)
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse("/epi/nova", status_code=303)
        if not data_iso:
            data_iso = date.today().isoformat()

        repo = EpiRepository()
        numero = repo.next_epi_number()
        pasta = get_epis_dir() / _pasta_funcionario(employee)
        pasta.mkdir(parents=True, exist_ok=True)
        nome_arq = (f"Ficha de EPI - {data_iso[8:10]}-{data_iso[5:7]}-{data_iso[0:4]}"
                    f" ({numero}).pdf")
        pdf_path = pasta / nome_arq
        try:
            generate_epi_pdf(str(pdf_path), numero, employee, data_iso, itens)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-epi-pdf", e)
            flash(request, erro="Não foi possível gerar o PDF da ficha.")
            return RedirectResponse("/epi/nova", status_code=303)
        epi_id = repo.save(numero, employee.id, data_iso, itens,
                           status="aberto", pdf_path=str(pdf_path))
        try:
            from src.core import network_sync
            ficha = repo.get_by_id(epi_id)
            network_sync.run_async(network_sync.sync_epi, ficha, employee)
        except Exception:
            pass
        flash(request, msg=f"Ficha {numero} aberta.")
        return RedirectResponse(f"/epi/{epi_id}", status_code=303)

    @app.get("/epi/{epi_id}")
    def epi_ficha(request: Request, epi_id: int,
                  user: dict = auth.require_permission("epi")):
        from src.core.epi_repo import EpiRepository
        repo = EpiRepository()
        ficha = repo.get_by_id(epi_id)
        if ficha is None:
            return RedirectResponse("/epi", status_code=303)
        itens = []
        for it in (ficha.get("items") or []):
            est = _estado(it)
            dev = str(it.get("dev_quantidade") or "").strip()
            itens.append({"ca": it.get("ca") or "—",
                          "descricao": it.get("descricao") or "—",
                          "quantidade": it.get("quantidade") or "—",
                          "data": _br(it.get("data_entrega")),
                          "estado": est or "Pendente",
                          "classe": "b-verde" if est == "Total"
                          else ("b-amarelo" if est == "Parcial" else "b-cinza"),
                          "dev_txt": (f"{dev}/{it.get('quantidade')} em "
                                      f"{_br(it.get('dev_data'))}" if est else "")})
        anexos = repo.list_docs(epi_id)
        tem_pdf = bool(ficha.get("pdf_path")) and Path(ficha["pdf_path"]).exists()
        return templates.TemplateResponse(
            request=request, name="epi_ficha.html",
            context=ctx(request, ficha=ficha, itens=itens, anexos=anexos,
                        tem_pdf=tem_pdf, hoje_br=_hoje_br(),
                        aberto=(ficha.get("status") != "fechado"),
                        pode_escrever=auth.pode_escrever(user["papel"], "epi")))

    def _epi_pdf_response(epi_id: int, attachment: bool):
        from src.core.epi_repo import EpiRepository
        ficha = EpiRepository().get_by_id(epi_id)
        path = ficha.get("pdf_path") if ficha else None
        if not path or not Path(path).exists():
            return Response("PDF não encontrado.", status_code=404)
        if attachment:
            return FileResponse(path, media_type="application/pdf",
                                filename=Path(path).name)
        return FileResponse(path, media_type="application/pdf")

    @app.get("/epi/{epi_id}/pdf")
    def epi_pdf(request: Request, epi_id: int,
                user: dict = auth.require_permission("epi")):
        return _epi_pdf_response(epi_id, attachment=False)

    @app.get("/epi/{epi_id}/pdf/download")
    def epi_pdf_download(request: Request, epi_id: int,
                         user: dict = auth.require_permission("epi")):
        return _epi_pdf_response(epi_id, attachment=True)

    @app.post("/epi/{epi_id}/status")
    def epi_status(request: Request, epi_id: int,
                   user: dict = auth.require_permission("epi")):
        if not auth.pode_escrever(user["papel"], "epi"):
            flash(request, erro="Somente administrador ou emissor podem alterar fichas.")
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        from src.core.epi_repo import EpiRepository
        novo = EpiRepository().toggle_status(epi_id)
        flash(request, msg="Ficha reaberta." if novo == "aberto" else "Ficha fechada.")
        return RedirectResponse(f"/epi/{epi_id}", status_code=303)

    @app.post("/epi/{epi_id}/devolucao")
    async def epi_devolucao(request: Request, epi_id: int,
                            user: dict = auth.require_permission("epi"),
                            data_devolucao: str = Form("")):
        papel = user["papel"]
        if not auth.pode_escrever(papel, "epi"):
            flash(request, erro="Somente administrador ou emissor podem registrar devoluções.")
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        from src.core.employee_repo import EmployeeRepository
        from src.core.epi_repo import EpiRepository
        from src.core.epi_pdf_generator import (generate_epi_pdf,
                                                generate_devolucao_pdf)
        form = await request.form()
        repo = EpiRepository()
        ficha = repo.get_by_id(epi_id)
        if ficha is None:
            return RedirectResponse("/epi", status_code=303)
        escolhas = {}
        for i in range(len(ficha.get("items") or [])):
            modo = (form.get(f"dev_modo_{i}") or "pendente").strip()
            escolhas[i] = (modo, form.get(f"dev_qtd_{i}") or "")
        try:
            data_iso = _iso_br(data_devolucao)
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        if not data_iso:
            data_iso = date.today().isoformat()
        try:
            itens = _resolver_devolucao(ficha.get("items") or [], escolhas,
                                        data_iso)
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        repo.update_items(epi_id, itens)
        ficha = repo.get_by_id(epi_id)
        employee = EmployeeRepository().get_by_id(ficha["employee_id"])
        try:
            if ficha.get("pdf_path") and Path(ficha["pdf_path"]).exists():
                generate_epi_pdf(ficha["pdf_path"], ficha["epi_number"],
                                 employee, ficha["data_emissao"], itens)
                pasta = Path(ficha["pdf_path"]).parent
                nome_termo = (f"Devolucao - {data_iso[8:10]}-{data_iso[5:7]}-"
                              f"{data_iso[0:4]} ({ficha['epi_number']}).pdf")
                termo = pasta / nome_termo
                generate_devolucao_pdf(str(termo), ficha["epi_number"], employee,
                                       data_iso, itens)
        except PermissionError:
            flash(request, erro="PDF aberto em outro programa. Feche-o e tente de novo.")
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-epi-devolucao", e)
            flash(request, erro="Devolução gravada, mas o PDF não pôde ser regerado.")
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        try:
            from src.core import network_sync
            network_sync.run_async(network_sync.sync_epi, ficha, employee)
            network_sync.run_async(
                network_sync.sync_epi,
                {**ficha, "pdf_path": str(termo)}, employee)
        except Exception:
            pass
        flash(request, msg="Devolução registrada (ficha e termo atualizados).")
        return RedirectResponse(f"/epi/{epi_id}", status_code=303)

    @app.post("/epi/{epi_id}/doc")
    async def epi_doc_upload(request: Request, epi_id: int,
                             user: dict = auth.require_permission("epi"),
                             arquivo: UploadFile = File(None)):
        if not auth.pode_escrever(user["papel"], "epi"):
            flash(request, erro="Somente administrador ou emissor podem anexar.")
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        if arquivo is None or not (arquivo.filename or "").strip():
            flash(request, erro="Selecione o arquivo.")
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        dados = await arquivo.read()
        from src.core.epi_repo import EpiRepository
        repo = EpiRepository()
        try:
            doc_id = repo.add_doc(epi_id, arquivo.filename, dados,
                                  _tipo_por_nome(arquivo.filename))
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        try:
            from src.core import network_sync
            network_sync.run_async(network_sync.sync_epi_doc, epi_id, doc_id)
        except Exception:
            pass
        flash(request, msg="Anexo adicionado.")
        return RedirectResponse(f"/epi/{epi_id}", status_code=303)

    @app.get("/epi/{epi_id}/doc/{doc_id}")
    def epi_doc_download(request: Request, epi_id: int, doc_id: int,
                         user: dict = auth.require_permission("epi")):
        from src.core.epi_repo import EpiRepository
        doc = EpiRepository().get_doc(doc_id)
        if doc is None or doc[0] != epi_id:
            return Response("Anexo não encontrado.", status_code=404)
        _epi_id, filename, dados, tipo = doc
        return Response(dados, media_type=_MIME.get(tipo, "application/octet-stream"),
                        headers={"Content-Disposition":
                                 f'attachment; filename="{filename}"'})

    @app.post("/epi/{epi_id}/doc/{doc_id}/excluir")
    def epi_doc_excluir(request: Request, epi_id: int, doc_id: int,
                        user: dict = auth.require_permission("epi")):
        if not auth.pode_escrever(user["papel"], "epi"):
            flash(request, erro="Somente administrador ou emissor podem excluir anexos.")
            return RedirectResponse(f"/epi/{epi_id}", status_code=303)
        from src.core.epi_repo import EpiRepository
        EpiRepository().delete_doc(doc_id)
        flash(request, msg="Anexo excluído.")
        return RedirectResponse(f"/epi/{epi_id}", status_code=303)


def _tipo_por_nome(filename: str) -> str:
    return (Path(filename).suffix or "").lstrip(".").lower()


def _pasta_funcionario(employee) -> str:
    from src.utils.folder_utils import employee_folder_name
    from src.core.employee_repo import EmployeeRepository
    return employee_folder_name(employee,
                                EmployeeRepository().get_all(limit=1000000))
