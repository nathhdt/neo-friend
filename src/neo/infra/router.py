import importlib
import re
import unicodedata

from pathlib import Path
from typing import List

from neo.modules.base import ModuleBase
from neo.shared.logging import technical_log, step_start, step_ok, step_error


class Router:
    """Charge les modules et collecte leurs tools. Détecte les goodbyes."""

    GOODBYE_PATTERNS = [
        r"\b(au revoir|a plus|salut|ciao|bye|a plus tard|bonne (journee|soiree|nuit))\b",
        r"\b(on se voit|on se parle|a bientot|a tout a l'heure)\b",
        r"\b(merci ca (sera tout|suffit)|c'est bon|c'est tout)\b",
    ]

    def __init__(self):
        self.goodbye_regex = re.compile("|".join(self.GOODBYE_PATTERNS))

        self.modules: List[ModuleBase] = []
        self._load_modules()

    def _load_modules(self):
        """Charge tous les modules depuis le package neo.modules"""
        modules_path = Path(__file__).resolve().parent.parent / "modules"

        if not modules_path.exists():
            technical_log("router", "no modules directory found")
            return

        step_start("router", "loading modules")

        loaded_count = 0

        for module_dir in modules_path.iterdir():
            if not module_dir.is_dir() or module_dir.name.startswith("_"):
                continue

            module_file = module_dir / "module.py"
            if not module_file.exists():
                continue

            try:
                mod = importlib.import_module(f"neo.modules.{module_dir.name}.module")

                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, ModuleBase) and
                        attr is not ModuleBase):

                        instance = attr()
                        instance.on_load()
                        self.modules.append(instance)

                        step_ok("router", f"module loaded: '{module_dir.name}'")
                        loaded_count += 1

                        break

            except Exception as e:
                step_error("router", f"module failed : '{module_dir.name}' ({e})")

        step_ok("router", f"loaded {loaded_count} modules")

    def get_all_tools(self) -> List:
        tools = []
        for module in self.modules:
            tools.extend(module.get_tools())
        return tools

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower()
        text = unicodedata.normalize("NFD", text)
        return "".join(c for c in text if unicodedata.category(c) != "Mn")

    def detect_goodbye(self, text: str) -> bool:
        return bool(self.goodbye_regex.search(self._normalize(text)))

    def get_goodbye_response(self) -> str:
        return "À plu tard."
