import Contacts
import jellyfish
import time
import unicodedata

from langchain_core.tools import tool
from typing import List, Dict, Any

from neo.modules.base import ModuleBase
from neo.shared.logging import step_ok, step_error


class ContactsModule(ModuleBase):

    def __init__(self):
        super().__init__()
        self.store = None

    def on_load(self):
        try:
            self.store = Contacts.CNContactStore.alloc().init()

            granted = [False]
            done = [False]

            def handler(result, error):
                granted[0] = result
                done[0] = True

            self.store.requestAccessForEntityType_completionHandler_(
                Contacts.CNEntityTypeContacts,
                handler
            )

            elapsed = 0
            while not done[0] and elapsed < 10:
                time.sleep(0.1)
                elapsed += 0.1

            if not granted[0]:
                step_error("contacts", "access denied — authorize in System Settings → Privacy → Contacts")
                self.store = None
                return

            step_ok("contacts", "ready")

        except ImportError:
            step_error("contacts", "pyobjc-framework-Contacts not installed")
            self.store = None
        except Exception as e:
            step_error("contacts", f"initialization failed: {e}")
            self.store = None

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower()
        text = unicodedata.normalize("NFD", text)
        return "".join(c for c in text if unicodedata.category(c) != "Mn")

    @staticmethod
    def _soundex_token(token: str) -> str:
        try:
            return jellyfish.soundex(token)
        except Exception:
            return token

    @staticmethod
    def _score(query: str, candidate: str) -> float:
        if not candidate.strip():
            return 0.0

        q = ContactsModule._normalize(query)
        c = ContactsModule._normalize(candidate)

        if q == c:
            return 1.0
        if q in c or c in q:
            return 0.95

        q_tokens = q.split()
        c_tokens = c.split()

        q_set = set(q_tokens)
        c_set = set(c_tokens)
        common_text = q_set & c_set
        jaccard = len(common_text) / len(q_set | c_set) if (q_set | c_set) else 0.0

        q_soundex = [ContactsModule._soundex_token(t) for t in q_tokens if len(t) > 1]
        c_soundex = [ContactsModule._soundex_token(t) for t in c_tokens if len(t) > 1]
        c_soundex_set = set(c_soundex)

        phonetic_matches = sum(1 for qs in q_soundex if qs in c_soundex_set)
        phonetic_score = phonetic_matches / len(q_soundex) if q_soundex else 0.0

        return max(jaccard, phonetic_score * 0.9)

    def _find_best_matches(self, query: str, top_k: int = 3, threshold: float = 0.4) -> List[Any]:
        keys = [
            Contacts.CNContactGivenNameKey,
            Contacts.CNContactFamilyNameKey,
            Contacts.CNContactOrganizationNameKey,
            Contacts.CNContactPhoneNumbersKey,
            Contacts.CNContactEmailAddressesKey,
        ]
        fetch_request = Contacts.CNContactFetchRequest.alloc().initWithKeysToFetch_(keys)

        scored = []

        def handler(contact, stop):
            full_name = f"{contact.givenName()} {contact.familyName()}".strip()
            org = str(contact.organizationName() or "")
            name_to_score = full_name or org
            score = self._score(query, name_to_score)
            if score >= threshold:
                scored.append((score, contact))

        self.store.enumerateContactsWithFetchRequest_error_usingBlock_(
            fetch_request, None, handler
        )

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    @staticmethod
    def _format_contact(contact) -> Dict[str, Any]:
        full_name = f"{contact.givenName()} {contact.familyName()}".strip()
        org = str(contact.organizationName() or "")
        phones = [str(p.value().stringValue()) for p in (contact.phoneNumbers() or [])]
        emails = [str(e.value()) for e in (contact.emailAddresses() or [])]
        return {
            "name": full_name or org,
            "organization": org,
            "phones": phones,
            "emails": emails,
        }

    def get_tools(self) -> List:
        module = self

        @tool
        def find_contact(name: str) -> str:
            """Recherche un contact par nom dans les contacts macOS et retourne ses informations complètes (téléphones, emails, organisation). Utilise cet outil quand l'utilisateur cherche les coordonnées de quelqu'un.

            Args:
                name: nom ou prénom du contact à rechercher
            """
            if not module.store:
                return "Contacts non disponibles."
            try:
                contacts = module._find_best_matches(name)
                if not contacts:
                    return f"Aucun contact trouvé pour '{name}'."

                results = []
                for c in contacts:
                    d = module._format_contact(c)
                    parts = [d["name"]]
                    if d["organization"] and d["organization"] != d["name"]:
                        parts.append(f"({d['organization']})")
                    if d["phones"]:
                        parts.append(f"tél : {', '.join(d['phones'])}")
                    if d["emails"]:
                        parts.append(f"email : {', '.join(d['emails'])}")
                    results.append(" — ".join(parts))

                count = len(results)
                intro = f"{count} contact{'s' if count > 1 else ''} trouvé{'s' if count > 1 else ''} :"
                return intro + "\n" + "\n".join(results)

            except Exception as e:
                return f"Erreur: {e}"

        @tool
        def get_contact_phone(name: str) -> str:
            """Retourne le numéro de téléphone d'un contact. Utilise cet outil quand l'utilisateur demande le numéro, veut appeler quelqu'un, ou a besoin du téléphone d'un contact.

            Args:
                name: nom ou prénom du contact
            """
            if not module.store:
                return "Contacts non disponibles."
            try:
                contacts = module._find_best_matches(name, top_k=1)
                if not contacts:
                    return f"Aucun contact trouvé pour '{name}'."

                d = module._format_contact(contacts[0])
                if not d["phones"]:
                    return f"{d['name']} n'a pas de numéro de téléphone enregistré."
                return f"{d['name']} : {', '.join(d['phones'])}"

            except Exception as e:
                return f"Erreur: {e}"

        @tool
        def get_contact_email(name: str) -> str:
            """Retourne l'adresse email d'un contact. Utilise cet outil quand l'utilisateur demande l'email de quelqu'un ou veut envoyer un message.

            Args:
                name: nom ou prénom du contact
            """
            if not module.store:
                return "Contacts non disponibles."
            try:
                contacts = module._find_best_matches(name, top_k=1)
                if not contacts:
                    return f"Aucun contact trouvé pour '{name}'."

                d = module._format_contact(contacts[0])
                if not d["emails"]:
                    return f"{d['name']} n'a pas d'adresse email enregistrée."
                return f"{d['name']} : {', '.join(d['emails'])}"

            except Exception as e:
                return f"Erreur: {e}"

        return [find_contact, get_contact_phone, get_contact_email]
