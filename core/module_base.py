from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union, List


class ModuleResponse:
    
    def __init__(self, response_type: str, content: Any, metadata: Dict[str, Any] = None, instructions: str = None):
        self.type = response_type
        self.content = content
        self.metadata = metadata or {}
        self.instructions = instructions or ""


class ModuleBase(ABC):
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.enabled = True
    
    @abstractmethod
    def get_patterns(self) -> Dict[str, list]:
        """Patterns regex pour le router direct (fast-path)"""
        pass
    
    @abstractmethod
    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[Union[str, ModuleResponse]]:
        """Handler pour le router regex"""
        pass
    
    def get_tools(self) -> List:
        """
        Retourne les LangChain Tools exposés par ce module.
        À surcharger dans les modules qui veulent être utilisables par l'agent.
        """
        return []
    
    def on_load(self):
        pass
    
    def on_unload(self):
        pass