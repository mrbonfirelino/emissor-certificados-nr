"""Listas de Presenca (v1.36.0; fluxo do dia v1.37.0).

- GET  /presencas                lista (busca + paginacao + contadores)
- GET  /presencas/nova           escolhe a data e ve as secoes por NR do dia
- GET  /presencas/avulsa         v1.86.0: lista separada (colaboradores livres, data qualquer)
- POST /presencas/emitir-avulsa  gera a lista avulsa
- POST /presencas/emitir-dia     gera as listas de todas as NRs marcadas
- GET  /presencas/resultado      resumo do dia + dialog do compilado
- GET  /presencas/compilado/{iso}  PDF unico com todas as listas da data
- GET  /presencas/{pid}          detalhe
- POST /presencas/{pid}/status   muda status (pendente/parcial/assinada)
- POST /presencas/{pid}/assinar  anexa lista assinada (pdf/jpg/png)
- GET  /presencas/{pid}/assinada download do anexo
- POST /presencas/{pid}/assinada/excluir
- GET  /presencas/{pid}/pdf (+/pdf/download)
- POST /presencas/{pid}/excluir
"""

from pathlib import Path
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response

from src.web import auth
from src.core.presenca_repo import PresencaRepository, STATUS_VALIDOS
from src.core import presenca_generator
from src.utils.error_log import log_error

_PER_PAGE = 20
_ASSINADA_MAX = 50 * 1024 * 1024
_MIME = {"pdf": "application/pdf", "jpg": "image/jpeg",
         "jpeg": "image/jpeg", "png": "image/png"}

_STATUS_CLASSE = {"pendente": "b-amarelo", "parcial": "b-azul", "assinada": "b-verde"}
_STATUS_LABEL = {"pendente": "Pendente", "parcial": "Parcial", "assinada": "Assinada"}


def _br(iso: str) -> str:
    if not iso or len(iso) < 10:
        return iso or "—"
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


def _iso(txt: str) -> str:
    txt = (txt or "").strip()
    if not txt:
        return ""
    if len(txt) == 10 and txt[2] == "/":
        return f"{txt[6:]}-{txt[3:5]}-{txt[0:2]}"
    return txt[:10]


