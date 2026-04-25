import email
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union

from core.module_base import ModuleBase, ModuleResponse
from utils.logging import technical_log

from .call_patterns import PATTERNS
from .imap_client import IMAPClient
from .formatters import clean_subject, format_sender, format_relative_date
from .parser import decode_header_value, get_email_body


class ProtonMailModule(ModuleBase):

    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self.client = IMAPClient(self.config)

    def get_patterns(self) -> Dict[str, list]:
        return {"patterns": PATTERNS, "priority": 10}

    def _load_config(self) -> Dict[str, Any]:
        path = Path("modules/proton_mail/config.yaml")
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                return data
        
        return {}

    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[Union[str, ModuleResponse]]:
        intent = context.get("intent")

        imap = self.client.connect()

        if not imap:
            return "Impossible de me connecter à ProtonMail."

        if intent == "count":
            return await self._count_unread(imap)

        if intent == "list":
            return await self._list_titles(imap)

        if intent == "read":
            return await self._read_mails(imap)
        
        return None

    async def _count_unread(self, imap):
        try:
            status, _ = imap.select("INBOX")

            status, messages = imap.search(None, "UNSEEN")

            count = len(messages[0].split())

            if count == 0:
                return "Tu as aucun mail non lu."
            if count == 1:
                return "Tu as 1 mail non lu."
            return f"Tu as {count} mails non lus."

        except Exception as e:
            return "Erreur."

    async def _list_titles(self, imap):
        try:
            status, _ = imap.select("INBOX")

            status, messages = imap.search(None, "UNSEEN")

            ids = messages[0].split()

            if not ids:
                return "Aucun mail non lu."

            titles = []

            for mail_id in ids[:5]:
                status, data = imap.fetch(mail_id, "(RFC822.HEADER)")

                msg = email.message_from_bytes(data[0][1])

                subject = clean_subject(decode_header_value(msg.get("Subject")))
                sender = format_sender(decode_header_value(msg.get("From")))

                titles.append(f"{subject}, {sender}.")

            result = "\n".join(titles)

            return result

        except Exception as e:
            return "Erreur."

    async def _read_mails(self, imap):
        try:
            status, _ = imap.select("INBOX")

            status, messages = imap.search(None, "UNSEEN")

            ids = messages[0].split()

            if not ids:
                return "Aucun mail non lu."

            mails = []

            for mail_id in ids[:10]:
                status, data = imap.fetch(mail_id, "(BODY.PEEK[])")

                msg = email.message_from_bytes(data[0][1])

                subject = clean_subject(decode_header_value(msg.get("Subject")))
                sender = decode_header_value(msg.get("From"))
                date_raw = msg.get("Date")
                body = get_email_body(msg)

                mails.append({
                    "id": mail_id.decode(),
                    "subject": subject,
                    "from": sender,
                    "date": date_raw,
                    "relative_date": format_relative_date(date_raw),
                    "body": body[:500]
                })

            return ModuleResponse(
                response_type="data",
                content=mails,
                instructions="""
Tu lis des emails pour l'utilisateur.

Ta tâche :
- Résume chaque mail en une phrase courte
- Sois TRÈS concis
- Tutoie l'utilisateur
- Utilise "relative_date"
- Ne dis jamais que tu ne peux pas accéder aux mails

Format :
Mail 1 : ...
Mail 2 : ...
"""
            )

        except Exception as e:
            return "Erreur."

    def on_load(self):
        technical_log("proton-mail", "module loaded")