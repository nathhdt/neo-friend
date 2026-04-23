from datetime import datetime
from utils.colors import CYAN, RESET


def technical_log(module, message):
    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    print(f"{CYAN}{now} - [{module}] {message}{RESET}")

def flow_log(message):
    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    print(f"{now} - {message}{RESET}")