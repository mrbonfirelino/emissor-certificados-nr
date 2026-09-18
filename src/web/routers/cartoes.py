"""Portal Web — Cartões de bloqueio (emissão de cartões/crachás de acesso).

Reaproveita blocking_card_service (templates JSON/ReportLab e PPTX/PowerPoint),
o MESMO dispatch do desktop. Lista de emissões = varredura de data/cartoes
(LOTES + pasta por funcionário). Módulo só para admin/emissor.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response

from src.utils.paths import get_cartoes_dir
from src.web import auth

_MIME = "application/pdf"
_PER_PAGE = 20
_TAMANHOS = {1: "1 cartão", 2: "2 cartões", 4: "4 cartões", 6: "6 cartões",
             8: "8 cartões"}


def _br_ts(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "—"


def _kb(size: int) -> str:
    return f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"


def _rel_seguro(rel: str) -> Optional[Path]:
    """Resolve o caminho relativo sob data/cartoes (bloqueia traversal)."""
    base = get_cartoes_dir().resolve()
    try:
        alvo = (base / rel).resolve()
        alvo.relative_to(base)
    except Exception:
        return None
    return alvo if alvo.is_file() else None


def _templates_cartao() -> list:
    from src.core.blocking_card_service import load_card_templates
    tpls = [t for t in load_card_templates().values()
            if t.get("template_type") != "cracha"]
    tpls.sort(key=lambda t: (t.get("template_type") == "json", t.get("card_code", "")))
    return tpls


def _tipo_label(t: dict) -> str:
    return {"pptx": "PPTX (PowerPoint)", "cracha": "Crachá"}.get(
        t.get("template_type"), "JSON (ReportLab)")


def _usa_matricula(t: dict) -> bool:
    return "MATRICULA" in set(t.get("used_fields") or [])


def register(app, deps: dict):
    users = deps["users"]
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    # ---------------- lista (varredura da pasta) ----------------
    @app.get("/cartoes")
    def cartoes_lista(request: Request,
                      busca: str = "",
                      page: int = 1,
                      user: dict = auth.require_permission("cartoes")):
        from urllib.parse import quote_plus
        base = get_cartoes_dir()
        pdfs = []
        for p in sorted(base.rglob("*.pdf")):
            try:
                stat = p.stat()
            except OSError:
                continue
            pasta = p.parent.relative_to(base).as_posix()
            pdfs.append({"rel": p.relative_to(base).as_posix(),
                         "nome": p.name, "pasta": pasta,
                         "quando": _br_ts(stat.st_mtime),
                         "tamanho": _kb(stat.st_size)})
        pdfs.sort(key=lambda x: x["nome"], reverse=True)
        pdfs.sort(key=lambda x: x["pasta"].lower())
        q = (busca or "").strip().lower()
        if q:
            pdfs = [p for p in pdfs
                    if q in p["nome"].lower() or q in p["pasta"].lower()]
        total = len(pdfs)
        paginas = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
        page = max(1, min(page, paginas))
        fatia = pdfs[(page - 1) * _PER_PAGE: page * _PER_PAGE]
        pg_base = ("/cartoes?busca=" + quote_plus(q)) if q else "/cartoes"
        return templates.TemplateResponse(
            request=request, name="cartoes.html",
            context=ctx(request, pdfs=fatia, total=total, busca=q,
                        page=page, paginas=paginas, pg_base=pg_base,
                        pode_escrever=auth.pode_escrever(user["papel"], "cartoes")))

    # ---------------- PDF por caminho relativo ----------------
    def _pdf(request: Request, rel: str, attachment: bool):
        alvo = _rel_seguro(rel)
        if alvo is None:
            return Response("PDF não encontrado.", status_code=404)
        if attachment:
            return FileResponse(str(alvo), media_type=_MIME, filename=alvo.name)
        return FileResponse(str(alvo), media_type=_MIME)

    @app.get("/cartoes/pdf")
    def cartoes_ver(request: Request, rel: str = "",
                    user: dict = auth.require_permission("cartoes")):
        return _pdf(request, rel, attachment=False)

    @app.get("/cartoes/pdf/download")
    def cartoes_baixar(request: Request, rel: str = "",
                       user: dict = auth.require_permission("cartoes")):
        return _pdf(request, rel, attachment=True)

    # ---------------- nova emissão ----------------
    @app.get("/cartoes/novo")
    def cartoes_novo_form(request: Request, sel: str = "",
                          user: dict = auth.require_permission("cartoes")):
        if not auth.pode_escrever(user["papel"], "cartoes"):
            return templates.TemplateResponse(
                request=request, name="cartoes_novo.html",
                context=ctx(request, erro="Somente administrador ou emissor "
                                          "podem emitir cartões."))
        from src.core.employee_repo import EmployeeRepository
        er = EmployeeRepository()
        funcionarios = sorted(er.get_all(limit=1000000), key=lambda e: e.nome.lower())
        pre_sel = {s.strip() for s in (sel or "").split(",") if s.strip().isdigit()}
        linhas = [{"id": e.id, "nome": e.nome, "cpf": e.cpf or "—",
                   "telefone": bool(getattr(e, "telefone", None)),
                   "foto": bool(getattr(e, "foto", None)),
                   "sel": str(e.id) in pre_sel}
                  for e in funcionarios]
        tpls = [{"code": t.get("card_code"),
                 "nome": f"{t.get('card_code')} — {_tipo_label(t)}"
                         f" ({t.get('card_width_mm')}x{t.get('card_height_mm')}mm)",
                 "tipo": _tipo_label(t),
                 "matricula": _usa_matricula(t),
                 "usa_setor": "SETOR" in set(t.get("used_fields") or []),
                 "usa_papel": "PAPEL" in set(t.get("used_fields") or [])}
                for t in _templates_cartao()]
        return templates.TemplateResponse(
            request=request, name="cartoes_novo.html",
            context=ctx(request, linhas=linhas, tpls=tpls))

    @app.post("/cartoes/emitir")
    async def cartoes_emitir(request: Request,
                             user: dict = auth.require_permission("cartoes")):
        if not auth.pode_escrever(user["papel"], "cartoes"):
            flash(request, erro="Somente administrador ou emissor podem emitir cartões.")
            return RedirectResponse("/cartoes", status_code=303)
        form = await request.form()
        from src.core.blocking_card_service import (generate_cards,
                                                    load_card_template)
        template = load_card_template(str(form.get("template_code") or ""))
        if template is None:
            flash(request, erro="Selecione um modelo de cartão válido.")
            return RedirectResponse("/cartoes/novo", status_code=303)

        from src.core.employee_repo import EmployeeRepository
        er = EmployeeRepository()
        todos = {e.id: e for e in er.get_all(limit=1000000)}
        sel_ids = sorted(int(k.split("_")[1]) for k in form.keys()
                         if k.startswith("sel_")
                         and k.split("_")[1].isdigit())
        if not sel_ids:
            flash(request, erro="Selecione pelo menos um funcionário.")
            return RedirectResponse("/cartoes/novo", status_code=303)
        selecionados = [todos[i] for i in sel_ids if i in todos]
        if not selecionados:
            flash(request, erro="Funcionários selecionados não encontrados.")
            return RedirectResponse("/cartoes/novo", status_code=303)

        usados = set(template.get("used_fields") or [])
        usa_matricula = "MATRICULA" in usados
        matriculas, sem_matricula = {}, []
        for emp in selecionados:
            mat = str(form.get(f"matricula_{emp.id}") or "").strip()
            if usa_matricula and not mat:
                sem_matricula.append(emp.nome)
            if mat:
                matriculas[emp.id] = mat
        if sem_matricula:
            flash(request, erro="Matrícula obrigatória para este modelo — "
                                f"faltou em: {', '.join(sem_matricula)}.")
            return RedirectResponse("/cartoes/novo", status_code=303)

        options = {"matriculas": matriculas}
        if "SETOR" in usados:
            options["setor"] = str(form.get("setor") or "").strip()
        if "PAPEL" in usados:
            options["papeis"] = {emp.id: str(form.get(f"papel_{emp.id}")
                                             or "LIDERADO").upper()
                                 for emp in selecionados}
        saida = str(form.get("saida") or "folha")
        single_pdf = saida != "pagina"
        try:
            paths, faltantes = generate_cards(
                selecionados, template, single_pdf=single_pdf, options=options)
        except Exception as e:
            from src.utils.error_log import log_error
            log_error("portal-cartoes-emitir", e)
            flash(request, erro="Falha ao gerar os cartões"
                                " (modelos PPTX exigem PowerPoint no servidor).")
            return RedirectResponse("/cartoes/novo", status_code=303)
        if not paths:
            flash(request, erro="Nenhum cartão gerado. Pendências: "
                                + " | ".join(faltantes or ["desconhecida"]))
            return RedirectResponse("/cartoes/novo", status_code=303)
        gerados = [{"nome": p.name, "rel": p.relative_to(get_cartoes_dir()).as_posix()}
                   for p in paths]
        users.audit("emitir-cartoes", user["username"], template.get("card_code"),
                    f"{len(gerados)} cartao(s)")
        return templates.TemplateResponse(
            request=request, name="cartoes_resultado.html",
            context=ctx(request, gerados=gerados, faltantes=list(faltantes or []),
                        total=len(gerados)))

    # ---------------- importar lista de bloqueios (.xlsx) ----------------
    @app.post("/cartoes/importar")
    async def cartoes_importar(request: Request, arquivo: UploadFile = None,
                               user: dict = auth.require_permission("cartoes")):
        if not auth.pode_escrever(user["papel"], "cartoes"):
            flash(request, erro="Somente administrador ou emissor podem importar listas.")
            return RedirectResponse("/cartoes/novo", status_code=303)
        from src.web.routers.importacoes import ler_upload_xlsx
        caminho, erro = await ler_upload_xlsx(arquivo)
        if erro:
            flash(request, erro=erro)
            return RedirectResponse("/cartoes/novo", status_code=303)
        try:
            from src.core.employee_repo import EmployeeRepository
            from src.utils.blocking_importer import import_blocking_list
            encontrados, fora = import_blocking_list(str(caminho),
                                                     EmployeeRepository())
        except Exception as e:
            flash(request, erro=f"Falha ao ler a planilha ({e}).")
            return RedirectResponse("/cartoes/novo", status_code=303)
        finally:
            try:
                caminho.unlink(missing_ok=True)
            except OSError:
                pass
        if encontrados:
            sel = ",".join(str(e.id) for e in encontrados)
            msg = f"{len(encontrados)} funcionário(s) da lista prontos para emissão."
            if fora:
                msg += f" Sem correspondência: {', '.join(fora)}."
            flash(request, msg=msg)
            return RedirectResponse(f"/cartoes/novo?sel={sel}", status_code=303)
        flash(request, erro="Nenhum funcionário da planilha foi encontrado no cadastro."
                            + (f" Fora da lista: {', '.join(fora)}." if fora else ""))
        return RedirectResponse("/cartoes/novo", status_code=303)
