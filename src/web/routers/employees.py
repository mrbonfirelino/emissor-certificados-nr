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
    def _nivel_cadastro(emp, aso_ok: set) -> str:
        """v1.77.0: nivel de cadastro do funcionario.
        completo = todos os campos preenchidos (basico + nasc/tipo sanguineo/
        admissao/CTPS); basico = foto, nome, cpf, funcao, telefone e ASO valido;
        incompleto = nao atende o basico."""
        def _ok(v):
            return bool(v and str(v).strip())
        basico = bool(getattr(emp, "foto", None)) and _ok(emp.cpf) \
            and _ok(emp.funcao) and _ok(emp.telefone) and emp.id in aso_ok
        if not basico:
            return "incompleto"
        extras = [getattr(emp, "data_nascimento", None),
                  getattr(emp, "tipo_sanguineo", None),
                  getattr(emp, "data_admissao", None),
                  getattr(emp, "registro_ctps", None)]
        if all(_ok(c) for c in extras):
            return "completo"
        return "basico"

    # v1.81.0: XLSX de funcionarios com cadastro incompleto
    @app.get("/funcionarios/incompletos/exportar")
    def funcionarios_incompletos_exportar(
            user: dict = auth.require_permission("funcionarios")):
        from io import BytesIO
        from openpyxl import Workbook
        from openpyxl.styles import Border, Font, PatternFill, Side
        er = EmployeeRepository()
        todos = list(er.get_all(limit=1_000_000))
        todos.sort(key=lambda e: str(e.nome).lower())
        from src.core.aso_repo import AsoRepository
        try:
            aso_ok = {a["employee_id"] for a in
                      AsoRepository().get_asos_with_expiration(only_latest=True)
                      if a["dias_para_vencer"] >= 0}
        except Exception:
            aso_ok = set()

        def _ok(v):
            return bool(v and str(v).strip())

        linhas = []
        for e in todos:
            if _nivel_cadastro(e, aso_ok) != "incompleto":
                continue
            faltando = []
            if not getattr(e, "foto", None):
                faltando.append("Foto")
            if not _ok(e.cpf):
                faltando.append("CPF")
            if not _ok(e.funcao):
                faltando.append("Função")
            if not _ok(e.telefone):
                faltando.append("Telefone")
            if e.id not in aso_ok:
                faltando.append("ASO válido")
            linhas.append((e.nome, e.cpf or "", e.funcao or "",
                           e.telefone or "", ", ".join(faltando)))

        wb = Workbook()
        ws = wb.active
        ws.title = "Incompletos"
        ws.append(["Funcionário", "CPF", "Função", "Telefone", "Faltando"])
        for r in linhas:
            ws.append(list(r))
        fina = Side(style="thin", color="999999")
        borda = Border(left=fina, right=fina, top=fina, bottom=fina)
        for c in ws[1]:
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor="FFE699")
            c.border = borda
        larguras = {"A": 38, "B": 16, "C": 22, "D": 18, "E": 42}
        for col, w in larguras.items():
            ws.column_dimensions[col].width = w
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.border = borda
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        buf = BytesIO()
        wb.save(buf)
        from urllib.parse import quote
        nome = quote("cadastros_incompletos.xlsx")
        return Response(content=buf.getvalue(),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition":
                                 f"attachment; filename*=UTF-8''{nome}"})

    @app.get("/funcionarios")
    def funcionarios(request: Request, busca: str = "", page: int = 1, per: int = PER_PAGE,
                     arquivado: str = "nao", nivel: str = "todos",
                     tem_aso: str = "todos", tem_telefone: str = "todos",
                     tem_foto: str = "todos", tem_cpf: str = "todos",
                     tem_funcao: str = "todos",
                     user: dict = auth.require_permission("funcionarios")):
        er = EmployeeRepository()
        busca = (busca or "").strip()
        per = per if per in PER_OPCOES else PER_PAGE
        arquivado = arquivado if arquivado in ("nao", "sim", "todos") else "nao"
        nivel = nivel if nivel in ("todos", "basico", "incompleto", "completo") else "todos"
        if arquivado == "sim":
            todos = er.get_all_arquivados(limit=1_000_000)
        elif arquivado == "todos":
            todos = list(er.get_all(limit=1_000_000)) + \
                list(er.get_all_arquivados(limit=1_000_000))
            todos.sort(key=lambda e: str(e.nome).lower())
        else:
            todos = (er.search(busca, limit=1_000_000) if busca
                     else er.get_all(limit=1_000_000))
        # v1.77.0: nivel de cadastro (badge) — ASO valido via expirations
        from src.core.aso_repo import AsoRepository
        try:
            aso_ok = {a["employee_id"] for a in
                      AsoRepository().get_asos_with_expiration(only_latest=True)
                      if a["dias_para_vencer"] >= 0}
        except Exception:
            aso_ok = set()
        nivel_map = {e.id: _nivel_cadastro(e, aso_ok) for e in todos}
        if nivel != "todos":
            todos = [e for e in todos if nivel_map.get(e.id) == nivel]
        # v1.79.0: filtros SIM/NAO por dado cadastrado
        def _tem(e, campo):
            v = getattr(e, campo, None)
            if campo == "foto":
                return bool(v)
            return bool(v and str(v).strip())
        _filtros_tem = {
            "tem_aso": lambda e: e.id in aso_ok,
            "tem_telefone": lambda e: _tem(e, "telefone"),
            "tem_foto": lambda e: _tem(e, "foto"),
            "tem_cpf": lambda e: _tem(e, "cpf"),
            "tem_funcao": lambda e: _tem(e, "funcao"),
        }
        for _k, _fn in _filtros_tem.items():
            _v = locals()[_k]
            if _v == "sim":
                todos = [e for e in todos if _fn(e)]
            elif _v == "nao":
                todos = [e for e in todos if not _fn(e)]
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
        if arquivado != "nao":
            params.append(f"arquivado={arquivado}")
        if nivel != "todos":
            params.append(f"nivel={nivel}")
        for _k in ("tem_aso", "tem_telefone", "tem_foto", "tem_cpf", "tem_funcao"):
            if locals()[_k] != "todos":
                params.append(f"{_k}={locals()[_k]}")
        pg_base = "/funcionarios" + (("?" + "&".join(params)) if params else "")
        return templates.TemplateResponse(
            request=request, name="funcionarios.html",
            context=ctx(request, lista=fatia, total=total, page=page,
                        paginas=paginas, pg_base=pg_base, busca=busca, per=per,
                        per_opcoes=PER_OPCOES, arquivado=arquivado, nivel=nivel,
                        nivel_map=nivel_map,
                        tem_aso=tem_aso, tem_telefone=tem_telefone,
                        tem_foto=tem_foto, tem_cpf=tem_cpf, tem_funcao=tem_funcao,
                        pode_escrever=pode_escrever(user["papel"], "funcionarios")))

    # ---------------- arquivar / desarquivar (v1.69.0) ----------------
    @app.post("/funcionarios/{emp_id}/excluir")
    def excluir_funcionario(emp_id: int, request: Request,
                            motivo: str = Form(""),
                            user: dict = auth.require_permission("funcionarios")):
        # v1.86.0: usuarios do setor Seguranca podem ARQUIVAR funcionarios
        # desligados (mas nao excluir); exclusao continua só admin.
        eh_admin = user["papel"] == "admin"
        try:
            _u_db = users.get_by_id(user["id"])
            setor_usuario = (dict(_u_db).get("setor") if _u_db else "") or ""
        except Exception:
            setor_usuario = ""
        eh_seguranca = setor_usuario == "seguranca"
        if not eh_admin and not eh_seguranca:
            flash(request, erro="Somente o administrador pode excluir/arquivar funcionarios.")
            return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)
        er = EmployeeRepository()
        emp = er.get_by_id(emp_id)
        if not emp:
            flash(request, erro="Funcionario nao encontrado.")
            return RedirectResponse("/funcionarios", status_code=303)
        if eh_seguranca and not eh_admin:
            # setor Seguranca apenas ARQUIVA (nunca exclui o registro)
            er.set_arquivado(emp_id, True)
            users.audit("arquivar-funcionario", user["username"], emp_id,
                        motivo or emp.nome)
            flash(request, msg=f"Funcionario {emp.nome} ARQUIVADO. "
                  "Ele sai das listas, mas o historico permanece.")
            return RedirectResponse("/funcionarios", status_code=303)
        if er.delete(emp_id):
            users.audit("excluir-funcionario", user["username"], emp_id,
                        motivo or emp.nome)
            flash(request, msg=f"Funcionario {emp.nome} excluido.")
        elif eh_seguranca and not eh_admin:
            er.set_arquivado(emp_id, True)
            users.audit("arquivar-funcionario", user["username"], emp_id,
                        motivo or emp.nome)
            flash(request, msg=f"Funcionario {emp.nome} ARQUIVADO. "
                  "Ele sai das listas, mas o historico permanece.")
        else:
            er.set_arquivado(emp_id, True)
            users.audit("arquivar-funcionario", user["username"], emp_id,
                        motivo or emp.nome)
            flash(request, msg=f"Funcionario {emp.nome} ARQUIVADO (possui certificados, "
                  "nao pode ser excluido). Ele sai das listas, mas o historico permanece.")
        return RedirectResponse("/funcionarios", status_code=303)

    @app.post("/funcionarios/{emp_id}/desarquivar")
    def desarquivar_funcionario(emp_id: int, request: Request,
                                user: dict = auth.require_permission("funcionarios")):
        if user["papel"] != "admin":
            flash(request, erro="Somente o administrador pode desarquivar funcionarios.")
            return RedirectResponse(f"/funcionarios/{emp_id}", status_code=303)
        er = EmployeeRepository()
        er.set_arquivado(emp_id, False)
        users.audit("desarquivar-funcionario", user["username"], emp_id, "")
        flash(request, msg="Funcionario desarquivado.")
        return RedirectResponse("/funcionarios?arquivado=nao", status_code=303)

    # ---------------- duplicidades / mesclar (v1.80.0) ----------------
    @app.get("/funcionarios/duplicidades")
    def duplicidades(request: Request,
                     user: dict = auth.require_permission("funcionarios")):
        if user["papel"] != "admin":
            flash(request, erro="Somente o administrador pode ver duplicidades.")
            return RedirectResponse("/funcionarios", status_code=303)
        from src.utils.text_utils import normalize_text
        er = EmployeeRepository()
        # v1.80.1: agrupar somente ATIVOS — apos a mescla (duplicado arquivado)
        # o grupo sai da lista automaticamente. Arquivados seguem em /funcionarios?arquivado=sim.
        todos = list(er.get_all(limit=1_000_000))
        pai = {e.id: e.id for e in todos}

        def _raiz(i):
            while pai[i] != i:
                pai[i] = pai[pai[i]]
                i = pai[i]
            return i

        def _unir(a, b):
            ra, rb = _raiz(a), _raiz(b)
            if ra != rb:
                pai[rb] = ra

        por_cpf, por_nome = {}, {}
        for e in todos:
            cpf = (e.cpf or "").strip()
            if cpf:
                if cpf in por_cpf:
                    _unir(por_cpf[cpf], e.id)
                else:
                    por_cpf[cpf] = e.id
            nome = normalize_text(e.nome or "")
            if nome:
                if nome in por_nome:
                    _unir(por_nome[nome], e.id)
                else:
                    por_nome[nome] = e.id
        grupos = {}
        for e in todos:
            grupos.setdefault(_raiz(e.id), []).append(e)
        lista = [sorted(g, key=lambda x: x.id)
                 for g in grupos.values() if len(g) > 1]
        lista.sort(key=lambda g: normalize_text(g[0].nome or ""))
        return templates.TemplateResponse(
            request=request, name="funcionarios_duplicidades.html",
            context=ctx(request, grupos=lista,
                        total=len(lista),
                        funcs={e.id: e for g in lista for e in g}))

    @app.post("/funcionarios/mesclar")
    def mesclar_funcionarios(request: Request, principal_id: int = Form(0),
                             duplicado_id: int = Form(0),
                             motivo: str = Form(""),
                             user: dict = auth.require_permission("funcionarios")):
        if user["papel"] != "admin":
            flash(request, erro="Somente o administrador pode mesclar cadastros.")
            return RedirectResponse("/funcionarios/duplicidades", status_code=303)
        if not motivo or not motivo.strip():
            flash(request, erro="Informe o motivo da mescla.")
            return RedirectResponse("/funcionarios/duplicidades", status_code=303)
        if not principal_id or not duplicado_id or principal_id == duplicado_id:
            flash(request, erro="Selecione o registro principal e o duplicado.")
            return RedirectResponse("/funcionarios/duplicidades", status_code=303)
        er = EmployeeRepository()
        p, d = er.get_by_id(principal_id), er.get_by_id(duplicado_id)
        if not p or not d:
            flash(request, erro="Funcionario nao encontrado.")
            return RedirectResponse("/funcionarios/duplicidades", status_code=303)
        mov = er.mesclar(principal_id, duplicado_id)
        users.audit("mesclar-funcionarios", user["username"],
                    f"{duplicado_id}->{principal_id}",
                    motivo or "")
        total = sum(v for k, v in mov.items() if isinstance(v, int) and k != "arquivado")
        flash(request, msg=f"Cadastros mesclados: {d.nome} -> {p.nome} "
              f"({total} registro(s) movido(s); duplicado arquivado).")
        return RedirectResponse("/funcionarios/duplicidades", status_code=303)

    # ---------------- novo ----------------
    # IMPORTANTE: declarado ANTES de /funcionarios/{emp_id} — o FastAPI casa
    # rotas na ordem de declaração e "novo" seria capturado como emp_id.
    @app.get("/funcionarios/novo")
    def novo_form(request: Request,
                  user: dict = auth.require_permission("funcionarios")):
        salvo = request.session.pop("func_form", None) or {}
        fvals = salvo.get("campos", {}) if isinstance(salvo, dict) else {}
        ferros = salvo.get("erros", []) if isinstance(salvo, dict) else []
        return templates.TemplateResponse(
            request=request, name="funcionario_form.html",
            context=ctx(request, emp=None, tipos=_TIPOS_SANGUINEOS,
                        form_salvo=fvals, form_erros=ferros,
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
            request.session["func_form"] = {
                "campos": {k: v for k, v in form.items() if isinstance(v, str)},
                "erros": erros}
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
        # v1.75.0: enriquece certificados com situacao de validade e vigencia
        certificados = []
        try:
            _todos = hr.get_certificates_with_expiration(only_latest=False)
            _mapa = {c["id"]: c for c in _todos if c["employee_id"] == emp_id}
            _vigentes = {c["id"] for c in hr.get_certificates_with_expiration(
                only_latest=True) if c["employee_id"] == emp_id}
            for _r in hr.get_by_employee(emp_id):
                try:
                    _cid = _r["id"]
                    _c = dict(_r)
                except TypeError:
                    _cid = _r.id
                    _c = {"id": _r.id, "cert_number": _r.cert_number,
                          "nr_code": _r.nr_code, "data_fim": _r.data_fim,
                          "carga_horaria": _r.carga_horaria,
                          "has_signed_doc": getattr(_r, "has_signed_doc", None)}
                _m = _mapa.get(_cid, {})
                _dv = _m.get("data_validade") or ""
                _c["dias"] = _m.get("dias_para_vencer")
                _c["st"] = _m.get("status", "")
                _c["validade_br"] = f"{_dv[8:10]}/{_dv[5:7]}/{_dv[0:4]}" if _dv else ""
                _c["vigente"] = _cid in _vigentes
                certificados.append(_c)
        except Exception:
            try:
                certificados = [dict(_r) for _r in hr.get_by_employee(emp_id)]
            except Exception:
                certificados = []
        try:
            from src.core.epi_repo import EpiRepository
            epi_count = len(EpiRepository().get_by_employee(emp_id))
        except Exception:
            epi_count = 0
        asos = []
        try:
            from src.core.aso_repo import AsoRepository
            from src.web.routers.aso import _br as _aso_br, _status_e_classe as _aso_status
            for _a in AsoRepository().get_by_employee(emp_id):
                _valido, _st, _cls = _aso_status(_a["data_exame"], _a.get("validade_meses") or 12)
                asos.append({
                    "id": _a["id"], "numero": _a["aso_number"],
                    "tipo": _a["tipo_aso"], "exame_br": _aso_br(_a["data_exame"]),
                    "valido_br": _valido.strftime("%d/%m/%Y") if _valido else "",
                    "status": _st, "classe": _cls,
                    "bloqueado": bool(_a.get("bloqueado")),
                })
        except Exception:
            asos = []
        return templates.TemplateResponse(
            request=request, name="funcionario_ficha.html",
            context=ctx(request, emp=emp, docs=er.list_docs(emp_id),
                        certificados=certificados,
                        epi_count=epi_count,
                        asos=asos,
                        eh_admin=(user["papel"] == "admin"),
                        pode_aso=pode_escrever(user["papel"], "aso"),
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
        salvo = request.session.pop("func_form", None) or {}
        fvals = salvo.get("campos", {}) if isinstance(salvo, dict) else {}
        ferros = salvo.get("erros", []) if isinstance(salvo, dict) else []
        return templates.TemplateResponse(
            request=request, name="funcionario_form.html",
            context=ctx(request, emp=emp, tipos=_TIPOS_SANGUINEOS,
                        form_salvo=fvals, form_erros=ferros,
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
            request.session["func_form"] = {
                "campos": {k: v for k, v in form.items() if isinstance(v, str)},
                "erros": erros}
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
