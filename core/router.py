import re
import unicodedata
import importlib
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from core.module_base import ModuleBase
from utils.logging import technical_log


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
                        
                        technical_log("router", f"loaded module: {module_dir.name}")
                        break
            
            except Exception as e:
                technical_log("router", f"failed to load {module_dir.name}: {e}")
        
        self.modules.sort(
            key=lambda m: m.get_patterns().get('priority', 0),
            reverse=True
        )
        
        technical_log("router", f"loaded {len(self.modules)} modules")
    
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
    
    async def route(self, user_input: str, context: Dict[str, Any]) -> Optional[Union[str, 'ModuleResponse']]:
        """
        Route la requête vers le bon module
        
        Returns:
            - str: Réponse directe
            - ModuleResponse: Données pour le LLM
            - None: Aucun module ne gère
        """
        from core.module_base import ModuleResponse
        
        normalized = self._normalize(user_input)
        
        for module in self.modules:
            patterns_info = module.get_patterns()
            patterns = patterns_info.get('patterns', [])
            
            for pattern in patterns:
                if re.search(pattern, normalized, re.IGNORECASE):
                    response = await module.handle(user_input, context)
                    if response:
                        return response
        
        return None
    
    def get_goodbye_response(self) -> str:
        """Retourne une réponse d'au revoir"""
        return "Ok."