def register(app, deps):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]
    users = deps["users"]
    router = APIRouter()

    @router.get("/presencas")
    def lista(request: Request, user=auth.require_permission("presencas"),
              busca: str = "", page: int = 1, per: int = 10,
              arquivado: str = "nao"):
        repo = PresencaRepository()
        busca = (busca or "").strip()
        per = per if per in (10, 20, 25, 50) else 10
        arquivado = arquivado if arquivado in ("nao", "sim", "todos") else "nao"
        _, total = repo.list(busca=busca, limit=1, offset=0, arquivado=arquivado)
        paginas = max(1, (total + per - 1) // per)
        page = max(1, min(page, paginas))
        itens, _t = repo.list(busca=busca, limit=per, offset=(page - 1) * per,
                              arquivado=arquivado)
        for it in itens:
            it["data_br"] = _br(it["data_ref"])
            it["status_label"] = _STATUS_LABEL.get(it["status"], it["status"])
            it["status_classe"] = _STATUS_CLASSE.get(it["status"], "b-cinza")
        contagem = repo.count_por_status()
        pg_base = "/presencas?busca=" + quote_plus(busca) if busca else "/presencas"
        pg_base += ("&" if "?" in pg_base else "?") + "per=" + str(per)
        if arquivado != "nao":
            pg_base += "&arquivado=" + arquivado
        return templates.TemplateResponse(request, "presencas.html", ctx(
            request, user=user,
            itens=itens, total=total, page=page, paginas=paginas, pg_base=pg_base, per=per,
            busca=busca, arquivado=arquivado,
            pode_escrever=auth.pode_escrever(user["papel"], "presencas"),
            pend=contagem.get("pendente", 0), parcial=contagem.get("parcial", 0),
            assinadas=contagem.get("assinada", 0),
        ))

    @router.post("/presencas/{pid}/arquivar")
    def presenca_arquivar(pid: int, request: Request, motivo: str = Form(""),
                          user=auth.require_permission("presencas")):
        """v1.77.0: arquivar lista de presenca (com motivo via popup)."""
        if not auth.pode_escrever(user["papel"], "presencas"):
            flash(request, erro="Sem permissão para arquivar listas.")
            return RedirectResponse("/presencas", status_code=303)
        PresencaRepository().set_arquivado(pid, 1)
        try:
            users.audit("presenca-arquivar", user.get("username", ""), str(pid),
                        motivo or "")
        except Exception:
            pass
        flash(request, msg=f"Lista de presença #{pid} arquivada.")
        return RedirectResponse("/presencas", status_code=303)

    @router.post("/presencas/{pid}/desarquivar")
    def presenca_desarquivar(pid: int, request: Request,
                             user=auth.require_permission("presencas")):
        if not auth.pode_escrever(user["papel"], "presencas"):
            flash(request, erro="Sem permissão.")
            return RedirectResponse("/presencas?arquivado=sim", status_code=303)
        PresencaRepository().set_arquivado(pid, 0)
        flash(request, msg=f"Lista de presença #{pid} desarquivada.")
        return RedirectResponse("/presencas?arquivado=sim", status_code=303)

    def _nr_label(nr: str) -> str:
        if nr == "FDS":  # v1.86.0: lista FDS/FISPQ (registry)
            return "FDS — FISPQ (Ficha de Dados de Segurança)"
        try:
            from src.core.template_loader import load_all_templates
            t = load_all_templates().get(nr)
            if t is not None and getattr(t, "nr_name", None):
                return t.nr_name
        except Exception:
            pass
        return nr

    @router.get("/presencas/nova")
    def nova(request: Request, user=auth.require_permission("presencas"),
             data: str = ""):
        modelo = {c: True for c in presenca_generator.tipos_com_modelo()}
        iso = _iso(data)
        secoes = []
        if iso:
            try:
                from src.core.history_repo import HistoryRepository
                emissoes = HistoryRepository().query(
                    data_de=iso, data_ate=iso, limit=10000)
            except Exception:
                emissoes = []
            nrs_do_dia = sorted({r.nr_code for r in emissoes})
            for nr in nrs_do_dia:
                try:
                    part, carga = presenca_generator.participantes_da_emissao(nr, iso)
                except Exception:
                    part, carga = [], 0
                if not part:
                    continue
                secoes.append({
                    "nr": nr, "participantes": part, "carga": carga,
                    "tem_modelo": modelo.get(nr, False),
                    "label": _nr_label(nr),
                })
        return templates.TemplateResponse(request, "presencas_nova.html", ctx(
            request, user=user,
            data=data, iso=iso, data_br=_br(iso), secoes=secoes,
            pode_escrever=auth.pode_escrever(user["papel"], "presencas"),
        ))

    @router.post("/presencas/emitir-dia")
    async def emitir_dia(request: Request, user=auth.require_permission("presencas")):
        if not auth.pode_escrever(user["papel"], "presencas"):
            flash(request, erro="Sem permissão para escrever neste módulo.")
            return RedirectResponse("/presencas", status_code=303)
        form = await request.form()
        data_txt = (form.get("data") or "").strip()
        iso = _iso(data_txt)
        if not iso:
            flash(request, erro="Informe a data das listas.")
            return RedirectResponse("/presencas/nova", status_code=303)
        marcadas = sorted({k[len("incluir_"):] for k in form.keys()
                           if k.startswith("incluir_")})
        if not marcadas:
            flash(request, erro="Nenhuma NR selecionada.")
            return RedirectResponse(f"/presencas/nova?data={quote_plus(data_txt)}",
                                    status_code=303)

        repo = PresencaRepository()
        geradas, falhas = [], []
        for nr in marcadas:
            try:
                participantes, carga = presenca_generator.participantes_da_emissao(nr, iso)
            except Exception as e:
                log_error("portal-presencas", e)
                participantes, carga = [], 0
            if not participantes:
                falhas.append({"nr": nr, "motivo": "sem emissões nesta data"})
                continue
            nr_label = _nr_label(nr)
            pid, serial = repo.add(
                nr_code=nr, nr_label=nr_label, data_ref=iso, carga_horaria=carga,
                participantes=participantes, assunto=nr_label,
                criado_por=(user.get("username") or ""),
            )
            saida = presenca_generator.get_listas_dir() / f"{serial}.pdf"
            try:
                presenca_generator.gerar_pdf_lista(
                    nr, nr_label, iso, carga, participantes, nr_label, saida,
                    serial=serial)
            except Exception as e:
                repo.delete(pid)
                log_error("portal-presencas", e)
                falhas.append({"nr": nr, "motivo": f"falha ao gerar PDF: {e}"})
                continue
            repo.set_pdf_path(pid, str(saida))
            geradas.append({"pid": pid, "serial": serial, "nr": nr,
                            "n": len(participantes)})

        if geradas:
            try:
                users.audit("listas-presenca-dia", user.get("username", ""), iso,
                            f"{len(geradas)} lista(s): "
                            + ", ".join(g["nr"] for g in geradas))
            except Exception:
                pass
        request.session["presencas_dia"] = {
            "data": iso, "geradas": geradas, "falhas": falhas,
        }
        return RedirectResponse("/presencas/resultado", status_code=303)

    # ── v1.86.0: lista avulsa (colaboradores livres, data qualquer) ──

    @router.get("/presencas/avulsa")
    def avulsa(request: Request, user=auth.require_permission("presencas")):
        """Lista separada: o usuario escolhe a NR, a data (futura ou passada)
        e os colaboradores livremente — sem depender de emissao do dia."""
        modelo = {c: True for c in presenca_generator.tipos_com_modelo()}
        nrs = []
        try:
            from src.core.template_loader import load_all_templates
            for codigo, t in sorted(load_all_templates().items()):
                nrs.append({"codigo": codigo,
                            "label": getattr(t, "nr_name", "") or codigo,
                            "tem_modelo": modelo.get(codigo, False)})
        except Exception:
            pass
        if not any(n["codigo"] == "FDS" for n in nrs):  # v1.86.0: lista FDS
            nrs.append({"codigo": "FDS",
                        "label": "FDS — FISPQ (Ficha de Dados de Segurança)",
                        "tem_modelo": "FDS" in modelo})
        funcs = []
        try:
            from src.core.employee_repo import EmployeeRepository
            funcs = [{"id": e.id, "nome": e.nome, "funcao": (e.funcao or "")}
                     for e in EmployeeRepository().get_all(limit=100000)]
            funcs.sort(key=lambda f: (f["nome"] or "").upper())
        except Exception:
            funcs = []
        return templates.TemplateResponse(request, "presencas_avulsa.html", ctx(
            request, user=user, nrs=nrs, funcionarios=funcs,
            pode_escrever=auth.pode_escrever(user["papel"], "presencas"),
        ))

    @router.post("/presencas/emitir-avulsa")
    async def emitir_avulsa(request: Request,
                            user=auth.require_permission("presencas")):
        if not auth.pode_escrever(user["papel"], "presencas"):
            flash(request, erro="Sem permissão para escrever neste módulo.")
            return RedirectResponse("/presencas", status_code=303)
        form = await request.form()
        iso = _iso(form.get("data"))
        if not iso:
            flash(request, erro="Informe a data da lista.")
            return RedirectResponse("/presencas/avulsa", status_code=303)
        nr = (form.get("nr") or "").strip().upper()
        if not nr:
            flash(request, erro="Escolha a NR do treinamento.")
            return RedirectResponse("/presencas/avulsa", status_code=303)
        try:
            carga = float(str(form.get("carga") or "0").replace(",", "."))
        except ValueError:
            carga = 0.0
        ids = []
        for k in form.keys():
            if k.startswith("emp_"):
                try:
                    ids.append(int(k[len("emp_"):]))
                except ValueError:
                    pass
        participantes = []
        vistos = set()
        if ids:
            try:
                from src.core.employee_repo import EmployeeRepository
                er = EmployeeRepository()
                for i in sorted(set(ids)):
                    emp = er.get_by_id(i)
                    if emp is None:
                        continue
                    chave = (emp.nome or "").strip().upper()
                    if not chave or chave in vistos:
                        continue
                    vistos.add(chave)
                    participantes.append({"nome": emp.nome,
                                          "funcao": emp.funcao or "",
                                          "cpf": emp.cpf or ""})
            except Exception as e:
                log_error("portal-presencas", e)
        for linha in (form.get("nomes_extras") or "").splitlines():
            nome = linha.strip()
            chave = nome.upper()
            if not nome or chave in vistos:
                continue
            vistos.add(chave)
            participantes.append({"nome": nome, "funcao": "", "cpf": ""})
        if not participantes:
            flash(request, erro="Selecione ao menos um colaborador ou digite um nome.")
            return RedirectResponse("/presencas/avulsa", status_code=303)

        nr_label = _nr_label(nr)
        repo = PresencaRepository()
        pid, serial = repo.add(
            nr_code=nr, nr_label=nr_label, data_ref=iso, carga_horaria=carga,
            participantes=participantes, assunto=nr_label,
            criado_por=(user.get("username") or ""),
        )
        saida = presenca_generator.get_listas_dir() / f"{serial}.pdf"
        falhas = []
        try:
            presenca_generator.gerar_pdf_lista(
                nr, nr_label, iso, carga, participantes, nr_label, saida,
                serial=serial)
        except Exception as e:
            repo.delete(pid)
            log_error("portal-presencas", e)
            falhas.append({"nr": nr, "motivo": f"falha ao gerar PDF: {e}"})
        else:
            repo.set_pdf_path(pid, str(saida))
            geradas = [{"pid": pid, "serial": serial, "nr": nr,
                        "n": len(participantes)}]
            try:
                users.audit("lista-presenca-avulsa", user.get("username", ""),
                            iso, f"{nr}: {len(participantes)} participante(s)")
            except Exception:
                pass
            request.session["presencas_dia"] = {
                "data": iso, "geradas": geradas, "falhas": falhas,
            }
            return RedirectResponse("/presencas/resultado", status_code=303)
        flash(request, erro="; ".join(f["motivo"] for f in falhas))
        return RedirectResponse("/presencas/avulsa", status_code=303)

    @router.get("/presencas/resultado")
    def resultado(request: Request, user=auth.require_permission("presencas")):
        info = request.session.pop("presencas_dia", None)
        if not info:
            return RedirectResponse("/presencas", status_code=303)
        info["data_br"] = _br(info.get("data", ""))
        return templates.TemplateResponse(request, "presencas_resultado.html", ctx(
            request, user=user, info=info,
            pode_escrever=auth.pode_escrever(user["papel"], "presencas"),
        ))

    @router.get("/presencas/compilado/{iso}")
    def compilado(request: Request, iso: str, ids: str = "",
                  user=auth.require_permission("presencas")):
        iso = _iso(iso)
        repo = PresencaRepository()
        if ids.strip():
            # compilado da EMISSAO: apenas as listas geradas agora, na ordem
            listas = []
            for pid_txt in ids.split(","):
                try:
                    pid = int(pid_txt.strip())
                except ValueError:
                    continue
                it = repo.get(pid)
                if it and it.get("pdf_path") and Path(it["pdf_path"]).exists():
                    listas.append(it)
        else:
            # compilado de um dia inteiro (mini-form da listagem)
            listas = [l for l in repo.list_por_data(iso)
                      if l.get("pdf_path") and Path(l["pdf_path"]).exists()]
        if not listas:
            flash(request, erro=f"Nenhuma lista com PDF encontrada para {_br(iso)}.")
            return RedirectResponse("/presencas", status_code=303)
        import fitz

        doc = fitz.open()
        try:
            for l in listas:
                src = fitz.open(l["pdf_path"])
                try:
                    doc.insert_pdf(src)
                finally:
                    src.close()
            dados = doc.tobytes()
        finally:
            doc.close()
        filename = f"Listas de Presenca {_br(iso).replace('/', '-')}.pdf"
        return Response(content=dados, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="{filename}"'})

    @router.get("/presencas/{pid}")
    def detalhe(request: Request, pid: int,
                user=auth.require_permission("presencas")):
        repo = PresencaRepository()
        it = repo.get(pid)
        if it is None:
            flash(request, erro="Lista não encontrada.")
            return RedirectResponse("/presencas", status_code=303)
        it["data_br"] = _br(it["data_ref"])
        it["status_label"] = _STATUS_LABEL.get(it["status"], it["status"])
        it["status_classe"] = _STATUS_CLASSE.get(it["status"], "b-cinza")
        anexo = repo.get_signed(pid)
        return templates.TemplateResponse(request, "presenca_detalhe.html", ctx(
            request, user=user, it=it,
            anexo_nome=anexo[2] if anexo else None,
            status_opcoes=STATUS_VALIDOS,
            pode_escrever=auth.pode_escrever(user["papel"], "presencas"),
        ))

    @router.post("/presencas/{pid}/status")
    async def mudar_status(request: Request, pid: int,
                           user=auth.require_permission("presencas")):
        if not auth.pode_escrever(user["papel"], "presencas"):
            flash(request, erro="Sem permissão para escrever neste módulo.")
            return RedirectResponse(f"/presencas/{pid}", status_code=303)
        form = await request.form()
        novo = (form.get("status") or "").strip().lower()
        repo = PresencaRepository()
        try:
            repo.set_status(pid, novo)
            flash(request, msg=f"Status alterado para {_STATUS_LABEL.get(novo, novo)}.")
        except ValueError:
            flash(request, erro="Status inválido.")
        return RedirectResponse(f"/presencas/{pid}", status_code=303)

    @router.post("/presencas/{pid}/assinar")
    async def assinar(request: Request, pid: int,
                      user=auth.require_permission("presencas"),
                      arquivo: UploadFile = File(None)):
        if not auth.pode_escrever(user["papel"], "presencas"):
            flash(request, erro="Sem permissão para escrever neste módulo.")
            return RedirectResponse(f"/presencas/{pid}", status_code=303)
        if arquivo is None or not arquivo.filename:
            flash(request, erro="Escolha o arquivo da lista assinada (PDF, JPG ou PNG).")
            return RedirectResponse(f"/presencas/{pid}", status_code=303)
        ext = Path(arquivo.filename).suffix.lower().lstrip(".")
        if ext not in _MIME:
            flash(request, erro="Formato não permitido. Use PDF, JPG ou PNG.")
            return RedirectResponse(f"/presencas/{pid}", status_code=303)
        dados = await arquivo.read()
        if len(dados) > _ASSINADA_MAX:
            flash(request, erro="Arquivo maior que 50 MB.")
            return RedirectResponse(f"/presencas/{pid}", status_code=303)
        PresencaRepository().attach_signed(pid, dados, _MIME[ext], arquivo.filename)
        try:
            users.audit("lista-presenca-assinar", user.get("username", ""), str(pid),
                        arquivo.filename)
        except Exception:
            pass
        flash(request, msg="Lista assinada anexada — status: Assinada.")
        return RedirectResponse(f"/presencas/{pid}", status_code=303)

    @router.get("/presencas/{pid}/assinada")
    def baixar_assinada(pid: int, user=auth.require_permission("presencas")):
        anexo = PresencaRepository().get_signed(pid)
        if anexo is None:
            return RedirectResponse(f"/presencas/{pid}", status_code=303)
        dados, tipo, filename = anexo
        return Response(content=dados, media_type=tipo, headers={
            "Content-Disposition": f'attachment; filename="{filename}"'})

    @router.post("/presencas/{pid}/assinada/excluir")
    async def excluir_assinada(request: Request, pid: int,
                               user=auth.require_permission("presencas")):
        if not auth.pode_escrever(user["papel"], "presencas"):
            flash(request, erro="Sem permissão para escrever neste módulo.")
            return RedirectResponse(f"/presencas/{pid}", status_code=303)
        PresencaRepository().remove_signed(pid)
        flash(request, msg="Anexo da lista assinada removido — status voltou para Pendente.")
        return RedirectResponse(f"/presencas/{pid}", status_code=303)

    @router.get("/presencas/{pid}/pdf")
    def ver_pdf(request: Request, pid: int, user=auth.require_permission("presencas")):
        return _responder_pdf(request, pid, attachment=False)

    @router.get("/presencas/{pid}/pdf/download")
    def baixar_pdf(request: Request, pid: int, user=auth.require_permission("presencas")):
        return _responder_pdf(request, pid, attachment=True)

    def _responder_pdf(request: Request, pid: int, attachment: bool):
        repo = PresencaRepository()
        it = repo.get(pid)
        if it is None or not it.get("pdf_path") or not Path(it["pdf_path"]).exists():
            flash(request, erro="PDF da lista não encontrado.")
            return RedirectResponse(f"/presencas/{pid}", status_code=303)
        kwargs = {}
        if attachment:
            kwargs["filename"] = f"{it['serial']}.pdf"
        return FileResponse(it["pdf_path"], media_type="application/pdf", **kwargs)

    @router.post("/presencas/{pid}/excluir")
    async def excluir(request: Request, pid: int,
                      user=auth.require_permission("presencas")):
        if not auth.pode_escrever(user["papel"], "presencas"):
            flash(request, erro="Sem permissão para escrever neste módulo.")
            return RedirectResponse("/presencas", status_code=303)
        repo = PresencaRepository()
        it = repo.get(pid)
        if it is None:
            return RedirectResponse("/presencas", status_code=303)
        repo.delete(pid)
        try:
            if it.get("pdf_path"):
                Path(it["pdf_path"]).unlink(missing_ok=True)
        except Exception:
            pass
        try:
            users.audit("lista-presenca-excluir", user.get("username", ""), it["serial"],
                        it.get("nr_code", ""))
        except Exception:
            pass
        flash(request, msg=f"Lista {it['serial']} excluída.")
        return RedirectResponse("/presencas", status_code=303)

    app.include_router(router)
