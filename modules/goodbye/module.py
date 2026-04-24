"""
Module de gestion des messages d'adieu.
Déplace cette logique hors du Router.
"""
from core.module_base import ModuleBase
from typing import Dict, Any, Optional
import random


class GoodbyeModule(ModuleBase):
    """Gère les messages d'adieu de l'utilisateur"""
    
    def get_patterns(self) -> Dict[str, list]:
        return {
            'patterns': [
                r'\b(au revoir|a plus|salut|ciao|bye|a plus tard|bonne (journee|soiree|nuit))\b',
                r'\b(on se voit|on se parle|a bientot|a tout a l\'heure)\b',
                r'\b(merci ca (sera tout|suffit)|c\'est bon|c\'est tout)\b',
            ],
            'priority': 100
        }
    
    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[str]:
        """Retourne un message d'adieu"""
        responses = [
            "Ok.",
            "À plus.",
            "Salut.",
        ]
        return random.choice(responses)