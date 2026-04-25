from datetime import datetime
import sys
from utils.colors import CYAN, GREEN, RED, RESET

IS_TTY = sys.stdout.isatty()


def _now():
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")

def technical_log(module, message):
    print(f"{CYAN}{_now()} - [{module}] {message}{RESET}")

def step_start(module, message):
    if IS_TTY:
        sys.stdout.write(f"{CYAN}[{module}] [..] {message}{RESET}")
        sys.stdout.flush()
    else:
        technical_log(module, message)

def step_ok(module, message):
    if IS_TTY:
        sys.stdout.write(f"\r\033[K{CYAN}[{module}] {GREEN}[ok]{CYAN} {message}{RESET}\n")
        sys.stdout.flush()
    else:
        technical_log(module, f"[ok] {message}")

def step_error(module, message):
    if IS_TTY:
        sys.stdout.write(f"\r\033[K{RED}[{module}] error: {message}{RESET}\n")
        sys.stdout.flush()
    else:
        technical_log(module, f"error: {message}")