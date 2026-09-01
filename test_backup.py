"""
Testes do BackupManager: snapshot consistente com WAL, retencao separada
de periodicos e backup duplo.

Uso:  python test_backup.py
"""
import gzip
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def test_snapshot_wal():
    """Escreve com WAL ativo e confere que o snapshot contem os dados do -wal."""
    tmp = Path(tempfile.mkdtemp(prefix="test_backup_"))
    db = tmp / "base.db"

    # cria banco e escreve com WAL (mesmo pragma do repos do app)
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.commit()
    conn.execute("INSERT INTO t VALUES ('antes-do-backup')")
    conn.commit()
    # deixa transacao NO WAL sem checkpoint: fecha com wal presente
    wal_size_after = (tmp / "base.db-wal").stat().st_size if (tmp / "base.db-wal").exists() else 0

    from src.core.backup_manager import BackupManager

    bm = BackupManager.__new__(BackupManager)  # sem scheduler (init abriria jobs)
    bm.db_path = db
    bm.backup_dir = tmp / "backups"
    bm.backup_dir.mkdir()

    path = bm.create_backup()
    assert path and path.exists(), "backup nao criado"

    # restaura o gz e confere o dado
    with gzip.open(path, "rb") as f:
        data = f.read()
    restored = tmp / "restored.db"
    restored.write_bytes(data)
    r = sqlite3.connect(restored)
    vals = r.execute("SELECT v FROM t").fetchall()
    r.close()
    assert ("antes-do-backup",) in vals, f"dado perdido! wal={wal_size_after}: {vals}"
    print("[OK] snapshot contem dados do WAL (backup consistente)")


def test_retencao_separada():
    """Periodicos nao eliminam os manuais/semanais (e vice-versa)."""
    tmp = Path(tempfile.mkdtemp(prefix="test_retenc_"))
    from src.core.backup_manager import BackupManager, KEEP_REGULAR, KEEP_PERIODIC

    bm = BackupManager.__new__(BackupManager)
    bm.db_path = tmp / "db.db"
    bm.db_path.write_bytes(b"fake")
    bm.backup_dir = tmp / "backups"
    bm.backup_dir.mkdir()
    # backup duplo desligado p/ teste
    from src.core import app_settings
    orig_load = app_settings.load_app_settings
    app_settings.load_app_settings = lambda: {"notificacoes_ativas": False, "backup_duplo": False,
                                              "backup_intervalo_min": 15}

    try:
        # cria KEEP_REGULAR+5 manuais e KEEP_PERIODIC+5 periodicos
        for i in range(KEEP_REGULAR + 5):
            (bm.backup_dir / f"certificados_manual_20260101_{i:06d}.db.gz").write_bytes(b"x")
        for i in range(KEEP_PERIODIC + 5):
            (bm.backup_dir / f"certificados_periodic_20260101_{i:06d}.db.gz").write_bytes(b"x")
        bm._cleanup_old_backups()
        manuais = list(bm.backup_dir.glob("certificados_manual_*.db.gz"))
        periodicos = list(bm.backup_dir.glob("certificados_periodic_*.db.gz"))
        assert len(manuais) == KEEP_REGULAR, f"manuais: {len(manuais)}"
        assert len(periodicos) == KEEP_PERIODIC, f"periodicos: {len(periodicos)}"
        # os mantidos sao os mais recentes (maior timestamp no nome)
        assert max(p.name for p in manuais) == f"certificados_manual_20260101_{KEEP_REGULAR + 4:06d}.db.gz"
        print(f"[OK] retencao separada: {len(manuais)} manuais + {len(periodicos)} periodicos")
    finally:
        app_settings.load_app_settings = orig_load


