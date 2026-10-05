"""Portal Web — módulo Romaneios (Fase: Romaneios).

Romaneio nunca é excluído: apenas bloqueado (roadmap 909-921). Emissão gera
serial único (ROM-000001) + documento (xlsx preenchido e, quando possível,
PDF via Excel COM). Operações exigem pode_escrever('romaneios').
"""

from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse, Response

from src.utils.paths import get_romaneios_dir
from src.web import auth

PER_PAGE = 20
import base64
_MIME = {"pdf": "application/pdf", "xlsx":
         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def _br(iso: str) -> str:
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(iso or "—")


def _iso_br(txt: str) -> str:
    txt = (txt or "").strip()
    if not txt:
        return date.today().isoformat()
    try:
        return datetime.strptime(txt, "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return txt


def register(app, deps) -> None:
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]
    users = deps["users"]
    rotas = APIRouter()

    def _repo():
        from src.core.romaneio_repo import RomaneioRepository
        return RomaneioRepository()

    def _pode_escrever(request: Request):
        user = auth.current_user(request)
        from src.web.permissions import pode_escrever
        return user and pode_escrever(user["papel"], "romaneios")

    def _usuario(request: Request) -> str:
        return (auth.current_user(request) or {}).get("username", "")

    # ------------------------------------------------------------- listagem
    @rotas.get("/romaneios")
    def lista(request: Request, busca: str = "", page: int = 1,
              user: dict = auth.require_permission("romaneios")):
        from src.web.permissions import pode_escrever
        repo = _repo()
        busca = (busca or "").strip()
        if busca:
            total = repo.count_search(busca)
            linhas = repo.search(busca, limit=PER_PAGE,
                                 offset=(page - 1) * PER_PAGE)
        else:
            total = repo.count_all()
            linhas = repo.get_all(limit=PER_PAGE, offset=(page - 1) * PER_PAGE)
        paginas = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        return templates.TemplateResponse(
            request, "romaneios.html",
            context=ctx(request, linhas=linhas, busca=busca, page=page,
                        total_paginas=paginas, total=total,
                        pg_base="/romaneios?busca=" + busca,
                        pode_escrever=pode_escrever(user["papel"], "romaneios")))

    # ---------------------------------------------------------- novo/cadastro
    @rotas.get("/romaneios/novo")
    def novo_form(request: Request,
                  user: dict = auth.require_permission("romaneios")):
        from src.web.permissions import pode_escrever
        if not pode_escrever(user["papel"], "romaneios"):
            return RedirectResponse("/romaneios", 303)
        return templates.TemplateResponse(
            request, "romaneio_form.html",
            context=ctx(request, hoje=date.today().strftime("%d/%m/%Y"),
                        editar=False))

    @rotas.post("/romaneios/novo")
    async def novo(request: Request,
                   user: dict = auth.require_permission("romaneios")):
        if not _pode_escrever(request):
            flash(request, erro="Sem permissão para emitir romaneios.")
            return RedirectResponse("/romaneios", 303)
        form = await request.form()
        repo = _repo()
        serial = repo.next_serial()
        dados = {
            "serial": serial,
            "os": (form.get("os") or "").strip(),
            "cliente": (form.get("cliente") or "").strip(),
            "ordem_compra": (form.get("ordem_compra") or "").strip(),
            "responsavel": _usuario(request),
            "data_elaboracao": date.today().isoformat(),
            "transportadora": (form.get("transportadora") or "").strip(),
            "transportadora_doc": (form.get("transportadora_doc") or "").strip(),
            "veiculo": (form.get("veiculo") or "").strip(),
            "placa": (form.get("placa") or "").strip(),
            "motorista": (form.get("motorista") or "").strip(),
            "data_embarque": _iso_br(form.get("data_embarque") or ""),
            "emitido_por": _usuario(request),
        }
        itens = _coletar_itens(form)
        rid = repo.save(dados, itens)

        # documento
        pasta = get_romaneios_dir() / serial
        pasta.mkdir(parents=True, exist_ok=True)
        from src.core.romaneio_pdf import gerar_romaneio_xlsx, xlsx_para_pdf
        xlsx = pasta / f"{serial}.xlsx"
        try:
            gerar_romaneio_xlsx(xlsx, dados, itens)
        except Exception as exc:
            from src.utils.logs import log_erro
            log_erro("portal-romaneio-xlsx", exc)
        pdf = xlsx_para_pdf(xlsx)
        repo.update_pdf_path(rid, str(pdf or xlsx))

        users.audit("emitir-romaneio", _usuario(request), serial)
        flash(request, msg=f"Romaneio {serial} emitido.")
        return RedirectResponse(f"/romaneios/{rid}", 303)

    def _coletar_itens(form) -> list:
        codigos = form.getlist("codigo[]")
        descricoes = form.getlist("descricao[]")
        unidades = form.getlist("unidade[]")
        qtds = form.getlist("qtd[]")
        dimensoes = form.getlist("dimensoes[]")
        pesos = form.getlist("peso[]")
        tipos = form.getlist("tipo[]")
        observacoes = form.getlist("observacoes[]")
        blocos = form.getlist("bloco[]")
        titulos = form.getlist("bloco_titulo[]")
        itens = []
        for i in range(len(descricoes)):
            desc = (descricoes[i] if i < len(descricoes) else "").strip()
            if not any((desc,
                        (codigos[i] if i < len(codigos) else "").strip(),
                        (qtds[i] if i < len(qtds) else "").strip())):
                continue  # linha vazia
            try:
                bloco = int((blocos[i] if i < len(blocos) else "1") or 1)
            except Exception:
                bloco = 1
            itens.append({
                "bloco": bloco,
                "bloco_titulo": (titulos[i] if i < len(titulos) else ""),
                "codigo": (codigos[i] if i < len(codigos) else "").strip(),
                "descricao": desc,
                "unidade": (unidades[i] if i < len(unidades) else "").strip(),
                "qtd": (qtds[i] if i < len(qtds) else "").strip(),
                "dimensoes": (dimensoes[i] if i < len(dimensoes) else "").strip(),
                "peso": (pesos[i] if i < len(pesos) else "").strip(),
                "tipo": (tipos[i] if i < len(tipos) else "").strip(),
                "observacoes": (observacoes[i] if i < len(observacoes) else "").strip(),
            })
        return itens

    # ------------------------------------------------------------------ ficha
    @rotas.get("/romaneios/{romaneio_id}")
    def ficha(request: Request, romaneio_id: int,
              user: dict = auth.require_permission("romaneios")):
        from src.web.permissions import pode_escrever
        repo = _repo()
        r = repo.get_by_id(romaneio_id)
        if r is None:
            return RedirectResponse("/romaneios", 303)
        return templates.TemplateResponse(
            request, "romaneio_ficha.html",
            context=ctx(request, r=r,
                        elaboracao_br=_br(r["data_elaboracao"]),
                        embarque_br=_br(r["data_embarque"]),
                        pode_escrever=pode_escrever(user["papel"], "romaneios")))

    # -------------------------------------------------------------- documento
    
    @rotas.get("/romaneios/{romaneio_id}/assinatura/{qual}")
    def assinatura_img(request: Request, romaneio_id: int, qual: str,
                       user: dict = auth.require_permission("romaneios")):
        blob = _repo().get_assinatura(romaneio_id, qual)
        if not blob:
            return Response(status_code=404)
        return Response(content=blob, media_type="image/png")


    @rotas.post("/romaneios/{romaneio_id}/assinatura")
    async def assinatura_salvar(request: Request, romaneio_id: int,
                                user: dict = auth.require_permission("romaneios")):
        if not _pode_escrever(request):
            flash(request, erro="Sem permissao para assinar romaneios.")
            return RedirectResponse(f"/romaneios/{romaneio_id}", status_code=303)
        repo = _repo()
        r = repo.get_by_id(romaneio_id)
        if r is None:
            return RedirectResponse("/romaneios", status_code=303)
        if r.get("bloqueado"):
            flash(request, erro="Romaneio bloqueado: desbloqueie antes de assinar.")
            return RedirectResponse(f"/romaneios/{romaneio_id}", status_code=303)
        form = await request.form()

        def _dec(nome):
            txt = (form.get(nome) or "").strip()
            if not txt or "," not in txt:
                return None
            try:
                return base64.b64decode(txt.split(",", 1)[1])
            except Exception:
                return None

        altec = _dec("altec")
        transp = _dec("transp")
        if not altec and not transp:
            flash(request, erro="Nenhuma assinatura foi desenhada.")
            return RedirectResponse(f"/romaneios/{romaneio_id}", status_code=303)
        if altec:
            repo.set_assinatura(romaneio_id, "altec", altec)
        if transp:
            repo.set_assinatura(romaneio_id, "transp", transp)
        # Regera o documento com as assinaturas embutidas
        try:
            from src.core.romaneio_pdf import gerar_romaneio_xlsx, xlsx_para_pdf
            pasta = Path(r["pdf_path"]).parent if r.get("pdf_path") else None
            if pasta and Path(pasta).exists():
                xlsx = Path(pasta) / f"{r['serial']}.xlsx"
                gerar_romaneio_xlsx(
                    xlsx, r, r.get("itens") or [],
                    assinatura_altec=altec or repo.get_assinatura(romaneio_id, "altec"),
                    assinatura_transp=transp or repo.get_assinatura(romaneio_id, "transp"))
                pdf = xlsx_para_pdf(xlsx)
                if pdf:
                    repo.update_pdf_path(romaneio_id, str(pdf))
        except Exception as exc:
            log_erro("portal-romaneio-assinatura", exc)
        users.audit("assinar-romaneio", _usuario(request), r.get("serial", ""))
        flash(request, msg="Assinaturas salvas e documento atualizado.")
        return RedirectResponse(f"/romaneios/{romaneio_id}", status_code=303)

    @rotas.get("/romaneios/{romaneio_id}/pdf")
    def documento(request: Request, romaneio_id: int,
                  user: dict = auth.require_permission("romaneios")):
        repo = _repo()
        r = repo.get_by_id(romaneio_id)
        if r is None or not r.get("pdf_path"):
            return Response("Documento não encontrado.", 404)
        caminho = Path(r["pdf_path"])
        if not caminho.exists():
            return Response("Documento não encontrado.", 404)
        return FileResponse(caminho, media_type=_MIME.get(caminho.suffix.lstrip("."),
                                                          "application/octet-stream"))

    # --------------------------------------------------------------- bloqueio
    @rotas.post("/romaneios/{romaneio_id}/bloquear")
    def bloquear(request: Request, romaneio_id: int,
                 user: dict = auth.require_permission("romaneios")):
        if not _pode_escrever(request):
            flash(request, erro="Sem permissão.")
            return RedirectResponse(f"/romaneios/{romaneio_id}", 303)
        repo = _repo()
        repo.set_bloqueio(romaneio_id, True, _usuario(request))
        users.audit("bloquear-romaneio", _usuario(request), str(romaneio_id))
        flash(request, msg="Romaneio bloqueado (não é excluído).")
        return RedirectResponse(f"/romaneios/{romaneio_id}", 303)

    @rotas.post("/romaneios/{romaneio_id}/desbloquear")
    def desbloquear(request: Request, romaneio_id: int,
                    user: dict = auth.require_permission("romaneios")):
        if not _pode_escrever(request):
            flash(request, erro="Sem permissão.")
            return RedirectResponse(f"/romaneios/{romaneio_id}", 303)
        repo = _repo()
        repo.set_bloqueio(romaneio_id, False, "")
        users.audit("desbloquear-romaneio", _usuario(request), str(romaneio_id))
        flash(request, msg="Romaneio desbloqueado.")
        return RedirectResponse(f"/romaneios/{romaneio_id}", 303)

    app.include_router(rotas)
