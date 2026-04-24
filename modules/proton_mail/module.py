import imaplib
import email
import yaml
from core.module_base import ModuleBase, ModuleResponse
from datetime import datetime
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
from utils.logging import technical_log


from .call_patterns import PATTERNS


class ProtonMailModule(ModuleBase):
    
    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self.imap = None
    
    def _load_config(self) -> Dict[str, Any]:
        config_path = Path("modules/proton_mail/config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}
    
    def _connect_imap(self):
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
        return PATTERNS
    
    def _clean_subject(self, subject: str) -> str:
        prefixes = ['Re:', 'RE:', 'Fwd:', 'FW:', 'Fw:', 'TR:', 'Re :', 'Fwd :']
        for prefix in prefixes:
            subject = subject.replace(prefix, '').strip()
        return subject
    
    def _format_sender(self, sender: str) -> str:
        name, email_addr = parseaddr(sender)
        
        if name and name.strip():
            name = name.strip('"').strip("'")
            return f"de {name}"
        
        if email_addr and '@' in email_addr:
            domain = email_addr.split('@')[1]
            parts = domain.split('.')
            
            if len(parts) > 1:
                domain_name = '.'.join(parts[:-1])
            else:
                domain_name = domain
            
            return f"depuis {domain_name}"
        
        return "de expéditeur inconnu"
    
    def _format_relative_date(self, date_str: str) -> str:
        try:
            mail_date = parsedate_to_datetime(date_str)
            now = datetime.now(mail_date.tzinfo)
            
            delta = now - mail_date
            days = delta.days
            
            if days == 0:
                return "aujourd'hui"
            elif days == 1:
                return "hier"
            elif days == 2:
                return "avant-hier"
            elif days < 7:
                return f"il y a {days} jours"
            elif days < 14:
                return "il y a plus d'une semaine"
            elif days < 21:
                return "il y a environ 2 semaines"
            elif days < 30:
                return "il y a environ 3 semaines"
            elif days < 60:
                return "il y a environ un mois"
            else:
                months = days // 30
                return f"il y a environ {months} mois"
        except:  # noqa: E722
            return "récemment"
    
    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[Union[str, ModuleResponse]]:
        self._connect_imap()
        
        if not self.imap:
            return "Impossible de me connecter à ProtonMail. Vérifie que Proton Bridge tourne."
        
        normalized = user_input.lower()
        
        if any(word in normalized for word in ['combien', 'nombre', 'quantite']):
            return await self._count_unread()
        
        if any(phrase in normalized for phrase in ['titre', 'sujet', 'c\'est quoi', 'cest quoi', 'quoi comme', 'quels sont', 'lesquels', 'y a quoi']):
            return await self._list_unread_titles()
        
        if any(word in normalized for word in ['lis', 'lire', 'affiche', 'check', 'regarde', 'consulte', 'ouvre', 'verifie']):
            return await self._read_unread_mails(context)
        
        return None
    
    async def _count_unread(self) -> str:
        try:
            self.imap.select("INBOX")
            status, messages = self.imap.search(None, "UNSEEN")
            
            if status == "OK":
                mail_ids = messages[0].split()
                count = len(mail_ids)
                
                if count == 0:
                    return "T'as aucun mail non lu."
                elif count == 1:
                    return "T'as 1 mail non lu."
                else:
                    return f"T'as {count} mails non lus."
        except Exception as e:
            technical_log("proton-mail", f"count error: {e}")
            return "Erreur lors de la récup des mails."
    
    async def _list_unread_titles(self) -> str:
        try:
            self.imap.select("INBOX")
            status, messages = self.imap.search(None, "UNSEEN")
            
            if status != "OK":
                return "Erreur lors de la récupération."
            
            mail_ids = messages[0].split()
            
            if not mail_ids:
                return "Aucun mail non lu."
            
            count = len(mail_ids)
            if count == 1:
                intro = "T'as 1 mail non lu:"
            else:
                intro = f"T'as {count} mails non lus:"
            
            titles = [intro]
            
            for mail_id in mail_ids[:5]:
                status, msg_data = self.imap.fetch(mail_id, "(RFC822.HEADER)")
                if status == "OK":
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    subject = self._decode_header(msg.get("Subject", "Sans titre"))
                    subject = self._clean_subject(subject)
                    
                    sender = self._decode_header(msg.get("From", ""))
                    sender_formatted = self._format_sender(sender)
                    
                    titles.append(f"{subject}, {sender_formatted}.")
            
            if len(mail_ids) > 5:
                titles.append(f"Et {len(mail_ids) - 5} autres mails.")
            
            return "\n".join(titles)
        
        except Exception as e:
            technical_log("proton-mail", f"list error: {e}")
            return "Erreur lors de la récup."
    
    async def _read_unread_mails(self, context: Dict[str, Any]) -> ModuleResponse:
        try:
            self.imap.select("INBOX")
            status, messages = self.imap.search(None, "UNSEEN")
            
            if status != "OK":
                return "Erreur lors de la récup."
            
            mail_ids = messages[0].split()
            
            if not mail_ids:
                return "Aucun mail non lu."
            
            mails_data = []
            
            for mail_id in mail_ids[:10]:
                status, msg_data = self.imap.fetch(mail_id, "(RFC822.PEEK)")
                if status == "OK":
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    subject = self._decode_header(msg.get("Subject", "Sans titre"))
                    subject = self._clean_subject(subject)
                    
                    sender = self._decode_header(msg.get("From", "Inconnu"))
                    date = msg.get("Date", "")
                    
                    body = self._get_email_body(msg)
                    
                    mails_data.append({
                        "id": mail_id.decode(),
                        "subject": subject,
                        "from": sender,
                        "date": date,
                        "relative_date": self._format_relative_date(date),
                        "body": body[:500]
                    })
            
            instructions = """Instructions pour répondre sur les mails :
    - Utilise le champ "relative_date" au lieu de "date" pour indiquer quand les mails ont été envoyés
    - Tutoie l'utilisateur
    - Sois concis et va droit au but
    - Ne répète pas les informations inutilement"""
            
            return ModuleResponse(
                response_type="data",
                content=mails_data,
                metadata={
                    "total_unread": len(mail_ids),
                    "fetched": len(mails_data)
                },
                instructions=instructions
            )
        
        except Exception as e:
            technical_log("proton-mail", f"read error: {e}")
            return "Erreur lors de la lecture."

    def _decode_header(self, header: str) -> str:
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