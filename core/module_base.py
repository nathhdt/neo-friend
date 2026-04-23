from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union


class ModuleResponse:
    """Réponse structurée d'un module"""
    
    def __init__(self, response_type: str, content: Any, metadata: Dict[str, Any] = None):
        self.type = response_type
        self.content = content
        self.metadata = metadata or {}


class ModuleBase(ABC):
    """Classe de base pour tous les modules Neo"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.enabled = True
    
    @abstractmethod
    def get_patterns(self) -> Dict[str, list]:
        """
        Retourne les patterns regex que ce module peut gérer
        
        Returns:
            Dict avec clés: 'patterns' (list de regex), 'priority' (int, optionnel)
        """
        pass
    
    @abstractmethod
    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[Union[str, ModuleResponse]]:
        """
        Gère la requête de l'utilisateur
        
        Args:
            user_input: Ce que l'user a dit
            context: Contexte (tts, stt, config, etc.)
        
        Returns:
            - str: Réponse directe (affichée sans passer par le LLM)
            - ModuleResponse: Données structurées (passées au LLM pour orchestration)
            - None: Le module ne peut pas gérer
        """
        pass
    
    def on_load(self):
        """Appelé quand le module est chargé (optionnel)"""
        pass
    
    def on_unload(self):
        """Appelé quand le module est déchargé (optionnel)"""
        pass