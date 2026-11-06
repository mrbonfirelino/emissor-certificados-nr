"""Feedbacks dos usuarios (v1.87.0).

Storage em ARQUIVOS (nao usa o banco): um JSON por feedback em
data/feedbacks/, anexos em data/feedbacks/anexos/{id}/.

Estrutura do JSON:
  id, texto, usuario, pagina, data_hora (ISO local), status
  ("aberto"|"arquivado"), motivo_arquivamento, anexos: [nomes]
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.utils.paths import get_data_dir

STATUS_VALIDOS = ("aberto", "arquivado")


def feedbacks_dir() -> Path:
    d = get_data_dir() / "feedbacks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def anexos_dir(feedback_id: str) -> Path:
    d = feedbacks_dir() / "anexos" / feedback_id
    d.mkdir(parents=True, exist_ok=True)
    return d


class FeedbackRepository:
    """CRUD simples sobre arquivos JSON em data/feedbacks/."""

    @staticmethod
    def _arquivo(feedback_id: str) -> Path:
        return feedbacks_dir() / f"{feedback_id}.json"

    @staticmethod
    def _salvar(d: dict):
        f = FeedbackRepository._arquivo(d["id"])
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    def add(self, texto: str, usuario: str, pagina: str = "",
            anexos: Optional[List[tuple]] = None) -> dict:
        """anexos: lista de (bytes, nome_original). Devolve o feedback criado."""
        texto = (texto or "").strip()
        agora = datetime.now()
        feedback_id = f"FB-{agora:%Y%m%d-%H%M%S}"
        n = 1
        while self._arquivo(feedback_id).exists():
            n += 1
            feedback_id = f"FB-{agora:%Y%m%d-%H%M%S}-{n}"
        dados = {
            "id": feedback_id,
            "texto": texto,
            "usuario": (usuario or "").strip(),
            "pagina": (pagina or "").strip(),
            "data_hora": agora.isoformat(timespec="seconds"),
            "status": "aberto",
            "motivo_arquivamento": "",
            "anexos": [],
        }
        for conteudo, nome in (anexos or []):
            nome = Path(nome or "").name.strip()
            if not nome:
                continue
            try:
                (anexos_dir(feedback_id) / nome).write_bytes(conteudo)
                dados["anexos"].append(nome)
            except Exception:
                pass
        self._salvar(dados)
        return dados

    def get(self, feedback_id: str) -> Optional[dict]:
        f = self._arquivo(feedback_id)
        if not f.exists():
            return None
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None

    def list(self, arquivado: str = "nao", busca: str = "") -> List[dict]:
        itens = []
        for f in sorted(feedbacks_dir().glob("*.json"), reverse=True):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if arquivado == "sim" and d.get("status") != "arquivado":
                continue
            if arquivado != "sim" and arquivado != "todos" \
                    and d.get("status") != "aberto":
                continue
            itens.append(d)
        if arquivado == "todos":
            itens.sort(key=lambda x: x.get("data_hora", ""), reverse=True)
        q = (busca or "").strip().lower()
        if q:
            itens = [d for d in itens
                     if q in (d.get("texto") or "").lower()
                     or q in (d.get("usuario") or "").lower()
                     or q in (d.get("pagina") or "").lower()
                     or q in (d.get("id") or "").lower()]
        return itens

    def arquivar(self, feedback_id: str, motivo: str) -> Optional[dict]:
        d = self.get(feedback_id)
        if d is None:
            return None
        d["status"] = "arquivado"
        d["motivo_arquivamento"] = (motivo or "").strip()
        d["arquivado_em"] = datetime.now().isoformat(timespec="seconds")
        self._salvar(d)
        return d

    def contagem_abertos(self) -> int:
        return sum(1 for d in self.list(arquivado="nao"))

    def caminho_anexo(self, feedback_id: str, nome: str) -> Optional[Path]:
        """Caminho seguro do anexo (sem traversal de pasta)."""
        nome = Path(nome or "").name
        if not nome:
            return None
        d = self.get(feedback_id)
        if d is None or nome not in (d.get("anexos") or []):
            return None
        p = anexos_dir(feedback_id) / nome
        return p if p.exists() else None
