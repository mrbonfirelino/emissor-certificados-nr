# -*- coding: utf-8 -*-
"""Portal Web — Controle de Cintos e Talabartes (v1.83.0).

Estoque separado de EPIs enviados a funcionarios em servicos em fabricas de
clientes. Itens com marca/modelo/CA/lote/numero de serie/fabricacao, badge
antichama, validade padrao de 5 anos, descarte antecipado (arquivar com
motivo), inspecoes periodicas a cada 3 meses (anexo OU relatorio interno com
texto + fotos) e entrada/saida com localizacao e confirmacao de teste.
Escrita exige admin/emissor; consulta navega em modo leitura.
"""
from typing import List
from pathlib import Path
from datetime import date, datetime, timedelta

from fastapi import Request, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, Response

from src.web import auth
from src.web.permissions import pode_escrever
from src.core.cinto_repo import (
    CintoRepository, INTERVALO_INSPESAO_MESES, CINTO_DOC_TIPOS,
    CINTO_DOC_MAX_BYTES,
)

_PER_PAGE = 20
_PER_OPCOES = (10, 20, 25, 50)
_MIME = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
         "png": "image/png"}

_CONFIRMACAO = ("Eu, {usuario}, confirmo que o equipamento foi inspecionado "
                "pela equipe de seguranca e que esta apto para uso")


def _repo() -> CintoRepository:
    return CintoRepository()


def _hoje() -> date:
    return date.today()


def _parse_data_br(s: str):
    """dd/mm/aaaa -> date, ou None."""
    try:
        return datetime.strptime((s or "").strip(), "%d/%m/%Y").date()
    except Exception:
        return None


def _fabricacao_mes_ano(s: str) -> str:
    """Aceita m/aaaa ou mm/aaaa (v1.84.1). Devolve 01/mm/aaaa ou ''."""
    s = (s or "").strip()
    try:
        mes, ano = s.split("/")
        mes_i, ano_i = int(mes), int(ano)
        if 1 <= mes_i <= 12 and 1900 <= ano_i <= 2100:
            return f"01/{mes_i:02d}/{ano_i}"
    except Exception:
        pass
    return ""


def _qs(**vals) -> str:
    """Querystring com os campos digitados, para repor o formulario (v1.84.1)."""
    from urllib.parse import urlencode
    limpo = {k: v for k, v in vals.items() if v not in (None, "")}
    return urlencode(limpo)


