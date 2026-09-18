"""Router de Funcionários do portal (Fase 2) — lista, ficha, CRUD, foto e docs.

Reaproveita EmployeeRepository/HistoryRepository (mesmo banco). Escrita
(POST) exige admin/emissor; consulta navega em modo leitura.
"""

from pathlib import Path

from fastapi import Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, Response

from src.core.employee_repo import EmployeeRepository
from src.core.history_repo import HistoryRepository
from src.utils.paths import get_data_dir
from src.utils.validators import validar_cpf, validar_data, validar_telefone
from src.web import auth
from src.web.permissions import pode_escrever

PER_PAGE = 20
PER_OPCOES = (10, 20, 25, 50)
MAX_FOTO = 50 * 1024 * 1024
MAX_DOC = 50 * 1024 * 1024

_TIPOS_SANGUINEOS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
_MIME = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
         "png": "image/png", "gif": "image/gif", "txt": "text/plain"}


def _mime(tipo: str) -> str:
    return _MIME.get((tipo or "").lower(), "application/octet-stream")


def _mime_imagem(foto: bytes) -> str:
    if foto[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return "image/jpeg"


def _ext(filename: str) -> str:
    return Path(filename or "").suffix.lstrip(".").lower()


def _validar_funcionario(nome, cpf, telefone, nascimento, admissao, tipo) -> list:
    erros = []
    if len((nome or "").strip()) < 2:
        erros.append("Informe o nome completo.")
    cpf_dig = "".join(c for c in (cpf or "") if c.isdigit())
    if cpf_dig and not validar_cpf(cpf_dig):
        erros.append("CPF inválido (confira os dígitos).")
    tel_dig = "".join(c for c in (telefone or "") if c.isdigit())
    if tel_dig and not validar_telefone(tel_dig):
        erros.append("Telefone inválido (use DDD + 9 dígitos, ex.: 21984209236).")
    if (nascimento or "").strip() and validar_data(nascimento.strip()) is None:
        erros.append("Data de nascimento inválida (use dd/mm/aaaa).")
    if (admissao or "").strip() and validar_data(admissao.strip()) is None:
        erros.append("Data de admissão inválida (use dd/mm/aaaa).")
    if (tipo or "").strip() and tipo.strip().upper() not in _TIPOS_SANGUINEOS:
        erros.append("Tipo sanguíneo inválido.")
    return erros


def _campos_form(form) -> dict:
    return {
        "nome": (form.get("nome") or "").strip(),
        "cpf": (form.get("cpf") or "").strip(),
        "funcao": (form.get("funcao") or "").strip(),
        "telefone": (form.get("telefone") or "").strip(),
        "nascimento": (form.get("nascimento") or "").strip(),
        "admissao": (form.get("admissao") or "").strip(),
        "tipo": (form.get("tipo") or "").strip().upper(),
        "ctps": (form.get("ctps") or "").strip(),
        "ear": form.get("ear") == "on",
    }


def _foto_bytes(foto_file):
    """Lê e processa a foto enviada (3x4). None = sem upload; str = erro."""
    if foto_file is None or not foto_file.filename:
        return None
    data = foto_file.file.read()
    if not data:
        return None
    if len(data) > MAX_FOTO:
        return "Foto maior que 50MB."
    import os
    import tempfile
    try:
        from src.utils.photo_utils import process_photo_3x4
        fd, caminho = tempfile.mkstemp(suffix=".png")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            return process_photo_3x4(caminho)
        finally:
            try:
                os.unlink(caminho)
            except OSError:
                pass
    except Exception:
        return "Não foi possível processar a foto (envie um JPG ou PNG)."


def register(app, deps: dict):
    users = deps["users"]
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    def _bloqueio(request: Request, user: dict, url: str):
        """Redirect 303 se o papel não pode escrever no módulo."""
        if pode_escrever(user["papel"], "funcionarios"):
            return None
        flash(request, erro="Seu papel é somente leitura neste módulo.")
        return RedirectResponse(url, status_code=303)

    # ---------------- importação de fotos em massa (2.32.1) ----------------
    _FOTO_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

    def _dir_previews_fotos():
        d = Path(get_data_dir()) / "tmp_importacoes"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @app.get("/funcionarios/importar-fotos")
    def importar_fotos_form(request: Request,
                            user: dict = auth.require_permission("funcionarios")):
        red = _bloqueio(request, user, "/funcionarios")
        if red:
            return red
        return templates.TemplateResponse(
            request=request, name="funcionarios_fotos.html",
            context=ctx(request))

    @app.post("/funcionarios/importar-fotos/confirmar")
    async def importar_fotos_confirmar(request: Request,
                                       user: dict = auth.require_permission("funcionarios")):
        import json as _json
        import shutil

        from src.utils.photo_utils import process_photo_3x4

        red = _bloqueio(request, user, "/funcionarios")
        if red:
            return red
        form = await request.form()
        token = (form.get("token") or "").strip()
        if not token or "/" in token or "\\" in token:
            flash(request, erro="Sessão de importação inválida — envie as fotos novamente.")
            return RedirectResponse("/funcionarios/importar-fotos", status_code=303)
        meta_path = _dir_previews_fotos() / f"{token}.json"
        if not meta_path.exists():
            flash(request, erro="Importação expirada — envie as fotos novamente.")
            return RedirectResponse("/funcionarios/importar-fotos", status_code=303)
        try:
            meta = _json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            flash(request, erro="Importação inválida — envie as fotos novamente.")
            return RedirectResponse("/funcionarios/importar-fotos", status_code=303)
        er = EmployeeRepository()
        aplicados, falhas = 0, []
        for item in meta.get("casados", []):
            if form.get(f"aplicar_{item['idx']}") != "on":
                continue
            caminho = Path(meta["pasta"]) / item["arquivo"]
            try:
                dados = process_photo_3x4(str(caminho))
                er.update_foto(int(item["emp_id"]), bytes(dados))
                aplicados += 1
            except Exception:
                falhas.append(item.get("nome") or item["arquivo"])
        try:
            shutil.rmtree(meta.get("pasta"), ignore_errors=True)
        except Exception:
            pass
        meta_path.unlink(missing_ok=True)
        if aplicados:
            users.audit("importar-fotos", user["username"], "",
                        f"fotos={aplicados}")
        msg = f"{aplicados} foto(s) importada(s)."
        if falhas:
            msg += f" Falhas: {', '.join(falhas[:10])}."
        flash(request, msg=msg)
        return RedirectResponse("/funcionarios", status_code=303)

    @app.post("/funcionarios/importar-fotos")
    async def importar_fotos(request: Request,
                             fotos: list[UploadFile] = File(None),
                             user: dict = auth.require_permission("funcionarios")):
        import json as _json
        import secrets as _secrets
        import shutil as _shutil
        import tempfile as _tempfile

        from src.utils.photo_importer import match_photos

        red = _bloqueio(request, user, "/funcionarios")
        if red:
            return red
        uploads = [f for f in (fotos or []) if f and f.filename]
        if not uploads:
            flash(request, erro="Selecione ao menos uma foto.")
            return RedirectResponse("/funcionarios/importar-fotos", status_code=303)
        pasta = Path(_tempfile.mkdtemp(prefix="fotos_"))
        salvos = 0
        for f in uploads:
            ext = Path(f.filename).suffix.lower()
            if ext not in _FOTO_EXTS:
                continue
            dados = await f.read()
            if not dados or len(dados) > MAX_FOTO:
                continue
            destino = pasta / Path(f.filename).name
            try:
                destino.write_bytes(dados)
                salvos += 1
            except OSError:
                continue
        if not salvos:
            _shutil.rmtree(pasta, ignore_errors=True)
            flash(request, erro="Nenhuma foto válida (JPG/PNG/BMP/WEBP até 50MB).")
            return RedirectResponse("/funcionarios/importar-fotos", status_code=303)
        er = EmployeeRepository()
        employees = er.get_all(limit=1_000_000)
        casados, nao_casados = match_photos(employees, pasta)
        if not casados:
            _shutil.rmtree(pasta, ignore_errors=True)
            msg = "Nenhuma foto casou com o cadastro."
            if nao_casados:
                nomes = ", ".join(p["path"].name for p in nao_casados[:10])
                msg += f" Arquivos: {nomes}."
            flash(request, erro=msg)
            return RedirectResponse("/funcionarios/importar-fotos", status_code=303)
        token = _secrets.token_urlsafe(16)
        meta = {
            "pasta": str(pasta),
            "casados": [{"idx": i, "emp_id": c["employee"].id,
                         "nome": c["employee"].nome,
                         "arquivo": c["path"].name}
                        for i, c in enumerate(casados)],
            "nao": [{"arquivo": n["path"].name, "motivo": n["motivo"]}
                    for n in nao_casados],
        }
        (_dir_previews_fotos() / f"{token}.json").write_text(
            _json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        return templates.TemplateResponse(
            request=request, name="funcionarios_fotos_confirma.html",
            context=ctx(request, token=token, casados=casados,
                        nao=nao_casados))

    @app.get("/funcionarios/importar-fotos/preview/{token}/{idx}")
    def importar_fotos_preview(token: str, idx: int):
        import json as _json
        if not token or "/" in token or "\\" in token:
            return Response(status_code=404)
        meta_path = _dir_previews_fotos() / f"{token}.json"
        if not meta_path.exists():
            return Response(status_code=404)
        try:
            meta = _json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return Response(status_code=404)
        for item in meta.get("casados", []):
            if item["idx"] == idx:
                caminho = Path(meta["pasta"]) / item["arquivo"]
                if caminho.exists():
                    ext = caminho.suffix.lower().lstrip(".")
                    media = "image/jpeg" if ext in ("jpg", "jpeg") else (
                        "image/png" if ext == "png" else "application/octet-stream")
                    return Response(content=caminho.read_bytes(), media_type=media)
                break
        return Response(status_code=404)

    # ---------------- lista ----------------
    @app.get("/funcionarios")
    def funcionarios(request: Request, busca: str = "", page: int = 1, per: int = PER_PAGE,
                     user: dict = auth.require_permission("funcionarios")):
        er = EmployeeRepository()
        busca = (busca or "").strip()
        per = per if per in PER_OPCOES else PER_PAGE
        todos = (er.search(busca, limit=1_000_000) if busca
                 else er.get_all(limit=1_000_000))
        total = len(todos)
        page = max(1, page)
        paginas = max(1, (total + per - 1) // per)
        page = min(page, paginas)
        fatia = todos[(page - 1) * per: page * per]
        params = []
        if busca:
            params.append(f"busca={busca}")
        if per != PER_PAGE:
            params.append(f"per={per}")
        pg_base = "/funcionarios" + (("?" + "&".join(params)) if params else "")
        return templates.TemplateResponse(
            request=request, name="funcionarios.html",
            context=ctx(request, lista=fatia, total=total, page=page,
                        paginas=paginas, pg_base=pg_base, busca=busca, per=per,
                        per_opcoes=PER_OPCOES,
                        pode_escrever=pode_escrever(user["papel"], "funcionarios")))

    # ---------------- novo ----------------
    # IMPORTANTE: declarado ANTES de /funcionarios/{emp_id} — o FastAPI casa
    # rotas na ordem de declaração e "novo" seria capturado como emp_id.
    @app.get("/funcionarios/novo")
    def novo_form(request: Request,
                  user: dict = auth.require_permission("funcionarios")):
        return templates.TemplateResponse(
            request=request, name="funcionario_form.html",
            context=ctx(request, emp=None, tipos=_TIPOS_SANGUINEOS,
                        pode_escrever=pode_escrever(user["papel"], "funcionarios")))

    @app.post("/funcionarios/novo")
    async def novo(request: Request,
                   user: dict = auth.require_permission("funcionarios")):
        red = _bloqueio(request, user, "/funcionarios")
        if red:
            return red
        form = await request.form()
        c = _campos_form(form)
        erros = _validar_funcionario(c["nome"], c["cpf"], c["telefone"],
                                     c["nascimento"], c["admissao"], c["tipo"])
        foto_res = _foto_bytes(form.get("foto"))
        if isinstance(foto_res, str):
            erros.append(foto_res)
        if erros:
            flash(request, erro=" ".join(erros))
            return RedirectResponse("/funcionarios/novo", status_code=303)
        er = EmployeeRepository()
        nasc = validar_data(c["nascimento"]) if c["nascimento"] else None
        adm = validar_data(c["admissao"]) if c["admissao"] else None
        emp_id = er.create(
            nome=c["nome"], cpf=c["cpf"] or None, funcao=c["funcao"] or None,
            telefone=c["telefone"] or None,
            data_nascimento=nasc.isoformat() if nasc else None,
            tipo_sanguineo=c["tipo"] or None,
            data_admissao=adm.isoformat() if adm else None,
            registro_ctps=c["ctps"] or None, cnh_ear=c["ear"])
        if isinstance(foto_res, (bytes, bytearray)):
            er.update_foto(emp_id, bytes(foto_res))
        users.audit("criar-funcionario", user["username"], c["nome"])
        flash(request, msg=f"Funcionário '{c['nome']}' cadastrado.")
        return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)

    # ---------------- ficha ----------------
    @app.get("/funcionarios/{emp_id}")
    def ficha(emp_id: int, request: Request,
              user: dict = auth.require_permission("funcionarios")):
        er = EmployeeRepository()
        emp = er.get_by_id(emp_id)
        if emp is None:
            flash(request, erro="Funcionário não encontrado.")
            return RedirectResponse("/funcionarios", status_code=303)
        hr = HistoryRepository()
        try:
            from src.core.epi_repo import EpiRepository
            epi_count = len(EpiRepository().get_by_employee(emp_id))
        except Exception:
            epi_count = 0
        return templates.TemplateResponse(
            request=request, name="funcionario_ficha.html",
            context=ctx(request, emp=emp, docs=er.list_docs(emp_id),
                        certificados=hr.get_by_employee(emp_id),
                        epi_count=epi_count,
                        pode_escrever=pode_escrever(user["papel"], "funcionarios")))

    @app.get("/funcionarios/{emp_id}/foto")
    def foto(emp_id: int):
        emp = EmployeeRepository().get_by_id(emp_id)
        if emp is None or not emp.foto:
            return Response(status_code=404)
        return Response(content=emp.foto, media_type=_mime_imagem(emp.foto))

    # ---------------- editar ----------------
    @app.get("/funcionarios/{emp_id}/editar")
    def editar_form(emp_id: int, request: Request,
                    user: dict = auth.require_permission("funcionarios")):
        emp = EmployeeRepository().get_by_id(emp_id)
        if emp is None:
            flash(request, erro="Funcionário não encontrado.")
            return RedirectResponse("/funcionarios", status_code=303)
        return templates.TemplateResponse(
            request=request, name="funcionario_form.html",
            context=ctx(request, emp=emp, tipos=_TIPOS_SANGUINEOS,
                        pode_escrever=pode_escrever(user["papel"], "funcionarios")))

    @app.post("/funcionarios/{emp_id}/editar")
    async def editar(emp_id: int, request: Request,
                     user: dict = auth.require_permission("funcionarios")):
        red = _bloqueio(request, user, f"/funcionarios/{emp_id}")
        if red:
            return red
        er = EmployeeRepository()
        emp = er.get_by_id(emp_id)
        if emp is None:
            flash(request, erro="Funcionário não encontrado.")
            return RedirectResponse("/funcionarios", status_code=303)
        form = await request.form()
        c = _campos_form(form)
        erros = _validar_funcionario(c["nome"], c["cpf"], c["telefone"],
                                     c["nascimento"], c["admissao"], c["tipo"])
        foto_res = _foto_bytes(form.get("foto"))
        if isinstance(foto_res, str):
            erros.append(foto_res)
        if erros:
            flash(request, erro=" ".join(erros))
            return RedirectResponse(f"/funcionarios/{emp_id}/editar", status_code=303)
        nasc = validar_data(c["nascimento"]) if c["nascimento"] else None
        adm = validar_data(c["admissao"]) if c["admissao"] else None
        er.update(
            emp_id, nome=c["nome"], cpf=c["cpf"] or None, funcao=c["funcao"] or None,
            telefone=c["telefone"] or None,
            data_nascimento=nasc.isoformat() if nasc else None,
            limpar_nascimento=not nasc,
            tipo_sanguineo=c["tipo"] or None, limpar_tipo_sanguineo=not c["tipo"],
            data_admissao=adm.isoformat() if adm else None, limpar_admissao=not adm,
            registro_ctps=c["ctps"] or None, limpar_ctps=not c["ctps"],
            cnh_ear=c["ear"])
        if isinstance(foto_res, (bytes, bytearray)):
            er.update_foto(emp_id, bytes(foto_res))
        flash(request, msg="Dados atualizados.")
        return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)

    # ---------------- documentos ----------------
    @app.post("/funcionarios/{emp_id}/docs")
    async def docs_upload(emp_id: int, request: Request,
                          arquivo: UploadFile = File(None),
                          user: dict = auth.require_permission("funcionarios")):
        red = _bloqueio(request, user, f"/funcionarios/{emp_id}")
        if red:
            return red
        er = EmployeeRepository()
        emp = er.get_by_id(emp_id)
        if emp is None:
            flash(request, erro="Funcionário não encontrado.")
            return RedirectResponse("/funcionarios", status_code=303)
        if arquivo is None or not arquivo.filename:
            flash(request, erro="Selecione um arquivo.")
            return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)
        data = await arquivo.read()
        try:
            er.add_doc(emp_id, Path(arquivo.filename).name, data, _ext(arquivo.filename))
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)
        except Exception:
            flash(request, erro="Não foi possível salvar o documento.")
            return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)
        try:
            from src.core import network_sync
            network_sync.run_async(network_sync.sync_doc,
                                   Path(arquivo.filename).name, data, emp)
        except Exception:
            pass
        flash(request, msg=f"Documento '{Path(arquivo.filename).name}' anexado.")
        return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)

    @app.get("/funcionarios/{emp_id}/docs/{doc_id}/download")
    def docs_download(emp_id: int, doc_id: int):
        resultado = EmployeeRepository().get_doc(doc_id)
        if not resultado or resultado[0] != emp_id:
            return Response(status_code=404)
        _emp_id, filename, data, tipo = resultado
        return Response(content=data, media_type=_mime(tipo),
                        headers={"Content-Disposition":
                                 f'attachment; filename="{filename}"'})

    @app.post("/funcionarios/{emp_id}/docs/{doc_id}/excluir")
    def docs_excluir(emp_id: int, doc_id: int, request: Request,
                     user: dict = auth.require_permission("funcionarios")):
        red = _bloqueio(request, user, f"/funcionarios/{emp_id}")
        if red:
            return red
        er = EmployeeRepository()
        resultado = er.get_doc(doc_id)
        if not resultado or resultado[0] != emp_id:
            flash(request, erro="Documento não encontrado.")
            return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)
        filename = resultado[1]
        er.delete_doc(doc_id)
        try:
            from src.core import network_sync
            emp = er.get_by_id(emp_id)
            network_sync.run_async(network_sync.remove_doc_network, filename, emp)
        except Exception:
            pass
        flash(request, msg=f"Documento '{filename}' removido.")
        return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)
