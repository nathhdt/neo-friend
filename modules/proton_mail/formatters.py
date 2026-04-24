from email.utils import parseaddr, parsedate_to_datetime
from datetime import datetime


def clean_subject(subject: str) -> str:
    prefixes = ['Re:', 'RE:', 'Fwd:', 'FW:', 'Fw:', 'TR:', 'Re :', 'Fwd :']
    for prefix in prefixes:
        subject = subject.replace(prefix, '').strip()
    return subject


def format_sender(sender: str) -> str:
    name, email_addr = parseaddr(sender)

    if name and name.strip():
        clean = name.strip().strip('"').strip("'")
        return f"de {clean}"

    if email_addr and '@' in email_addr:
        domain = email_addr.split('@')[1]
        parts = domain.split('.')
        domain_name = '.'.join(parts[:-1]) if len(parts) > 1 else domain
        return f"de {domain_name}"

    return "expéditeur inconnu"


def format_relative_date(date_str: str) -> str:
    try:
        mail_date = parsedate_to_datetime(date_str)
        now = datetime.now(mail_date.tzinfo)
        delta = now - mail_date
        days = delta.days

        if days == 0:
            return "aujourd'hui"
        if days == 1:
            return "hier"
        if days == 2:
            return "avant-hier"
        if days < 7:
            return f"il y a {days} jours"
        if days < 30:
            return f"il y a environ {days // 7} semaines"
        return f"il y a environ {days // 30} mois"
    except:
        return "récemment"