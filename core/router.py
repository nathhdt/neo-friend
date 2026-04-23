import re
import unicodedata


class Router:
    """Détecte les intentions avant d'appeler le LLM"""
    
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
    
    def get_goodbye_response(self) -> str:
        """Retourne une réponse d'au revoir aléatoire"""
        return "Ok."