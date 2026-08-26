import gzip
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.utils.paths import get_db_path, get_backup_dir, get_data_dir
from src.core.config import verify_restore_password


class BackupManager:
    """Gerencia backups automáticos (semanal) e manuais + restauração com senha."""

    def __init__(self):
        self.db_path = get_db_path()
        self.backup_dir = get_backup_dir()
        self.scheduler = BackgroundScheduler(daemon=True)
        self._start_auto_backup()

    def _start_auto_backup(self):
        """Inicia agendador de backup semanal silencioso."""
        try:
            self.scheduler.add_job(
                self.auto_backup_if_needed,
                IntervalTrigger(days=7),
                id='weekly_backup',
                replace_existing=True
            )
            self.scheduler.start()
        except Exception:
            pass  # Silencioso

    def auto_backup_if_needed(self):
        """Faz backup automático se passou mais de 7 dias do último."""
        from src.core.history_repo import HistoryRepository
        history = HistoryRepository()
        last_backup = history.get_backup_meta('last_auto_backup')
        today = datetime.now().date().isoformat()
        if last_backup != today:
            self.create_backup(auto=True)
            history.set_backup_meta('last_auto_backup', today)

    def create_backup(self, auto: bool = False) -> Optional[Path]:
        """Cria backup compactado do banco (.db.gz)."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "auto" if auto else "manual"
            backup_name = f"certificados_{prefix}_{timestamp}.db.gz"
            backup_path = self.backup_dir / backup_name
            
            with open(self.db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Mantém apenas últimos 12 backups
            self._cleanup_old_backups(keep=12)
            return backup_path
        except Exception:
            return None

    def _cleanup_old_backups(self, keep: int = 12):
        """Remove backups antigos, mantendo os mais recentes."""
        backups = sorted(self.backup_dir.glob("certificados_*.db.gz"), reverse=True)
        for old in backups[keep:]:
            try:
                old.unlink()
            except Exception:
                pass

    def list_backups(self) -> List[Path]:
        """Lista backups disponíveis (mais recentes primeiro)."""
        return sorted(self.backup_dir.glob("certificados_*.db.gz"), reverse=True)

    def restore_backup(self, backup_path: Path, password: str) -> bool:
        """Restaura backup (requer senha)."""
        if not verify_restore_password(password):
            return False
        try:
            # Para restaurar, precisa fechar conexões atuais
            # Faz restore para arquivo temporário e substitui
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                temp_path = Path(tmp.name)
            
            with gzip.open(backup_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Substitui o banco atual
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