"""Servidor do Portal Web NormaTech (FastAPI + waitress).

Uso local (testes):   python run_web.py
Servidor definitivo:  python run_web.py --host 0.0.0.0 --port 8000
Resetar senha admin:  python run_web.py --reset-admin
"""

import argparse
import sys


def _resetar_admin() -> int:
    from src.web.users_repo import UsersRepository
    users = UsersRepository()
    admin = users.get_by_username("admin")
    if admin is None:
        senha = users.bootstrap_admin()
        print("Usuario admin criado." if senha else "Falha ao criar admin.")
    else:
        senha = users.reset_password(admin["id"])
        print("Senha do admin resetada." if senha else "Falha ao resetar.")
    if senha:
        print(f"  login: admin    senha provisoria: {senha}")
        print("(troque no primeiro acesso)")
    return 0 if senha else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Portal Web NormaTech")
    parser.add_argument("--host", default="127.0.0.1",
                        help="IP de escuta (0.0.0.0 no servidor)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reset-admin", action="store_true",
                        help="Gera nova senha provisoria para o admin e sai")
    parser.add_argument("--sem-backup", action="store_true",
                        help="Nao inicia o agendador de backup automatico")
    args = parser.parse_args()

    if args.reset_admin:
        return _resetar_admin()

    from src.web.app import create_app
    app = create_app()

    if not args.sem_backup:
        try:
            from src.core.backup_manager import BackupManager
            BackupManager(start_jobs=True)
            print("Backup automatico agendado (portal).")
        except Exception as e:
            print(f"Aviso: backup automatico nao iniciado ({e})")

    import uvicorn
    print(f"Portal NormaTech em http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
