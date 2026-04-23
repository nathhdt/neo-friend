from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


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
        
        Example:
            {
                'patterns': [
                    r'\b(envoie|envoi) (un |)mail',
                    r'\bcheck (mes |)mails?\b'
                ],
                'priority': 10  # Plus haut = priorité plus haute
            }
        """
        pass
    
    @abstractmethod
    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Gère la requête de l'utilisateur
        
        Args:
            user_input: Ce que l'user a dit
            context: Contexte (tts, stt, config, etc.)
        
        Returns:
            La réponse de Neo (str) ou None si le module ne peut pas gérer
        """
        pass
    
    def on_load(self):
        """Appelé quand le module est chargé (optionnel)"""
        pass
    
    def on_unload(self):
        """Appelé quand le module est déchargé (optionnel)"""
        pass