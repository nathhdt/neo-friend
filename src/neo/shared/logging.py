import sys

from datetime import datetime
from neo.shared.colors import BLUE, PINK, RED, RESET

IS_TTY = sys.stdout.isatty()


def _now():
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def technical_log(module, message):
    print(f"{BLUE}{_now()} - [{module}] {message}{RESET}")


def step_start(module, message):
    if IS_TTY:
        sys.stdout.write(f"{BLUE}[{module}] [..] {message}{RESET}")
        sys.stdout.flush()
    else:
        technical_log(module, message)


def step_ok(module, message):
    if IS_TTY:
        sys.stdout.write(f"\r\033[K{BLUE}[{module}] {PINK}[ok]{BLUE} {message}{RESET}\n")
        sys.stdout.flush()
    else:
        technical_log(module, f"[ok] {message}")


def step_error(module, message):
    if IS_TTY:
        sys.stdout.write(f"\r\033[K{RED}[{module}] error: {message}{RESET}\n")
        sys.stdout.flush()
    else:
        technical_log(module, f"error: {message}")
