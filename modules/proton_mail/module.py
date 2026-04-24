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
        print("[proton] config loaded:", self.config)
        self.client = IMAPClient(self.config)

    def get_patterns(self) -> Dict[str, list]:
        return PATTERNS

    def _load_config(self) -> Dict[str, Any]:
        path = Path("modules/proton_mail/config.yaml")
        print("[proton] loading config from:", path)
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                print("[proton] config content:", data)
                return data
        print("[proton] config not found")
        return {}

    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[Union[str, ModuleResponse]]:
        print("[proton] handle input:", user_input)

        imap = self.client.connect()
        print("[proton] imap instance:", imap)

        if not imap:
            print("[proton] imap connection failed")
            return "Impossible de me connecter à ProtonMail."

        normalized = user_input.lower()
        print("[proton] normalized:", normalized)

        if any(w in normalized for w in ['combien', 'nombre', 'quantite']):
            print("[proton] intent: count")
            return await self._count_unread(imap)

        if any(p in normalized for p in ['titre', 'sujet', 'quoi', 'quels']):
            print("[proton] intent: list")
            return await self._list_titles(imap)

        if any(w in normalized for w in ['lis', 'lire', 'affiche', 'check', 'regarde']):
            print("[proton] intent: read")
            return await self._read_mails(imap)

        print("[proton] no intent matched")
        return None

    async def _count_unread(self, imap):
        try:
            print("[proton] selecting inbox")
            status, _ = imap.select("INBOX")
            print("[proton] select status:", status)

            status, messages = imap.search(None, "UNSEEN")
            print("[proton] search status:", status)
            print("[proton] raw messages:", messages)

            count = len(messages[0].split())
            print("[proton] unread count:", count)

            if count == 0:
                return "T'as aucun mail non lu."
            if count == 1:
                return "T'as 1 mail non lu."
            return f"T'as {count} mails non lus."
        except Exception as e:
            print("[proton] count error:", e)
            return "Erreur."

    async def _list_titles(self, imap):
        try:
            print("[proton] selecting inbox (list)")
            status, _ = imap.select("INBOX")
            print("[proton] select status:", status)

            status, messages = imap.search(None, "UNSEEN")
            print("[proton] search status:", status)
            print("[proton] raw messages:", messages)

            ids = messages[0].split()
            print("[proton] mail ids:", ids)

            if not ids:
                print("[proton] no unread mails")
                return "Aucun mail non lu."

            titles = []

            for mail_id in ids[:5]:
                print("[proton] fetching header for:", mail_id)
                status, data = imap.fetch(mail_id, "(RFC822.HEADER)")
                print("[proton] fetch status:", status)

                msg = email.message_from_bytes(data[0][1])

                raw_subject = msg.get("Subject")
                raw_from = msg.get("From")
                print("[proton] raw subject:", raw_subject)
                print("[proton] raw from:", raw_from)

                subject = clean_subject(decode_header_value(raw_subject))
                sender = format_sender(decode_header_value(raw_from))

                print("[proton] parsed subject:", subject)
                print("[proton] parsed sender:", sender)

                titles.append(f"{subject}, {sender}.")

            result = "\n".join(titles)
            print("[proton] final titles:", result)

            return result

        except Exception as e:
            print("[proton] list error:", e)
            return "Erreur."

    async def _read_mails(self, imap):
        try:
            print("[proton] selecting inbox (read)")
            status, _ = imap.select("INBOX")
            print("[proton] select status:", status)

            status, messages = imap.search(None, "UNSEEN")
            print("[proton] search status:", status)
            print("[proton] raw messages:", messages)

            ids = messages[0].split()
            print("[proton] mail ids:", ids)

            if not ids:
                print("[proton] no unread mails")
                return "Aucun mail non lu."

            mails = []

            for mail_id in ids[:10]:
                print("[proton] fetching full mail:", mail_id)
                status, data = imap.fetch(mail_id, "(BODY.PEEK[])")
                print("[proton] fetch status:", status)

                msg = email.message_from_bytes(data[0][1])

                subject_raw = msg.get("Subject")
                from_raw = msg.get("From")
                date_raw = msg.get("Date")

                print("[proton] subject raw:", subject_raw)
                print("[proton] from raw:", from_raw)
                print("[proton] date raw:", date_raw)

                subject = clean_subject(decode_header_value(subject_raw))
                sender = decode_header_value(from_raw)
                body = get_email_body(msg)

                print("[proton] subject parsed:", subject)
                print("[proton] sender parsed:", sender)
                print("[proton] body length:", len(body))

                mails.append({
                    "id": mail_id.decode(),
                    "subject": subject,
                    "from": sender,
                    "date": date_raw,
                    "relative_date": format_relative_date(date_raw),
                    "body": body[:500]
                })

            print("[proton] mails collected:", len(mails))

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
            print("[proton] read error:", e)
            return "Erreur."

    def on_load(self):
        technical_log("proton-mail", "module loaded")