def test_backup_duplo():
    """Backup duplo copia para Documents/BackupsNormaTech quando ativado."""
    tmp = Path(tempfile.mkdtemp(prefix="test_duplo_"))
    from src.core.backup_manager import BackupManager
    from src.core import app_settings

    bm = BackupManager.__new__(BackupManager)
    bm.db_path = tmp / "db.db"
    conn = sqlite3.connect(bm.db_path)
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.commit()
    conn.close()
    bm.backup_dir = tmp / "backups"
    bm.backup_dir.mkdir()

    dest = tmp / "Documents" / "BackupsNormaTech"
    orig_load = app_settings.load_app_settings
    orig_home = Path.home

    class FakePath(type(Path("C:/"))):
        @classmethod
        def home(cls):
            return tmp

    try:
        app_settings.load_app_settings = lambda: {"notificacoes_ativas": False, "backup_duplo": True}
        import pathlib
        orig_path_home = pathlib.Path.home
        pathlib.Path.home = staticmethod(lambda: tmp)

        path = bm.create_backup()
        copies = list(dest.glob("*.db.gz"))
        assert path and copies, "copia dupla nao encontrada"
        print(f"[OK] backup duplo em {dest.name}: {copies[0].name}")

        # desligado -> nao copia
        for c in dest.glob("*.db.gz"):
            c.unlink()
        app_settings.load_app_settings = lambda: {"notificacoes_ativas": False, "backup_duplo": False}
        path2 = bm.create_backup()
        assert path2 and not list(dest.glob("*.db.gz")), "copiou com duplo desligado"
        print("[OK] backup duplo respeita o toggle")
    finally:
        app_settings.load_app_settings = orig_load
        import pathlib
        pathlib.Path.home = orig_path_home


def test_periodic_startup_catchup():
    """Sessao curta: backup periodico vencido executa na hora (via meta), e
    nao repete quando o ultimo ainda esta dentro do intervalo."""
    import sqlite3
    from datetime import datetime, timedelta
    from src.core.backup_manager import BackupManager
    from src.core import app_settings

    tmp = Path(tempfile.mkdtemp(prefix="test_catchup_"))
    # banco + meta de backup no mesmo db (mesmo layout do app)
    db = tmp / "db.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE t (v TEXT);
        CREATE TABLE IF NOT EXISTS backup_meta (key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.commit()
    conn.close()

    bm = BackupManager.__new__(BackupManager)
    bm.db_path = db
    bm.backup_dir = tmp / "backups"
    bm.backup_dir.mkdir()

    orig_load = app_settings.load_app_settings
    orig_get_db = None
    import src.core.history_repo as hr
    orig_get_db = hr.get_db_path
    hr.get_db_path = lambda: db  # meta vai para o mesmo banco de teste

    def settings(intervalo):
        return lambda: {"notificacoes_ativas": False, "backup_duplo": False,
                        "backup_intervalo_min": intervalo}

    try:
        app_settings.load_app_settings = settings(15)

        # 1o startup: nunca fez periodico -> faz agora
        bm.periodic_backup()
        files1 = list(bm.backup_dir.glob("certificados_periodic_*.db.gz"))
        assert len(files1) == 1, files1

        # 2a chamada logo em seguida (dentro do intervalo) -> nao repete
        bm.periodic_backup()
        files2 = list(bm.backup_dir.glob("certificados_periodic_*.db.gz"))
        assert len(files2) == 1, files2

        # meta antiga (1h atras, intervalo 15min) -> refaz no "startup"
        import time
        time.sleep(1.1)  # garante timestamp diferente no nome do arquivo
        from src.core.history_repo import HistoryRepository
        hr2 = HistoryRepository(db)
        hr2.set_backup_meta("last_periodic_backup",
                            (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds"))
        bm.periodic_backup()
        files3 = list(bm.backup_dir.glob("certificados_periodic_*.db.gz"))
        assert len(files3) == 2, files3
        print("[OK] catch-up: startup faz backup vencido; nao duplica dentro do intervalo")
    finally:
        app_settings.load_app_settings = orig_load
        hr.get_db_path = orig_get_db


if __name__ == "__main__":
    test_snapshot_wal()
    test_retencao_separada()
    test_backup_duplo()
    test_periodic_startup_catchup()
    print("\nTODOS OS TESTES PASSARAM")
