import re


class Router:
    """Détecte les intentions avant d'appeler le LLM"""
    
    GOODBYE_PATTERNS = [
        r'\b(au revoir|à plus|à\+|salut|ciao|bye|a plus tard|bonne (journée|soirée|nuit))\b',
        r'\b(on se voit|on se parle|à bientôt|à tout à l\'heure)\b',
        r'\b(merci ça (sera tout|suffit)|c\'est bon|c\'est tout)\b',
    ]
    
    GOODBYE_RESPONSES = [
        "Ok.",
    ]
    
    def __init__(self):
        self.goodbye_regex = re.compile(
            '|'.join(self.GOODBYE_PATTERNS),
            re.IGNORECASE
        )
    
    def detect_goodbye(self, text: str) -> bool:
        """Retourne True si l'user dit au revoir"""
        return bool(self.goodbye_regex.search(text))
    
    def get_goodbye_response(self) -> str:
        """Retourne une réponse d'au revoir aléatoire"""
        import random
        return random.choice(self.GOODBYE_RESPONSES)