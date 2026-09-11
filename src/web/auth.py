"""Autenticacao do portal: sessao, current_user, guards e rate-limit de login."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request

from src.web.permissions import pode, pode_escrever  # noqa: F401 (pode_escrever re-export p/ routers)

# rate-limit simples em memoria: ip -> lista de tentativas com falha
_falhas: dict = {}
MAX_FALHAS = 5
JANELA_MINUTOS = 5


def login_excedido(ip: str) -> bool:
    agora = datetime.now()
    registros = [t for t in _falhas.get(ip, []) if agora - t < timedelta(minutes=JANELA_MINUTOS)]
    _falhas[ip] = registros
    return len(registros) >= MAX_FALHAS


def registrar_falha(ip: str):
    _falhas.setdefault(ip, []).append(datetime.now())


def limpar_falhas(ip: str):
    _falhas.pop(ip, None)


def current_user(request: Request) -> Optional[dict]:
    """Usuario logado na sessao (cookie assinado) ou None."""
    data = request.session.get("user")
    if not data:
        return None
    return {"id": data.get("id"), "username": data.get("username"),
            "nome": data.get("nome"), "papel": data.get("papel"),
            "must_change": bool(data.get("must_change"))}


def set_user(request: Request, user):
    request.session["user"] = {"id": user["id"], "username": user["username"],
                               "nome": user["nome"], "papel": user["papel"],
                               "must_change": bool(user["must_change"])}


def logout_user(request: Request):
    request.session.pop("user", None)


def require_user(request: Request) -> dict:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_permission(modulo: str):
    """Dependencia FastAPI: exige login + papel com acesso ao modulo.

    Com troca de senha obrigatoria pendente, so libera /troca-senha.
    """
    def _dep(request: Request) -> dict:
        user = current_user(request)
        if user is None:
            raise HTTPException(status_code=303, headers={"Location": "/login"})
        if user["must_change"]:
            raise HTTPException(status_code=303, headers={"Location": "/troca-senha"})
        if not pode(user["papel"], modulo):
            raise HTTPException(status_code=303, headers={"Location": "/?erro=sem-permissao"})
        return user
    return Depends(_dep)
