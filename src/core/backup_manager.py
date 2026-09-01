import gzip
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.utils.paths import get_db_path, get_backup_dir, get_data_dir
from src.core.config import verify_restore_password

KEEP_REGULAR = 12   # backups manuais/semanais mantidos
KEEP_PERIODIC = 32  # backups periodicos mantidos (32 x 15min = 8h de historico)
LOG_FILE = get_data_dir() / "backup.log"


def _log(msg: str):
    """Log simples de backups (data/backup.log) — falhas nao podem ser invisiveis."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
    except Exception:
        pass


class BackupManager:
    """Gerencia backups: semanal (silencioso), periodico (configuravel), manual,
    duplo (copia em Documents) e restauracao com senha.

    Os jobs rodam com next_run_time=agora: no startup cada um avalia seus
    metadados e executa se estiver vencido (sessoes curtas de uso tambem
    recebem backup). O IntervalTrigger mantem a cadencia enquanto o app fica
    aberto."""

    def __init__(self):
        self.db_path = get_db_path()
        self.backup_dir = get_backup_dir()
        self.scheduler = BackgroundScheduler(daemon=True)
        self._start_auto_backup()
        self._start_periodic_backup()

    def _start_auto_backup(self):
        """Backup semanal — avalia (e executa se vencido) ja no startup."""
        try:
            self.scheduler.add_job(
                self.auto_backup_if_needed,
                IntervalTrigger(days=7),
                id='weekly_backup',
                replace_existing=True,
                next_run_time=datetime.now(),
            )
            self.scheduler.start()
        except Exception as e:
            _log(f"ERRO ao iniciar job semanal: {e}")

    def _start_periodic_backup(self):
        """Backup periodico enquanto o app estiver aberto (intervalo configuravel).
        next_run_time=agora: se o ultimo backup periodico passou do intervalo,
        faz imediatamente na abertura do programa."""
        from src.core.app_settings import get_setting

        try:
            intervalo = max(1, int(get_setting("backup_intervalo_min", 15)))
        except Exception:
            intervalo = 15
        try:
            self.scheduler.add_job(
                self.periodic_backup,
                IntervalTrigger(minutes=intervalo),
                id='periodic_backup',
                replace_existing=True,
                next_run_time=datetime.now(),
            )
        except Exception as e:
            _log(f"ERRO ao iniciar job periodico: {e}")

    def reschedule(self):
        """Reaplica o intervalo do backup periodico apos mudanca nas configuracoes."""
        self._start_periodic_backup()

    def auto_backup_if_needed(self):
        """Faz backup automatico se passou mais de 7 dias do ultimo."""
        from src.core.history_repo import HistoryRepository
        history = HistoryRepository()
        last_backup = history.get_backup_meta('last_auto_backup')
        today = datetime.now().date().isoformat()
        if last_backup != today:
            self.create_backup(auto=True)
            history.set_backup_meta('last_auto_backup', today)

    def periodic_backup(self):
        """Backup periodico — executado no startup (se vencido) e a cada intervalo."""
        from src.core.history_repo import HistoryRepository
        from src.core.app_settings import get_setting

        try:
            intervalo = max(1, int(get_setting("backup_intervalo_min", 15)))
        except Exception:
            intervalo = 15
        history = HistoryRepository()
        now = datetime.now()
        last = history.get_backup_meta('last_periodic_backup')
        if last:
            try:
                # ainda dentro do intervalo -> nao repete (evita backup a cada abertura)
                if now - datetime.fromisoformat(last) < timedelta(minutes=intervalo):
                    return
            except ValueError:
                pass
        path = self.create_backup(periodic=True)
        history.set_backup_meta('last_periodic_backup', now.isoformat(timespec='seconds'))
        if not path:
            _log("ERRO backup periodico: create_backup falhou (ver disco/permissao)")

    def _snapshot_db(self, tmp_path: Path) -> bool:
        """
        Snapshot consistente do banco via SQLite backup API.
        Necessario porque o banco roda em WAL: copiar o arquivo .db direto
        pode perder transacoes ainda no -wal.
        """
        src = sqlite3.connect(str(self.db_path))
        try:
            dst = sqlite3.connect(str(tmp_path))
            try:
                dst.execute("PRAGMA journal_mode=DELETE")
                src.backup(dst)
                dst.commit()
            finally:
                dst.close()
        finally:
            src.close()
        return True

    def create_backup(self, auto: bool = False, periodic: bool = False) -> Optional[Path]:
        """Cria backup compactado do banco (.db.gz) com snapshot consistente."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            kind = "periodic" if periodic else ("auto" if auto else "manual")
            backup_name = f"certificados_{kind}_{timestamp}.db.gz"
            backup_path = self.backup_dir / backup_name

            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                self._snapshot_db(tmp_path)
                with open(tmp_path, 'rb') as f_in:
                    with gzip.open(backup_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

            # retencao separada: periodicos x manuais/semanais
            self._cleanup_old_backups()
            # backup duplo (Documents)
            self._copy_dual(backup_path)

            if periodic or auto:
                try:
                    from src.utils.notifications import notify
                    notify("Backup concluido", backup_name)
                except Exception:
                    pass
            _log(f"OK {backup_name}")
            return backup_path
        except Exception as e:
            _log(f"ERRO create_backup: {e}")
            return None

    def _dual_dir(self) -> Optional[Path]:
        """Destino duplo: Documents\\BackupsNormaTech (se ativado)."""
        from src.core.app_settings import get_setting

        try:
            if not get_setting("backup_duplo", True):
                return None
            d = Path.home() / "Documents" / "BackupsNormaTech"
            d.mkdir(parents=True, exist_ok=True)
            return d
        except Exception:
            return None

    def _copy_dual(self, backup_path: Path):
        d = self._dual_dir()
        if not d:
            return
        try:
            shutil.copy2(backup_path, d / backup_path.name)
        except Exception:
            pass

    def _cleanup_old_backups(self, base_dir: Optional[Path] = None):
        """Remove backups antigos. Periodicos e nao-periodicos tem retencao propria."""
        base = base_dir or self.backup_dir
        periodic_files = sorted(base.glob("certificados_periodic_*.db.gz"),
                                key=lambda p: p.name, reverse=True)
        regular_files = sorted(
            [p for p in base.glob("certificados_*.db.gz")
             if not p.name.startswith("certificados_periodic_")],
            key=lambda p: p.name, reverse=True)
        for old in periodic_files[KEEP_PERIODIC:] + regular_files[KEEP_REGULAR:]:
            try:
                old.unlink()
            except Exception:
                pass

    def list_backups(self) -> List[Path]:
        """Lista backups disponiveis (mais recentes primeiro)."""
        return sorted(self.backup_dir.glob("certificados_*.db.gz"),
                      key=lambda p: p.name, reverse=True)

    def restore_backup(self, backup_path: Path, password: str) -> bool:
        """Restaura backup (requer senha)."""
        if not verify_restore_password(password):
            return False
        try:
            # Para restaurar, precisa fechar conexões atuais
            # Faz restore para arquivo temporário e substitui
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                temp_path = Path(tmp.name)

            with gzip.open(backup_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Substitui o banco atual (remove WAL/SHM antigos)
            for suffix in ("-wal", "-shm"):
                side = Path(str(self.db_path) + suffix)
                try:
                    side.unlink(missing_ok=True)
                except Exception:
                    pass
            shutil.move(str(temp_path), str(self.db_path))
            return True
        except Exception:
            return False

    def shutdown(self):
        """Para o agendador (ao fechar app)."""
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            pass
