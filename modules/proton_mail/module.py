from core.module_base import ModuleBase, ModuleResponse
from typing import Dict, Any, Optional, Union
from utils.logging import technical_log
import imaplib
import email
from email.header import decode_header
import yaml
from pathlib import Path


class ProtonMailModule(ModuleBase):
    """Module pour gérer ProtonMail via Proton Bridge"""
    
    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self.imap = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la config du module"""
        config_path = Path("modules/proton_mail/config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}
    
    def _connect_imap(self):
        """Connexion IMAP à Proton Bridge"""
        if self.imap:
            return
        
        try:
            bridge = self.config.get("proton_bridge", {})
            self.imap = imaplib.IMAP4(
                bridge.get("host", "127.0.0.1"),
                bridge.get("imap_port", 1143)
            )
            self.imap.login(
                bridge.get("username"),
                bridge.get("password")
            )
            technical_log("proton-mail", "IMAP connected")
        except Exception as e:
            technical_log("proton-mail", f"IMAP connection failed: {e}")
            self.imap = None
    
    def get_patterns(self) -> Dict[str, list]:
        return {
            'patterns': [
                r'\b(combien|nombre) (de |d\' |)mails? (non lus?|new)\b',
                r'\b(lis|lire|affiche|montre) (mes |les |)mails?\b',
                r'\bcheck (mes |)mails?\b',
                r'\b(titre|sujet)s? (des |de mes |)mails?\b',
            ],
            'priority': 10
        }
    
    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[Union[str, ModuleResponse]]:
        """Gère les requêtes mail"""
        self._connect_imap()
        
        if not self.imap:
            return "Impossible de se connecter à ProtonMail. Vérifie que Proton Bridge est lancé."
        
        normalized = user_input.lower()
        
        if any(word in normalized for word in ['combien', 'nombre']):
            return await self._count_unread()
        
        elif any(word in normalized for word in ['titre', 'sujet']):
            return await self._list_unread_titles()
        
        elif any(word in normalized for word in ['lis', 'lire', 'affiche', 'check']):
            return await self._read_unread_mails(context)
        
        return None
    
    async def _count_unread(self) -> str:
        """Compte les mails non lus"""
        try:
            self.imap.select("INBOX")
            status, messages = self.imap.search(None, "UNSEEN")
            
            if status == "OK":
                mail_ids = messages[0].split()
                count = len(mail_ids)
                
                if count == 0:
                    return "Tu n'as aucun mail non lu."
                elif count == 1:
                    return "Tu as 1 mail non lu."
                else:
                    return f"Tu as {count} mails non lus."
        except Exception as e:
            technical_log("proton-mail", f"count error: {e}")
            return "Erreur lors de la récupération des mails."
    
    async def _list_unread_titles(self) -> str:
        """Liste les titres des mails non lus"""
        try:
            self.imap.select("INBOX")
            status, messages = self.imap.search(None, "UNSEEN")
            
            if status != "OK":
                return "Erreur lors de la récupération."
            
            mail_ids = messages[0].split()
            
            if not mail_ids:
                return "Aucun mail non lu."
            
            titles = []
            for mail_id in mail_ids[:5]:
                status, msg_data = self.imap.fetch(mail_id, "(RFC822.HEADER)")
                if status == "OK":
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject = self._decode_header(msg.get("Subject", "Sans titre"))
                    sender = self._decode_header(msg.get("From", "Inconnu"))
                    titles.append(f"• {subject} (de {sender})")
            
            response = f"Mails non lus ({len(mail_ids)}):\n" + "\n".join(titles)
            if len(mail_ids) > 5:
                response += f"\n... et {len(mail_ids) - 5} autres."
            
            return response
        
        except Exception as e:
            technical_log("proton-mail", f"list error: {e}")
            return "Erreur lors de la récupération."
    
    async def _read_unread_mails(self, context: Dict[str, Any]) -> ModuleResponse:
        """Lit les mails et retourne des données pour le LLM"""
        try:
            self.imap.select("INBOX")
            status, messages = self.imap.search(None, "UNSEEN")
            
            if status != "OK":
                return "Erreur lors de la récupération."
            
            mail_ids = messages[0].split()
            
            if not mail_ids:
                return "Aucun mail non lu."
            
            mails_data = []
            
            for mail_id in mail_ids[:10]:
                status, msg_data = self.imap.fetch(mail_id, "(RFC822)")
                if status == "OK":
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    subject = self._decode_header(msg.get("Subject", "Sans titre"))
                    sender = self._decode_header(msg.get("From", "Inconnu"))
                    date = msg.get("Date", "")
                    
                    body = self._get_email_body(msg)
                    
                    mails_data.append({
                        "id": mail_id.decode(),
                        "subject": subject,
                        "from": sender,
                        "date": date,
                        "body": body[:500]
                    })
            
            return ModuleResponse(
                response_type="data",
                content=mails_data,
                metadata={
                    "total_unread": len(mail_ids),
                    "fetched": len(mails_data)
                }
            )
        
        except Exception as e:
            technical_log("proton-mail", f"read error: {e}")
            return "Erreur lors de la lecture."
    
    def _decode_header(self, header: str) -> str:
        """Décode un header email"""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = []
        
        for content, encoding in decoded_parts:
            if isinstance(content, bytes):
                result.append(content.decode(encoding or 'utf-8', errors='ignore'))
            else:
                result.append(content)
        
        return " ".join(result)
    
    def _get_email_body(self, msg) -> str:
        """Extrait le body d'un email"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:  # noqa: E722
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:  # noqa: E722
                body = ""
        
        return body.strip()
    
    def on_load(self):
        technical_log("proton-mail", "module loaded")
        
        if not self.config.get("proton_bridge", {}).get("username"):
            technical_log("proton-mail", "WARNING: config not set, edit modules/proton_mail/config.yaml")
    
    def on_unload(self):
        if self.imap:
            try:
                self.imap.logout()
            except:  # noqa: E722
                pass