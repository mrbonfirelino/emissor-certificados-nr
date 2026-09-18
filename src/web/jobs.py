"""Jobs de longa duracao (emissao em lote, importacoes) com progresso.

Registro em memoria, thread-safe. O portal roda em processo unico
(uvicorn/waitress), portanto o dicionario em memoria e suficiente.

Fluxo:
    job = criar_job(titulo="Emissao em lote")
    thread = threading.Thread(target=..., args=(job["id"], ...))
    ...
    job_iniciar(job["id"], total=40)
    job_progresso(job["id"], 5, nome="Maria")
    job_finalizar(job["id"], redirect="/emissao-lote/resultado/<id>")
"""

import threading
import time
import uuid

_LOCK = threading.Lock()
_JOBS: dict = {}
_TTL = 24 * 3600  # limpa jobs com mais de 24h


def _limpar() -> None:
    agora = time.time()
    antigos = [jid for jid, j in _JOBS.items() if agora - j["criado"] > _TTL]
    for jid in antigos:
        _JOBS.pop(jid, None)


def criar_job(titulo: str = "") -> dict:
    with _LOCK:
        _limpar()
        jid = uuid.uuid4().hex
        job = {
            "id": jid,
            "titulo": titulo,
            "status": "pendente",  # pendente | executando | concluido | erro
            "total": 0,
            "atual": 0,
            "nome": "",
            "logs": [],
            "erros": [],
            "erro_fatal": "",
            "redirect": "",
            "resultado": None,
            "criado": time.time(),
        }
        _JOBS[jid] = job
        return job


def obter_job(jid: str) -> dict | None:
    with _LOCK:
        j = _JOBS.get(jid)
        return dict(j) if j else None


def job_iniciar(jid: str, total: int) -> None:
    with _LOCK:
        j = _JOBS.get(jid)
        if j:
            j["status"] = "executando"
            j["total"] = max(int(total), 0)


def job_progresso(jid: str, atual: int, nome: str = "") -> None:
    with _LOCK:
        j = _JOBS.get(jid)
        if j:
            j["atual"] = max(int(atual), 0)
            j["nome"] = nome or ""


def job_log(jid: str, msg: str) -> None:
    with _LOCK:
        j = _JOBS.get(jid)
        if j:
            j["logs"].append(str(msg))
            if len(j["logs"]) > 500:
                del j["logs"][: len(j["logs"]) - 500]


def job_erro(jid: str, msg: str) -> None:
    with _LOCK:
        j = _JOBS.get(jid)
        if j:
            j["erros"].append(str(msg))


def job_finalizar(jid: str, redirect: str = "", erro_fatal: str = "") -> None:
    with _LOCK:
        j = _JOBS.get(jid)
        if j:
            if erro_fatal:
                j["status"] = "erro"
                j["erro_fatal"] = erro_fatal
            else:
                j["status"] = "concluido"
                j["atual"] = j["total"]
            j["redirect"] = redirect


def job_resultado(jid: str, data: dict) -> None:
    with _LOCK:
        j = _JOBS.get(jid)
        if j:
            j["resultado"] = data


def snapshot(jid: str) -> dict | None:
    """Resumo para o endpoint de polling."""
    with _LOCK:
        j = _JOBS.get(jid)
        if not j:
            return None
        total = j["total"] or 1
        pct = min(100, int(j["atual"] * 100 / total)) if j["status"] != "pendente" else 0
        return {
            "id": j["id"],
            "status": j["status"],
            "total": j["total"],
            "atual": j["atual"],
            "pct": pct if j["status"] != "concluido" else 100,
            "nome": j["nome"],
            "n_erros": len(j["erros"]),
            "erro_fatal": j["erro_fatal"],
            "redirect": j["redirect"],
            "titulo": j["titulo"],
        }


def dados_resultado(jid: str) -> dict | None:
    """Dados completos (logs/erros) para a pagina de resultado."""
    with _LOCK:
        j = _JOBS.get(jid)
        if not j:
            return None
        return {
            "id": j["id"],
            "titulo": j["titulo"],
            "status": j["status"],
            "total": j["total"],
            "atual": j["atual"],
            "logs": list(j["logs"]),
            "erros": list(j["erros"]),
            "erro_fatal": j["erro_fatal"],
            "resultado": j["resultado"],
        }
