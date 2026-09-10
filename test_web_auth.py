"""Testes do Portal Web Fase 1 (auth, permissoes, usuarios, audit).

Standalone: python test_web_auth.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import src.core.history_repo as hr_mod
import src.web.app as app_mod
import src.web.auth as auth_mod
from src.web.app import create_app
from src.web.users_repo import UsersRepository
from fastapi.testclient import TestClient

FALHAS = []


def check(nome, ok):
    FALHAS.append(nome) if not ok else None
    print(f"  [{'OK' if ok else 'FALHOU'}] {nome}")


def main():
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(ignore_cleanup_errors=True) as td:
        tmp = Path(td)
        tmp.mkdir(parents=True, exist_ok=True)
        db = tmp / "test.db"
        secret = tmp / "secret.key"

        # isola arquivos de dados do portal (secret/aviso) no tmp
        app_mod.get_data_dir = lambda: tmp
        # dashboard le o mesmo db temporario
        hr_mod.get_db_path = lambda: str(db)

        app = create_app(db_path=str(db), secret_file=secret)
        client = TestClient(app)

        users = UsersRepository(db_path=str(db))

        print("== Fase 1: auth e usuarios ==")

        # secret criado
        check("secret criado", secret.exists() and len(secret.read_text(encoding="utf-8")) >= 32)

        # admin bootstrapado com troca obrigatoria
        admin = users.get_by_username("admin")
        check("admin bootstrapado", admin is not None and admin["papel"] == "admin")
        check("admin must_change=1", admin is not None and admin["must_change"] == 1)

        # sem login: / redireciona para /login
        r = client.get("/", follow_redirects=False)
        check("/ sem login -> 303 /login", r.status_code == 303 and r.headers["location"] == "/login")

        r = client.get("/login")
        check("login form 200", r.status_code == 200 and ("login" in r.text.lower()))

        # login errado
        r = client.post("/login", data={"username": "admin", "password": "errada"},
                        follow_redirects=False)
        check("login errado -> 200 com erro", r.status_code == 200 and "inv" in r.text.lower())
        check("audit login-falha", any(a["acao"] == "login-falha" for a in users.audit_list(50)))

        # senha provisoria conhecida: reseta o admin (must_change volta a 1)
        prov = users.reset_password(admin["id"])
        check("senha provisoria gerada", bool(prov) and "-" in prov)

        # login correto com must_change -> /troca-senha
        r = client.post("/login", data={"username": "admin", "password": prov},
                        follow_redirects=False)
        check("login ok -> 303 /troca-senha",
              r.status_code == 303 and r.headers["location"] == "/troca-senha")
        r = client.get("/troca-senha")
        check("troca-senha form 200", r.status_code == 200 and "senha" in r.text.lower())

        # com must_change, / continua bloqueado
        r = client.get("/", follow_redirects=False)
        check("/ com must_change -> 303 /troca-senha",
              r.status_code == 303 and "/troca-senha" in r.headers["location"])

        # troca: atual errada
        r = client.post("/troca-senha", data={"atual": "errada", "nova": "novasenha1",
                                              "confirma": "novasenha1"})
        check("troca com atual errada bloqueia", "incorreta" in r.text)
        # troca: nova curta
        r = client.post("/troca-senha", data={"atual": prov, "nova": "123",
                                              "confirma": "123"})
        check("troca com nova curta bloqueia", "6 caracteres" in r.text)
        # troca: confirmacao difere
        r = client.post("/troca-senha", data={"atual": prov, "nova": "novasenha1",
                                              "confirma": "diferente"})
        check("troca com confirmacao diferente bloqueia", "confere" in r.text or "diferente" in r.text.lower() or "não confere" in r.text)
        # troca ok
        r = client.post("/troca-senha", data={"atual": prov, "nova": "novasenha1",
                                              "confirma": "novasenha1"},
                        follow_redirects=False)
        check("troca ok -> 303 /", r.status_code == 303 and r.headers["location"] == "/")
        check("must_change limpo", users.get_by_id(admin["id"])["must_change"] == 0)

        # dashboard acessivel
        r = client.get("/")
        check("dashboard 200", r.status_code == 200 and "Certificados emitidos" in r.text)
        check("audit troca-senha", any(a["acao"] == "troca-senha" for a in users.audit_list(50)))

        # criar usuario emissor (senha gerada, must_change)
        r = client.post("/usuarios/criar", data={"username": "Carlos", "nome": "Carlos Emissor",
                                                 "papel": "emissor"}, follow_redirects=False)
        check("criar usuario 303", r.status_code == 303)
        carlos = users.get_by_username("carlos")
        check("usuario criado lower/must_change",
              carlos is not None and carlos["must_change"] == 1 and carlos["papel"] == "emissor")

        # duplicado rejeitado
        client.post("/usuarios/criar", data={"username": "carlos", "nome": "X", "papel": "emissor"})
        total_carlos = [u for u in users.list_users() if u["username"] == "carlos"]
        check("duplicado rejeitado", len(total_carlos) == 1)

        # papel invalido rejeitado
        r = client.post("/usuarios/criar", data={"username": "mau", "nome": "M", "papel": "chefe"})
        check("papel invalido rejeitado", users.get_by_username("mau") is None)

        # consulta: login e bloqueio de /usuarios
        cid, prov_c = users.create_user("maria", "Maria Consulta", "consulta")
        users.change_password(cid, "senha123")
        client.get("/logout")
        r = client.post("/login", data={"username": "maria", "password": "senha123"},
                        follow_redirects=False)
        check("consulta login -> 303 /", r.status_code == 303 and r.headers["location"] == "/")
        r = client.get("/usuarios", follow_redirects=False)
        check("consulta nao ve /usuarios (303)",
              r.status_code == 303 and "sem-permissao" in r.headers["location"])
        r = client.get("/")
        check("consulta ve dashboard", r.status_code == 200)

        # bloquear a si mesmo bloqueado
        client.get("/logout")
        client.post("/login", data={"username": "admin", "password": "novasenha1"})
        r = client.post(f"/usuarios/{admin['id']}/bloquear", follow_redirects=False)
        check("bloquear a si bloqueado", users.get_by_id(admin["id"])["ativo"] == 1)

        # bloquear consulta ok -> nao loga
        r = client.post(f"/usuarios/{cid}/bloquear", follow_redirects=False)
        check("bloquear consulta 303", r.status_code == 303)
        check("consulta bloqueada nao loga",
              users.verify_login("maria", "senha123") is None)

        # ultimo admin protegido: cria 2o admin, bloqueia 1, tenta bloquear o ultimo
        a2, _ = users.create_user("admin2", "Admin Dois", "admin")
        users.change_password(a2, "senha999")
        client.post(f"/usuarios/{admin['id']}/reset")
        prov2 = None
        # obtem a provisoria do admin via reset direto no repo (o flash nao e legivel)
        prov2 = users.reset_password(admin["id"])
        users.change_password(admin["id"], "senhadoadmin")
        client.post(f"/usuarios/{a2}/bloquear", follow_redirects=False)
        r = client.post(f"/usuarios/{admin['id']}/bloquear", follow_redirects=False)
        check("ultimo admin protegido", users.get_by_id(admin["id"])["ativo"] == 1)

        # reativar a consulta e conferir que volta a logar
        client.post(f"/usuarios/{cid}/ativar", follow_redirects=False)
        check("consulta reativada loga", users.verify_login("maria", "senha123") is not None)

        # reset: senha antiga deixa de valer
        client.post(f"/usuarios/{cid}/reset")
        maria = users.get_by_id(cid)
        check("reset maria must_change=1", maria["must_change"] == 1)
        check("senha antiga invalida apos reset",
              users.verify_login("maria", "senha123") is None)
        client.post("/usuarios/criar", data={"username": "lixo", "nome": "x", "papel": "consulta"})
        lixo = users.get_by_username("lixo")
        client.post(f"/usuarios/{lixo['id']}/reset")
        check("reset gera provisoria", users.get_by_id(lixo["id"])["must_change"] == 1)

        # rate limit: 5 falhas -> 6a bloqueada
        client.get("/logout")
        auth_mod.limpar_falhas("testclient")
        bloqueado = False
        for i in range(6):
            r = client.post("/login", data={"username": "admin", "password": "errada" + str(i)})
            if "muitas tentativas" in r.text.lower():
                bloqueado = True
                break
        check("rate limit apos 5 falhas", bloqueado)
        check("audit login-bloqueado", any(a["acao"] == "login-bloqueado" for a in users.audit_list(100)))
        auth_mod.limpar_falhas("testclient")

        # audit resumo
        acoes = {a["acao"] for a in users.audit_list(100)}
        esperados = {"login-ok", "login-falha", "logout", "criar-usuario",
                     "bloquear-usuario", "ativar-usuario", "reset-senha",
                     "troca-senha", "bootstrap-admin"}
        check("audit cobre acoes principais", esperados.issubset(acoes))

        print()
        if FALHAS:
            print(f"FALHAS ({len(FALHAS)}): " + ", ".join(FALHAS))
            return 1
        print(f"Todos os {29} checks do portal passaram.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
