"""Testes da tarefa agendada do Windows (v1.15.0): schtasks com runner falso.

Rodar: python test_scheduled_task.py
"""

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.core import scheduled_task as st

PASSOS = []


def check(nome, cond):
    PASSOS.append((nome, bool(cond)))
    print(f"[{'OK' if cond else 'FALHOU'}] {nome}")


class FakeRunner:
    """Registra comandos e responde returncode configuravel."""

    def __init__(self, returncode=0):
        self.calls = []
        self.returncode = returncode

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        return SimpleNamespace(returncode=self.returncode,
                               stdout="", stderr="")


def test_validar_hora():
    check("horario valido 12:00", st.validar_hora("12:00"))
    check("horario valido 00:00 e 23:59",
          st.validar_hora("00:00") and st.validar_hora("23:59"))
    check("horario invalido 24:00", not st.validar_hora("24:00"))
    check("horario invalido 12:60", not st.validar_hora("12:60"))
    check("horario invalido 9:5 (formato)", not st.validar_hora("9:5"))
    check("horario invalido vazio/lixo",
          not st.validar_hora("") and not st.validar_hora("meio-dia"))


def test_command_action():
    action = st._command_action()
    check("acao termina com --backup", action.endswith("--backup"))
    check("acao dev aponta python + main.py" if not getattr(sys, "frozen", False)
          else "acao exe aponta executavel",
          ("main.py" in action and sys.executable in action)
          if not getattr(sys, "frozen", False) else sys.executable in action)


def test_register():
    runner = FakeRunner(returncode=0)
    ok = st.register("12:00", runner=runner)
    check("register retorna True", ok)
    check("register chamou schtasks uma vez", len(runner.calls) == 1)
    cmd = runner.calls[0]
    check("comando /Create /F /TN NormaTechBackup",
          cmd[0] == "schtasks" and cmd[1] == "/Create" and "/F" in cmd
          and st.TASK_NAME in cmd)
    check("comando /SC DAILY /ST 12:00",
          "/SC" in cmd and "DAILY" in cmd and "/ST" in cmd and "12:00" in cmd)
    tr = cmd[cmd.index("/TR") + 1]
    check("/TR contem --backup", "--backup" in tr)

    runner2 = FakeRunner(returncode=0)
    check("hora invalida: register False SEM chamar runner",
          st.register("99:99", runner=runner2) is False and runner2.calls == [])

    runner3 = FakeRunner(returncode=1)
    check("schtasks falha (rc=1): register False",
          st.register("08:30", runner=runner3) is False)


def test_remove():
    runner = FakeRunner(returncode=0)
    check("remove retorna True", st.remove(runner=runner))
    cmd = runner.calls[0]
    check("comando /Delete /F /TN",
          cmd[0] == "schtasks" and "/Delete" in cmd and "/F" in cmd
          and st.TASK_NAME in cmd)


def test_is_active():
    r_ok = FakeRunner(returncode=0)
    r_nok = FakeRunner(returncode=1)
    check("is_active True (rc=0)", st.is_active(runner=r_ok))
    check("is_active False (rc=1)", not st.is_active(runner=r_nok))
    check("is_active chamou /Query /TN",
          r_ok.calls[0][1] == "/Query" and st.TASK_NAME in r_ok.calls[0])


def main():
    test_validar_hora()
    test_command_action()
    test_register()
    test_remove()
    test_is_active()

    falhas = [n for n, ok in PASSOS if not ok]
    print(f"\n{len(PASSOS) - len(falhas)}/{len(PASSOS)} testes OK")
    if falhas:
        print("FALHARAM:", falhas)
        sys.exit(1)


if __name__ == "__main__":
    main()