def _soma_meses(d: date, meses: int) -> date:
    mes = d.month - 1 + meses
    ano = d.year + mes // 12
    mes = mes % 12 + 1
    dia = min(d.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return date(ano, mes, dia)


def _ext(filename: str) -> str:
    return (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()


def _validade_de(fabricacao_br: str, meses: int) -> str:
    d = _parse_data_br(fabricacao_br)
    return _soma_meses(d, meses).strftime("%d/%m/%Y") if d else ""


def _status_inspecao(ultima: dict) -> str:
    """'' (sem inspecao = vencida) | 'ok' | 'proxima' | 'vencida'."""
    if not ultima:
        return ""
    prox = _parse_data_br(ultima.get("proxima_inspecao", ""))
    if not prox:
        return ""
    dias = (prox - _hoje()).days
    if dias < 0:
        return "vencida"
    if dias <= 7:
        return "proxima"
    return "ok"


def register(app, deps):
    templates = deps["templates"]
    ctx = deps["ctx"]
    flash = deps["flash"]

    def _pe(user):
        return pode_escrever(user["papel"], "cintos")

    def _bloqueio(request, user, url):
        if _pe(user):
            return None
        flash(request, erro="Seu papel é somente leitura neste módulo.")
        return RedirectResponse(url, status_code=303)

    def _audit(request, user, acao, alvo="", detalhe=""):
        try:
            deps["users"].audit(acao, user.get("username", ""), alvo, detalhe)
        except Exception:
            pass

    # ------------------------------------------------------------- listagem
    @app.get("/cintos")
    def cintos_lista(request: Request, busca: str = "", page: int = 1, per: int = 20,
                     antichama: str = "", arquivado: str = "nao", situacao: str = "",
                     tipo: str = "",
                     user: dict = auth.require_permission("cintos")):
        per_v = per if per in _PER_OPCOES else _PER_PAGE
        page_v = max(1, page)
        repo = _repo()
        itens, total = repo.list_items(busca=busca.strip(), antichama=antichama,
                                       arquivado=arquivado, situacao=situacao,
                                       tipo=tipo,
                                       limit=per_v, offset=(page_v - 1) * per_v)
        total = total if not situacao else total  # contagem bruta p/ paginacao
        paginas = max(1, -(-total // per_v))
        # enriquece com ultima inspecao p/ badges + flag de saida aberta (v1.84.0)
        for it in itens:
            ult = repo.ultima_inspecao(it["id"])
            it["proxima_inspecao"] = (ult or {}).get("proxima_inspecao", "")
            it["inspecao_status"] = _status_inspecao(ult)
            it["saida_aberta"] = bool(repo.saida_aberta(it["id"]))
        qs = []
        if busca.strip():
            qs.append(f"busca={busca.strip()}")
        if tipo:
            qs.append(f"tipo={tipo}")
        if antichama:
            qs.append(f"antichama={antichama}")
        if arquivado != "nao":
            qs.append(f"arquivado={arquivado}")
        if situacao:
            qs.append(f"situacao={situacao}")
        if per_v != _PER_PAGE:
            qs.append(f"per={per_v}")
        pg_base = "/cintos?" + "&".join(qs) + ("&" if qs else "")
        return templates.TemplateResponse(
            request=request, name="cintos.html",
            context=ctx(request, itens=itens, total=total, busca=busca.strip(),
                        page=page_v, paginas=paginas, per=per_v,
                        pg_base=pg_base, arquivado=arquivado, antichama=antichama,
                        situacao=situacao, tipo=tipo,
                        pode_escrever=_pe(user),
                        counts=repo.counts_situacao()))

    # --------------------------------------------------------- novo/editar
    @app.get("/cintos/novo")
    def cintos_novo(request: Request,
                    user: dict = auth.require_permission("cintos")):
        if r := _bloqueio(request, user, "/cintos"):
            return r
        # v1.84.1: repõe o que o usuario digitou quando houve erro de validacao
        q = dict(request.query_params)
        return templates.TemplateResponse(
            request=request, name="cinto_form.html",
            context=ctx(request, item=None, q=q, pode_escrever=True))

    @app.get("/cintos/{cinto_id}/editar")
    def cintos_editar(request: Request, cinto_id: int,
                      user: dict = auth.require_permission("cintos")):
        if r := _bloqueio(request, user, f"/cintos/{cinto_id}"):
            return r
        item = _repo().get(cinto_id)
        if not item:
            flash(request, erro="Item não encontrado.")
            return RedirectResponse("/cintos", status_code=303)
        return templates.TemplateResponse(
            request=request, name="cinto_form.html",
            context=ctx(request, item=item, q=dict(request.query_params),
                        pode_escrever=True))

    @app.post("/cintos/salvar")
    async def cintos_salvar(request: Request,
                            id: int = Form(0),
                            tipo: str = Form("cinto"),
                            nome: str = Form(...),
                            marca: str = Form(...),
                            modelo: str = Form(...),
                            ca: str = Form(""),
                            lote: str = Form(...),
                            numero_serie: str = Form(...),
                            data_fabricacao: str = Form(...),
                            validade_meses: int = Form(60),
                            antichama: str = Form(""),
                            observacoes: str = Form(""),
                            user: dict = auth.require_permission("cintos")):
        if r := _bloqueio(request, user, "/cintos"):
            return r
        tipo = tipo.strip().lower()
        if tipo not in ("cinto", "talabarte"):
            tipo = "cinto"
        nome = nome.strip()
        marca, modelo, lote = marca.strip(), modelo.strip(), lote.strip()
        ca = ca.strip() if tipo == "cinto" else ca.strip()
        serie = numero_serie.strip()
        qs = _qs(tipo=tipo, nome=nome, marca=marca, modelo=modelo, ca=ca,
                 lote=lote, numero_serie=serie, data_fabricacao=data_fabricacao,
                 validade_meses=validade_meses, antichama=antichama,
                 observacoes=observacoes)  # v1.84.1: repõe o digitado
        dest = lambda: (f"/cintos/{id}/editar?{qs}" if id else f"/cintos/novo?{qs}")
        # v1.84.0: CA e obrigatorio apenas para CINTO (talabarte normalmente nao tem)
        if tipo == "cinto" and not ca:
            flash(request, erro="CA é obrigatório para cintos.")
            return RedirectResponse(dest(), status_code=303)
        if not nome:
            flash(request, erro="Informe o nome do item.")
            return RedirectResponse(dest(), status_code=303)
        fab = _fabricacao_mes_ano(data_fabricacao)
        if not fab:
            flash(request, erro="Data de fabricação inválida (use mm/aaaa).")
            return RedirectResponse(dest(), status_code=303)
        # v1.84.1: fabricacao nao pode ser no futuro
        if _parse_data_br(fab) > _hoje():
            flash(request, erro="Data de fabricação não pode ser no futuro.")
            return RedirectResponse(dest(), status_code=303)
        if validade_meses < 1:
            validade_meses = 60
        repo = _repo()
        dup = repo.get_by_serie(serie)
        if dup and dup["id"] != id:
            flash(request, erro=f"Número de série já cadastrado (item {dup.get('codigo') or dup['id']} — {dup.get('nome') or dup['marca']}).")
            return RedirectResponse(dest(), status_code=303)
        dv = _validade_de(fab, validade_meses)
        iid = repo.save(id=id or None, marca=marca, modelo=modelo, ca=ca, lote=lote,
                        numero_serie=serie, data_fabricacao=fab,
                        validade_meses=validade_meses, data_validade=dv,
                        antichama=1 if antichama == "sim" else 0,
                        observacoes=observacoes.strip(), tipo=tipo, nome=nome)
        # v1.84.0: inspecao inicial = data de inclusao + 3 meses (item novo ou
        # ja inspecionado antes de entrar no sistema)
        if not id:
            prox = _soma_meses(_hoje(), INTERVALO_INSPESAO_MESES).strftime("%d/%m/%Y")
            repo.add_inspecao(cinto_id=iid,
                              data_inspecao=_hoje().strftime("%d/%m/%Y"),
                              proxima_inspecao=prox,
                              tipo="interno",
                              texto="Inspecão inicial automática — item novo ou inspecionado antes da inclusão no sistema.",
                              usuario="sistema")
        _audit(request, user, "cinto_salvar", alvo=serie, detalhe=f"id={iid}")
        flash(request, msg="Item salvo." if not id else "Item atualizado.")
        return RedirectResponse(f"/cintos/{iid}", status_code=303)

    # ---------------------------------------------------------------- ficha
    @app.get("/cintos/{cinto_id}")
    def cintos_ficha(request: Request, cinto_id: int,
                     user: dict = auth.require_permission("cintos")):
        repo = _repo()
        item = repo.get(cinto_id)
        if not item:
            flash(request, erro="Item não encontrado.")
            return RedirectResponse("/cintos", status_code=303)
        inspecoes = repo.list_inspecoes(cinto_id)
        movs = repo.list_movimentacoes(cinto_id)
        ult = inspecoes[0] if inspecoes else None
        item["proxima_inspecao"] = (ult or {}).get("proxima_inspecao", "")
        item["inspecao_status"] = _status_inspecao(ult)
        aberta = repo.saida_aberta(cinto_id)
        # v1.85.0: anexos do descarte (so quando o item esta descartado)
        desc_anexos = repo.list_descarte_anexos(cinto_id) if item.get("arquivado") else []
        return templates.TemplateResponse(
            request=request, name="cinto_ficha.html",
            context=ctx(request, item=item, inspecoes=inspecoes, movs=movs,
                        saida_aberta=aberta, desc_anexos=desc_anexos,
                        intervalo_meses=INTERVALO_INSPESAO_MESES,
                        pode_escrever=_pe(user)))

    # ------------------------------------------------------------- inspecao
    @app.post("/cintos/{cinto_id}/inspecao")
    async def cintos_inspecao(request: Request, cinto_id: int,
                              data_inspecao: str = Form(...),
                              tipo: str = Form("interno"),
                              texto: str = Form(""),
                              arquivo: UploadFile = File(None),
                              foto: UploadFile = File(None),
                              user: dict = auth.require_permission("cintos")):
        if r := _bloqueio(request, user, f"/cintos/{cinto_id}"):
            return r
        repo = _repo()
        if not repo.get(cinto_id):
            flash(request, erro="Item não encontrado.")
            return RedirectResponse("/cintos", status_code=303)
        d = _parse_data_br(data_inspecao)
        if not d:
            flash(request, erro="Data de inspeção inválida.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        # v1.84.1: inspecao so no estoque, e nao pode ser no futuro
        if repo.saida_aberta(cinto_id):
            flash(request, erro="Só é possível registrar inspeção com o item no estoque.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        if d > _hoje():
            flash(request, erro="Data de inspeção não pode ser no futuro.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        prox = _soma_meses(d, INTERVALO_INSPESAO_MESES).strftime("%d/%m/%Y")
        dados, filename, tipo_arquivo, texto_v = b"", "", "", (texto or "").strip()
        fotos, fotos_tipo = b"", ""
        if tipo == "arquivo":
            if arquivo and arquivo.filename:
                filename = arquivo.filename
                if _ext(filename) not in CINTO_DOC_TIPOS:
                    flash(request, erro="Formato não permitido (use PDF, JPG ou PNG).")
                    return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
                dados = await arquivo.read()
                tipo_arquivo = _MIME.get(_ext(filename), "application/octet-stream")
            if not dados:
                flash(request, erro="Selecione o arquivo do relatório de inspeção.")
                return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        else:
            if not texto_v:
                flash(request, erro="Descreva o resultado da inspeção (texto obrigatório).")
                return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
            if foto and foto.filename:
                if _ext(foto.filename) not in {"jpg", "jpeg", "png"}:
                    flash(request, erro="Foto deve ser JPG ou PNG.")
                    return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
                fotos = await foto.read()
                fotos_tipo = _MIME.get(_ext(foto.filename), "application/octet-stream")
        try:
            repo.add_inspecao(cinto_id=cinto_id,
                              data_inspecao=d.strftime("%d/%m/%Y"),
                              proxima_inspecao=prox,
                              tipo=tipo, filename=filename, dados=dados,
                              tipo_arquivo=tipo_arquivo, texto=texto_v,
                              fotos=fotos, fotos_tipo=fotos_tipo,
                              usuario=user.get("username", ""))
        except ValueError as e:
            flash(request, erro=str(e))
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        _audit(request, user, "cinto_inspecao", alvo=f"id={cinto_id}", detalhe=prox)
        flash(request, msg=f"Inspeção registrada. Próxima: {prox}.")
        return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)

    @app.get("/cintos/inspecao/{inspecao_id}/download")
    def cintos_inspecao_download(request: Request, inspecao_id: int,
                                 user: dict = auth.require_permission("cintos")):
        insp = _repo().get_inspecao(inspecao_id)
        if not insp or not insp.get("dados"):
            flash(request, erro="Arquivo não encontrado.")
            return RedirectResponse("/cintos", status_code=303)
        return Response(content=bytes(insp["dados"]), media_type=insp.get("tipo_arquivo") or "application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{insp.get("filename") or "inspecao"}"'})

    @app.get("/cintos/inspecao/{inspecao_id}/foto")
    def cintos_inspecao_foto(request: Request, inspecao_id: int,
                             user: dict = auth.require_permission("cintos")):
        insp = _repo().get_inspecao(inspecao_id)
        if not insp or not insp.get("fotos"):
            return Response(status_code=404)
        return Response(content=bytes(insp["fotos"]), media_type=insp.get("fotos_tipo") or "image/jpeg")

    # ------------------------------------------------- saida/entrada/loc.
    @app.post("/cintos/{cinto_id}/saida")
    async def cintos_saida(request: Request, cinto_id: int,
                           data: str = Form(...),
                           destino: str = Form(...),
                           testado: str = Form(""),
                           observacoes: str = Form(""),
                           voltar: str = Form(""),
                           user: dict = auth.require_permission("cintos")):
        if r := _bloqueio(request, user, f"/cintos/{cinto_id}"):
            return r
        repo = _repo()
        if not repo.get(cinto_id):
            flash(request, erro="Item não encontrado.")
            return RedirectResponse("/cintos", status_code=303)
        # v1.84.0: exigido marcar que o equipamento foi inspecionado/apto
        if not testado:
            flash(request, erro="Confirme que o equipamento foi inspecionado e está apto para uso.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        if repo.saida_aberta(cinto_id):
            flash(request, erro="Este item já tem uma saída em aberto. Registre a entrada primeiro.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        d = _parse_data_br(data)
        if not d:
            flash(request, erro="Data de saída inválida.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        # v1.84.1: saida nao pode ser no futuro
        if d > _hoje():
            flash(request, erro="Data de saída não pode ser no futuro.")
            return RedirectResponse(f"/cintos/{cinto_id}" if voltar != "lista" else "/cintos", status_code=303)
        resp = user.get("username", "")
        confirmacao = _CONFIRMACAO.format(usuario=resp) if testado else ""
        repo.add_movimentacao(cinto_id=cinto_id, tipo="saida",
                              data=d.strftime("%d/%m/%Y"), destino=destino.strip(),
                              responsavel=resp, testado=1 if testado else 0,
                              confirmacao=confirmacao, observacoes=observacoes.strip())
        repo.set_localizacao(cinto_id, destino.strip())
        _audit(request, user, "cinto_saida", alvo=f"id={cinto_id}", detalhe=destino.strip())
        flash(request, msg=f"Saída registrada. Localização atual: {destino.strip()}.")
        return RedirectResponse("/cintos" if voltar == "lista" else f"/cintos/{cinto_id}", status_code=303)

    @app.post("/cintos/{cinto_id}/entrada")
    async def cintos_entrada(request: Request, cinto_id: int,
                             data: str = Form(...),
                             testado: str = Form(""),
                             resultado: str = Form("apto"),
                             observacoes: str = Form(""),
                             voltar: str = Form(""),
                             user: dict = auth.require_permission("cintos")):
        if r := _bloqueio(request, user, f"/cintos/{cinto_id}"):
            return r
        repo = _repo()
        if not repo.get(cinto_id):
            flash(request, erro="Item não encontrado.")
            return RedirectResponse("/cintos", status_code=303)
        aberta = repo.saida_aberta(cinto_id)
        if not aberta:
            flash(request, erro="Não há saída em aberto para este item.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        # v1.84.1: exige marcar que o item foi inspecionado (resultado a parte)
        if not testado:
            flash(request, erro="Confirme que o item foi inspecionado.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        d = _parse_data_br(data)
        if not d:
            flash(request, erro="Data de entrada inválida.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        # v1.84.1: entrada nao pode ser no futuro nem anterior a saida
        if d > _hoje():
            flash(request, erro="Data de entrada não pode ser no futuro.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        d_saida = _parse_data_br(aberta.get("data") or "")
        if d_saida and d < d_saida:
            flash(request, erro="Data de entrada anterior à data da saída.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        danificado = resultado == "danificado"
        resp = user.get("username", "")
        # v1.84.1: item pode voltar danificado — nao afirmar "apto para uso"
        if danificado:
            confirmacao = f"Item retornou DANIFICADO — registro feito por {resp}."
        else:
            confirmacao = _CONFIRMACAO.format(usuario=resp)
        repo.add_movimentacao(cinto_id=cinto_id, tipo="entrada",
                              data=d.strftime("%d/%m/%Y"),
                              responsavel=resp, testado=1,
                              confirmacao=confirmacao, observacoes=observacoes.strip(),
                              resultado="danificado" if danificado else "apto")
        repo.set_localizacao(cinto_id, "Estoque")
        _audit(request, user, "cinto_entrada", alvo=f"id={cinto_id}")
        if danificado:
            flash(request, msg="Entrada registrada. ATENÇÃO: item retornou danificado — avalie o descarte.")
        else:
            flash(request, msg="Entrada registrada. Item de volta ao estoque.")
        return RedirectResponse("/cintos" if voltar == "lista" else f"/cintos/{cinto_id}", status_code=303)

    # ------------------------------------------------- arquivar/descartar
    @app.post("/cintos/{cinto_id}/arquivar")
    async def cintos_arquivar(request: Request, cinto_id: int,
                              motivo: str = Form(...),
                              acao: str = Form("arquivar"),
                              anexos: List[UploadFile] = File(None),
                              user: dict = auth.require_permission("cintos")):
        if r := _bloqueio(request, user, f"/cintos/{cinto_id}"):
            return r
        repo = _repo()
        item = repo.get(cinto_id)
        if not item:
            flash(request, erro="Item não encontrado.")
            return RedirectResponse("/cintos", status_code=303)
        # v1.84.0: nao permite descartar item com saida em aberto (so no estoque)
        if acao != "reativar" and repo.saida_aberta(cinto_id):
            flash(request, erro="Item com saída em aberto — registre a entrada antes de descartar.")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        motivo = motivo.strip()
        # v1.83.0: motivo so e obrigatorio ao arquivar/descartar (reativar nao precisa)
        if acao != "reativar" and not motivo:
            flash(request, erro="Informe o motivo (descarte, desgaste, retenção de queda etc.).")
            return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        arq = acao != "reativar"
        # v1.85.0: anexos (fotos/documentos) enviados junto ao descarte
        lidos = []
        if arq:
            for a in (anexos or []):
                if not a or not getattr(a, "filename", ""):
                    continue
                ext = _ext(a.filename)
                if ext not in CINTO_DOC_TIPOS:
                    flash(request, erro="Formato de anexo não permitido (use PDF, JPG ou PNG).")
                    return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
                dados = await a.read()
                if len(dados) > CINTO_DOC_MAX_BYTES:
                    flash(request, erro="Anexo excede o limite de 30 MB.")
                    return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
                lidos.append((Path(a.filename).name, dados, ext))
        repo.set_arquivado(cinto_id, arq, motivo=motivo,
                           usuario=user.get("username", ""))
        for nome_f, dados, ext in lidos:
            try:
                repo.add_descarte_anexo(cinto_id=cinto_id, filename=nome_f,
                                        dados=dados, tipo_arquivo=ext,
                                        usuario=user.get("username", ""))
            except ValueError:
                flash(request, erro="Anexo excede o limite de 30 MB.")
                return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)
        _audit(request, user, "cinto_arquivar" if arq else "cinto_reativar",
               alvo=f"id={cinto_id}", detalhe=motivo)
        flash(request, msg="Item descartado (arquivado)." if arq else "Item reativado ao estoque.")
        return RedirectResponse(f"/cintos/{cinto_id}", status_code=303)

    # v1.85.0: download/preview dos anexos do descarte
    @app.get("/cintos/descarte/{anexo_id}/download")
    def cinto_descarte_download(anexo_id: int,
                                user: dict = auth.require_permission("cintos")):
        a = _repo().get_descarte_anexo(anexo_id)
        if not a or not a.get("dados"):
            raise HTTPException(status_code=404)
        return Response(content=bytes(a["dados"]),
                        media_type=_MIME.get(a.get("tipo_arquivo") or "", "application/octet-stream"),
                        headers={"Content-Disposition": f'attachment; filename="{a["filename"]}"'})

    @app.get("/cintos/descarte/{anexo_id}/foto")
    def cinto_descarte_foto(anexo_id: int,
                            user: dict = auth.require_permission("cintos")):
        a = _repo().get_descarte_anexo(anexo_id)
        if not a or not a.get("dados") or a.get("tipo_arquivo") not in ("jpg", "png"):
            raise HTTPException(status_code=404)
        return Response(content=bytes(a["dados"]),
                        media_type=_MIME.get(a["tipo_arquivo"], "application/octet-stream"))
