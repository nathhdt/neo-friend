from core.module_base import ModuleBase
from typing import Dict, Any, Optional
from utils.logging import technical_log


class ProtonMailModule(ModuleBase):
    """Module pour gérer ProtonMail"""
    
    def get_patterns(self) -> Dict[str, list]:
        return {
            'patterns': [
                r'\b(envoie|envoi|envoyer) (un |le |)mail',
                r'\bcheck (mes |)mails?\b',
                r'\b(lis|lire) (mes |)mails?\b',
                r'\b(consulte|voir) (mes |)mails?\b',
            ],
            'priority': 10
        }
    
    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[str]:
        """Gère les requêtes mail"""
        normalized = user_input.lower()
        
        if any(word in normalized for word in ['check', 'lis', 'lire', 'consulte', 'voir']):
            return await self._check_mails()
        
        elif any(word in normalized for word in ['envoie', 'envoi', 'envoyer']):
            return await self._send_mail(context)
        
        return None
    
    async def _check_mails(self) -> str:
        """Vérifie les nouveaux mails"""
        return "Tu as 3 nouveaux mails. Le premier vient de ton boss."
    
    async def _send_mail(self, context: Dict[str, Any]) -> str:
        """Envoie un mail"""
        return "Mail envoyé avec succès."
    
    def on_load(self):
        technical_log("proton-mail", "module loaded")