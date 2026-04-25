import email
import yaml

from core.module_base import ModuleBase, ModuleResponse
from langchain_core.tools import tool
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
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

    def get_tools(self) -> List:
        """Expose les opérations mail comme LangChain Tools"""

        client = self.client

        @tool
        def check_email_count() -> str:
            """Compte le nombre de mails non lus dans la boîte de réception ProtonMail. Utilise cet outil quand l'utilisateur demande combien il a de mails, s'il a de nouveaux messages, ou s'il a reçu du courrier."""
            imap = client.connect()
            if not imap:
                return "Impossible de se connecter à ProtonMail."
            try:
                imap.select("INBOX")
                _, messages = imap.search(None, "UNSEEN")
                count = len(messages[0].split())
                if count == 0:
                    return "Aucun mail non lu."
                if count == 1:
                    return "1 mail non lu."
                return f"{count} mails non lus."
            except Exception:
                return "Erreur lors de la vérification des mails."

        @tool
        def list_email_subjects() -> str:
            """Liste les sujets et expéditeurs des mails non lus (max 5). Utilise cet outil quand l'utilisateur veut connaître les titres, sujets, ou savoir de qui viennent ses mails."""
            imap = client.connect()
            if not imap:
                return "Impossible de se connecter à ProtonMail."
            try:
                imap.select("INBOX")
                _, messages = imap.search(None, "UNSEEN")
                ids = messages[0].split()
                if not ids:
                    return "Aucun mail non lu."

                titles = []
                for mail_id in ids[:5]:
                    _, data = imap.fetch(mail_id, "(RFC822.HEADER)")
                    msg = email.message_from_bytes(data[0][1])
                    subject = clean_subject(decode_header_value(msg.get("Subject")))
                    sender = format_sender(decode_header_value(msg.get("From")))
                    titles.append(f"- {subject}, {sender}")

                return "\n".join(titles)
            except Exception:
                return "Erreur lors de la récupération des sujets."

        @tool
        def read_emails() -> str:
            """Lit le contenu des mails non lus (max 10) avec sujet, expéditeur, date et un extrait du corps. Utilise cet outil quand l'utilisateur veut lire, consulter ou vérifier ses mails en détail."""
            imap = client.connect()
            if not imap:
                return "Impossible de se connecter à ProtonMail."
            try:
                imap.select("INBOX")
                _, messages = imap.search(None, "UNSEEN")
                ids = messages[0].split()
                if not ids:
                    return "Aucun mail non lu."

                results = []
                for mail_id in ids[:10]:
                    _, data = imap.fetch(mail_id, "(BODY.PEEK[])")
                    msg = email.message_from_bytes(data[0][1])

                    subject = clean_subject(decode_header_value(msg.get("Subject")))
                    sender = decode_header_value(msg.get("From"))
                    date_raw = msg.get("Date")
                    body = get_email_body(msg)

                    results.append(
                        f"Sujet: {subject}\n"
                        f"De: {sender}\n"
                        f"Date: {format_relative_date(date_raw)}\n"
                        f"Contenu: {body[:300]}\n"
                    )

                return "\n---\n".join(results)
            except Exception:
                return "Erreur lors de la lecture des mails."

        return [check_email_count, list_email_subjects, read_emails]

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
            imap.select("INBOX")
            _, messages = imap.search(None, "UNSEEN")
            count = len(messages[0].split())
            if count == 0:
                return "Tu as aucun mail non lu."
            if count == 1:
                return "Tu as 1 mail non lu."
            return f"Tu as {count} mails non lus."
        except Exception:
            return "Erreur."

    async def _list_titles(self, imap):
        try:
            imap.select("INBOX")
            _, messages = imap.search(None, "UNSEEN")
            ids = messages[0].split()
            if not ids:
                return "Aucun mail non lu."

            titles = []
            for mail_id in ids[:5]:
                _, data = imap.fetch(mail_id, "(RFC822.HEADER)")
                msg = email.message_from_bytes(data[0][1])
                subject = clean_subject(decode_header_value(msg.get("Subject")))
                sender = format_sender(decode_header_value(msg.get("From")))
                titles.append(f"{subject}, {sender}.")

            return "\n".join(titles)
        except Exception:
            return "Erreur."

    async def _read_mails(self, imap):
        try:
            imap.select("INBOX")
            _, messages = imap.search(None, "UNSEEN")
            ids = messages[0].split()
            if not ids:
                return "Aucun mail non lu."

            mails = []
            for mail_id in ids[:10]:
                _, data = imap.fetch(mail_id, "(BODY.PEEK[])")
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
        except Exception:
            return "Erreur."

    def on_load(self):
        technical_log("proton-mail", "module loaded")