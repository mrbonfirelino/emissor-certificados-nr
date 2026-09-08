"""
Tarefa agendada do Windows (Task Scheduler) para backup diario headless.

Registra/remove a tarefa 'NormaTechBackup' via schtasks:
    schtasks /Create /F /TN NormaTechBackup /SC DAILY /ST HH:MM \
             /TR "\"...CertificadosNR.exe\" --backup"

No modo dev a tarefa chama 'python src\\main.py --backup'; congelado (exe),
chama o proprio executavel. Runner injetavel para testes.
"""

import re
import subprocess
import sys
from pathlib import Path

TASK_NAME = "NormaTechBackup"
_HORA_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def validar_hora(hora: str) -> bool:
    return bool(_HORA_RE.match((hora or "").strip()))


def _command_action() -> str:
    """String /TR: comando que executa o backup headless."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --backup'
    script = Path(__file__).resolve().parents[2] / "src" / "main.py"
    return f'"{sys.executable}" "{script}" --backup'


def _run(args, runner=None):
    runner = runner or subprocess.run
    return runner(["schtasks", *args], capture_output=True, text=True)


def register(hora: str, runner=None) -> bool:
    """Cria (ou substitui) a tarefa diaria no horario HH:MM."""
    hora = (hora or "12:00").strip()
    if not validar_hora(hora):
        return False
    res = _run(
        ["/Create", "/F", "/TN", TASK_NAME, "/SC", "DAILY",
         "/ST", hora, "/TR", _command_action()],
        runner,
    )
    return res.returncode == 0


def remove(runner=None) -> bool:
    """Remove a tarefa agendada (idempotente)."""
    res = _run(["/Delete", "/F", "/TN", TASK_NAME], runner)
    return res.returncode == 0


def is_active(runner=None) -> bool:
    """True se a tarefa existe no Task Scheduler."""
    res = _run(["/Query", "/TN", TASK_NAME], runner)
    return res.returncode == 0


def status_text() -> str:
    """Texto de status para a UI."""
    if is_active():
        return "Tarefa ativa (backup diário com o programa fechado)"
    return "Tarefa inativa"
