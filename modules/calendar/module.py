import yaml

from core.module_base import ModuleBase
from datetime import datetime, timedelta
from langchain_core.tools import tool
from pathlib import Path
from typing import List, Dict, Any
from utils.logging import step_ok, step_error, technical_log


class CalendarModule(ModuleBase):

    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self.calendar_names = self.config.get("calendars", [])
        self.store = None

    def _load_config(self) -> Dict[str, Any]:
        path = Path("modules/calendar/config.yaml")
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return {}

    def on_load(self):
        """Initialise EventKit et demande les permissions d'accès au calendrier."""
        try:
            import EventKit
            self.store = EventKit.EKEventStore.alloc().init()

            # Demande d'autorisation (bloquant jusqu'à réponse de l'OS)
            granted = [False]
            done = [False]

            def handler(result, error):
                granted[0] = result
                done[0] = True

            self.store.requestAccessToEntityType_completion_(
                EventKit.EKEntityTypeEvent,
                handler
            )

            # Attente synchrone de la réponse
            import time
            timeout = 10
            elapsed = 0
            while not done[0] and elapsed < timeout:
                time.sleep(0.1)
                elapsed += 0.1

            if not granted[0]:
                step_error("calendar", "access denied — authorize in System Settings → Privacy → Calendars")
                self.store = None
                return

            step_ok("calendar", f"ready ({len(self.calendar_names)} calendars: {', '.join(self.calendar_names)})")

        except ImportError:
            step_error("calendar", "pyobjc-framework-EventKit not installed — run: pip install pyobjc-framework-EventKit")
            self.store = None
        except Exception as e:
            step_error("calendar", f"initialization failed: {e}")
            self.store = None

    def _get_calendars(self):
        """Retourne les objets EKCalendar filtrés par nom."""
        if not self.store:
            return []
        import EventKit
        all_calendars = self.store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
        return [c for c in all_calendars if c.title() in self.calendar_names]

    def _ekevent_to_dict(self, event) -> Dict[str, Any]:
        """Convertit un EKEvent en dict sérialisable."""
        start = event.startDate()
        end = event.endDate()
        return {
            "title": str(event.title() or "Sans titre"),
            "calendar": str(event.calendar().title()),
            "start": str(start),
            "end": str(end),
            "location": str(event.location() or ""),
            "notes": str(event.notes() or ""),
            "event_id": str(event.eventIdentifier()),
        }

    def _ns_date(self, dt: datetime):
        """Convertit un datetime Python en NSDate."""
        from Foundation import NSDate
        import time
        timestamp = dt.timestamp()
        return NSDate.dateWithTimeIntervalSince1970_(timestamp)

    def get_tools(self) -> List:
        module = self

        @tool
        def list_today_events() -> str:
            """Liste tous les événements du calendrier pour aujourd'hui. Utilise cet outil quand l'utilisateur demande ce qu'il a aujourd'hui, son programme du jour, ou ses rendez-vous du jour."""
            if not module.store:
                return "Calendrier non disponible."
            try:
                now = datetime.now()
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(hour=23, minute=59, second=59, microsecond=0)
                return module._fetch_events(start, end)
            except Exception as e:
                return f"Erreur: {e}"

        @tool
        def list_upcoming_events(days: int = 7) -> str:
            """Liste les événements du calendrier pour les N prochains jours. Utilise cet outil quand l'utilisateur demande ses prochains rendez-vous, son agenda, ou les événements à venir.

            Args:
                days: nombre de jours à partir d'aujourd'hui (défaut: 7)
            """
            if not module.store:
                return "Calendrier non disponible."
            try:
                start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=days)
                return module._fetch_events(start, end)
            except Exception as e:
                return f"Erreur: {e}"

        @tool
        def create_event(title: str, start_iso: str, end_iso: str, calendar_name: str = "", notes: str = "") -> str:
            """Crée un événement dans le calendrier macOS. Utilise cet outil quand l'utilisateur veut ajouter, créer ou planifier un événement ou rendez-vous.

            Args:
                title: titre de l'événement
                start_iso: date/heure de début au format ISO 8601 (ex: '2026-04-29T14:00:00')
                end_iso: date/heure de fin au format ISO 8601 (ex: '2026-04-29T15:00:00')
                calendar_name: nom du calendrier cible (optionnel, prend le premier de la liste si vide)
                notes: notes ou description (optionnel)
            """
            if not module.store:
                return "Calendrier non disponible."
            try:
                import EventKit

                calendars = module._get_calendars()
                if not calendars:
                    return "Aucun calendrier trouvé."

                # Sélection du calendrier cible
                target = None
                if calendar_name:
                    target = next((c for c in calendars if c.title() == calendar_name), None)
                if not target:
                    target = calendars[0]

                start_dt = datetime.fromisoformat(start_iso)
                end_dt = datetime.fromisoformat(end_iso)

                event = EventKit.EKEvent.eventWithEventStore_(module.store)
                event.setTitle_(title)
                event.setStartDate_(module._ns_date(start_dt))
                event.setEndDate_(module._ns_date(end_dt))
                event.setCalendar_(target)

                if notes:
                    event.setNotes_(notes)

                error_ptr = None
                success = module.store.saveEvent_span_commit_error_(
                    event,
                    EventKit.EKSpanThisEvent,
                    True,
                    error_ptr
                )

                if success:
                    return f"Événement '{title}' créé le {start_dt.strftime('%d/%m à %Hh%M')} dans '{target.title()}'."
                else:
                    return "Échec de la création de l'événement."

            except Exception as e:
                return f"Erreur: {e}"

        @tool
        def delete_event(title: str) -> str:
            """Supprime un événement du calendrier via son titre. Supprime la première occurrence trouvée. Utilise cet outil quand l'utilisateur veut annuler, supprimer ou effacer un rendez-vous.

            Args:
                title: titre exact ou partiel de l'événement à supprimer
            """
            if not module.store:
                return "Calendrier non disponible."
            try:
                import EventKit

                # Recherche sur les 365 prochains jours
                start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=365)

                predicate = module.store.predicateForEventsWithStartDate_endDate_calendars_(
                    module._ns_date(start),
                    module._ns_date(end),
                    module._get_calendars()
                )
                events = module.store.eventsMatchingPredicate_(predicate) or []

                # Recherche insensible à la casse
                title_lower = title.lower()
                match = next(
                    (e for e in events if title_lower in str(e.title() or "").lower()),
                    None
                )

                if not match:
                    return f"Aucun événement trouvé avec le titre '{title}'."

                event_title = str(match.title())
                error_ptr = None
                success = module.store.removeEvent_span_commit_error_(
                    match,
                    EventKit.EKSpanThisEvent,
                    True,
                    error_ptr
                )

                if success:
                    return f"Événement '{event_title}' supprimé."
                else:
                    return "Échec de la suppression."

            except Exception as e:
                return f"Erreur: {e}"

        return [list_today_events, list_upcoming_events, create_event, delete_event]

    def _fetch_events(self, start: datetime, end: datetime) -> str:
        """Récupère et formate les événements entre deux dates."""
        import EventKit

        predicate = self.store.predicateForEventsWithStartDate_endDate_calendars_(
            self._ns_date(start),
            self._ns_date(end),
            self._get_calendars()
        )
        events = self.store.eventsMatchingPredicate_(predicate) or []

        if not events:
            return "Aucun événement sur cette période."

        # Tri par date de début
        events = sorted(events, key=lambda e: str(e.startDate()))

        lines = []
        for e in events:
            d = self._ekevent_to_dict(e)
            # Format lisible pour le LLM
            lines.append(
                f"- {d['title']} | {d['calendar']} | {d['start']} → {d['end']}"
                + (f" | {d['location']}" if d['location'] else "")
            )

        return "\n".join(lines)