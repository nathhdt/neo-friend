import email
import yaml

from langchain_core.tools import tool
from pathlib import Path
from typing import Dict, Any, List

from neo.modules.base import ModuleBase
from .imap_client import IMAPClient
from .formatters import clean_subject, format_sender, format_relative_date
from .parser import decode_header_value, get_email_body


class ProtonMailModule(ModuleBase):

    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self.client = IMAPClient(self.config)

    def _load_config(self) -> Dict[str, Any]:
        path = Path(__file__).parent / "config.yaml"
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return {}

    def get_tools(self) -> List:
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
