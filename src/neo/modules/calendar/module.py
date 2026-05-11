import EventKit
from Foundation import NSDate
import time
import unicodedata
import yaml

from datetime import datetime, timedelta
from langchain_core.tools import tool
from pathlib import Path
from typing import List, Dict, Any

from neo.modules.base import ModuleBase
from neo.shared.logging import step_ok, step_error


class CalendarModule(ModuleBase):

    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self.calendar_names = self.config.get("calendars", [])
        self.store = None

    def _load_config(self) -> Dict[str, Any]:
        path = Path(__file__).parent / "config.yaml"
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return {}

    def on_load(self):
        try:
            self.store = EventKit.EKEventStore.alloc().init()

            granted = [False]
            done = [False]

            def handler(result, error):
                granted[0] = result
                done[0] = True

            self.store.requestAccessToEntityType_completion_(
                EventKit.EKEntityTypeEvent,
                handler
            )

            elapsed = 0
            while not done[0] and elapsed < 10:
                time.sleep(0.1)
                elapsed += 0.1

            if not granted[0]:
                step_error("calendar", "access denied — authorize in System Settings → Privacy → Calendars")
                self.store = None
                return

            step_ok("calendar", f"ready ({len(self.calendar_names)} calendars: {', '.join(self.calendar_names)})")

        except ImportError:
            step_error("calendar", "pyobjc-framework-EventKit not installed")
            self.store = None
        except Exception as e:
            step_error("calendar", f"initialization failed: {e}")
            self.store = None

    def _get_calendars(self):
        if not self.store:
            return []
        all_calendars = self.store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
        return [c for c in all_calendars if c.title() in self.calendar_names]

    def _ns_date(self, dt: datetime):
        return NSDate.dateWithTimeIntervalSince1970_(dt.timestamp())

    @staticmethod
    def _clean_title(title: str) -> str:
        return "".join(c for c in title if unicodedata.category(c) not in ("So", "Sk", "Sm", "Cs")).strip()

    @staticmethod
    def _extract_city(location: str) -> str:
        if not location:
            return ""
        parts = [p.strip() for p in location.split(",") if p.strip()]
        return parts[-1] if parts else location

    def _format_event(self, event) -> str:
        title = self._clean_title(str(event.title() or "Sans titre"))
        calendar = str(event.calendar().title())
        location = str(event.location() or "")

        start_ns = event.startDate()
        end_ns = event.endDate()

        start = datetime.fromtimestamp(start_ns.timeIntervalSince1970())
        end = datetime.fromtimestamp(end_ns.timeIntervalSince1970())

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)

        if start.date() == today:
            date_str = "aujourd'hui"
        elif start.date() == tomorrow:
            date_str = "demain"
        else:
            days_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            months_fr = ["janvier", "février", "mars", "avril", "mai", "juin",
                         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            date_str = f"{days_fr[start.weekday()]} {start.day} {months_fr[start.month - 1]}"

        end_normalized = end.replace(hour=0, minute=0, second=0) if (end.hour == 23 and end.minute == 59) else end
        is_multiday = end_normalized.date() > start.date()

        is_all_day = (start.hour == 0 and start.minute == 0 and
                      (end.hour in (0, 23) and end.minute in (0, 59)))

        if calendar == "Anniversaires" or is_all_day:
            time_str = ""
        elif is_multiday:
            months_fr2 = ["janvier", "février", "mars", "avril", "mai", "juin",
                          "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            time_str = f" jusqu'au {end_normalized.day} {months_fr2[end_normalized.month - 1]}"
        else:
            time_str = f" à {start.strftime('%H:%M').replace(':00', 'h').replace(':', 'h')}"
            if end.date() == start.date():
                time_str += f" jusqu'à {end.strftime('%H:%M').replace(':00', 'h').replace(':', 'h')}"

        parts = [f"{title} — {date_str}{time_str}"]
        city = self._extract_city(location)
        if city:
            parts.append(f"à {city}")
        if calendar == "Anniversaires":
            parts.append("(anniversaire)")
        elif calendar != "Personnel":
            parts.append(f"calendrier : {calendar}")

        return ", ".join(parts)

    def _fetch_events(self, start: datetime, end: datetime) -> str:
        predicate = self.store.predicateForEventsWithStartDate_endDate_calendars_(
            self._ns_date(start),
            self._ns_date(end),
            self._get_calendars()
        )
        events = self.store.eventsMatchingPredicate_(predicate) or []

        if not events:
            return "Aucun événement sur cette période."

        events = sorted(events, key=lambda e: e.startDate().timeIntervalSince1970())

        lines = [self._format_event(e) for e in events]
        count = len(lines)
        intro = f"{count} événement{'s' if count > 1 else ''} trouvé{'s' if count > 1 else ''}, liste complète :"
        return intro + "\n" + "\n".join(lines)

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
                calendars = module._get_calendars()
                if not calendars:
                    return "Aucun calendrier trouvé."

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

                success = module.store.saveEvent_span_commit_error_(
                    event, EventKit.EKSpanThisEvent, True, None
                )

                if success:
                    return f"Événement '{title}' créé le {start_dt.strftime('%d/%m à %Hh%M')} dans '{target.title()}'."
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
                start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=365)

                predicate = module.store.predicateForEventsWithStartDate_endDate_calendars_(
                    module._ns_date(start),
                    module._ns_date(end),
                    module._get_calendars()
                )
                events = module.store.eventsMatchingPredicate_(predicate) or []

                title_lower = title.lower()
                match = next(
                    (e for e in events if title_lower in str(e.title() or "").lower()),
                    None
                )

                if not match:
                    return f"Aucun événement trouvé avec le titre '{title}'."

                event_title = str(match.title())
                success = module.store.removeEvent_span_commit_error_(
                    match, EventKit.EKSpanThisEvent, True, None
                )

                if success:
                    return f"Événement '{event_title}' supprimé."
                return "Échec de la suppression."

            except Exception as e:
                return f"Erreur: {e}"

        return [list_today_events, list_upcoming_events, create_event, delete_event]
