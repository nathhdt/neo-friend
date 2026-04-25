import importlib
import re
import unicodedata

from core.module_base import ModuleBase
from pathlib import Path
from typing import List, Dict, Any
from utils.logging import technical_log, step_start, step_ok, step_error


class Router:
    """Détecte les intentions et route vers les modules appropriés"""
    
    GOODBYE_PATTERNS = [
        r'\b(au revoir|a plus|salut|ciao|bye|a plus tard|bonne (journee|soiree|nuit))\b',
        r'\b(on se voit|on se parle|a bientot|a tout a l\'heure)\b',
        r'\b(merci ca (sera tout|suffit)|c\'est bon|c\'est tout)\b',
    ]
    
    def __init__(self):
        self.goodbye_regex = re.compile(
            '|'.join(self.GOODBYE_PATTERNS),
            re.IGNORECASE
        )
        
        self.modules: List[ModuleBase] = []
        self._load_modules()
    
    def _load_modules(self):
        """Charge tous les modules depuis le dossier modules/"""
        modules_path = Path("modules")
        
        if not modules_path.exists():
            technical_log("router", "no modules directory found")
            return
        
        step_start("router", "loading modules")

        loaded_count = 0

        for module_dir in modules_path.iterdir():
            if not module_dir.is_dir() or module_dir.name.startswith('_'):
                continue
            
            module_file = module_dir / "module.py"
            if not module_file.exists():
                continue
            
            try:
                spec = importlib.util.spec_from_file_location(
                    f"modules.{module_dir.name}.module",
                    module_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, ModuleBase) and 
                        attr is not ModuleBase):
                        
                        instance = attr()
                        instance.on_load()
                        self.modules.append(instance)

                        step_ok("router", f"module {module_dir.name} loaded")
                        loaded_count += 1
                        
                        break
            
            except Exception as e:
                step_error("router", f"module {module_dir.name} failed: {e}")

        self.modules.sort(
            key=lambda m: m.get_patterns().get('priority', 0),
            reverse=True
        )

        step_ok("router", f"loaded {loaded_count} modules")
    
    def get_all_tools(self) -> List:
        """Collecte tous les LangChain Tools de tous les modules chargés"""
        tools = []
        for module in self.modules:
            module_tools = module.get_tools()
            tools.extend(module_tools)
        return tools

    def _normalize(self, text: str) -> str:
        """Normalise le texte : minuscules + retire accents"""
        text = text.lower()
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
        return text
    
    def detect_goodbye(self, text: str) -> bool:
        """Retourne True si l'user dit au revoir"""
        normalized = self._normalize(text)
        return bool(self.goodbye_regex.search(normalized))
    
    async def route(self, user_input: str, context: Dict[str, Any]):
        normalized = self._normalize(user_input)

        best = None

        for module in self.modules:
            patterns_info = module.get_patterns()
            base_priority = patterns_info.get('priority', 0)

            for item in patterns_info.get("patterns", []):
                intent = item.get("intent")
                score = 0

                for pattern in item.get("patterns", []):
                    if re.search(pattern, normalized):
                        score += 1

                if score > 0:
                    total_score = score + base_priority

                    if not best or total_score > best["score"]:
                        best = {
                            "module": module,
                            "intent": intent,
                            "score": total_score
                        }

        if not best:
            return None

        return await best["module"].handle(user_input, {
            **context,
            "intent": best["intent"]
        })
    
    def get_goodbye_response(self) -> str:
        """Retourne une réponse d'au revoir"""
        return "À plu tard."