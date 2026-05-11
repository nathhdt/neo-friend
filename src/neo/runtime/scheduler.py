"""
Scheduler : planificateur de tâches cron-like.
Lit les schedules depuis config.yaml, vérifie chaque minute,
et émet des ScheduledTask sur le bus d'événements.
"""
import asyncio

from datetime import datetime
from typing import Any, Dict, List

from neo.domain.events import ScheduledTask
from neo.runtime.event_bus import EventBus
from neo.shared.logging import technical_log, step_ok


# ── Minimal cron parser ──────────────────────────────────────────────

def _match_field(field: str, value: int) -> bool:
    """Vérifie si une valeur correspond à un champ cron.

    Supporte : * | N | N-M | N,M,O | N-M,O
    """
    if field == "*":
        return True

    for part in field.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            if int(lo) <= value <= int(hi):
                return True
        else:
            if int(part) == value:
                return True

    return False


def cron_matches(expression: str, dt: datetime) -> bool:
    """Vérifie si une datetime correspond à une expression cron.

    Format : minute heure jour_du_mois mois jour_de_semaine
    Jour de semaine : 0 = lundi, 6 = dimanche
    """
    fields = expression.strip().split()
    if len(fields) != 5:
        return False

    minute, hour, dom, month, dow = fields

    return (
        _match_field(minute, dt.minute)
        and _match_field(hour, dt.hour)
        and _match_field(dom, dt.day)
        and _match_field(month, dt.month)
        and _match_field(dow, dt.weekday())
    )


# ── Scheduler ────────────────────────────────────────────────────────

class Scheduler:

    def __init__(self, event_bus: EventBus, schedules: List[Dict[str, Any]]):
        self._event_bus = event_bus
        self._schedules = schedules
        self._last_fired: Dict[str, datetime] = {}

        if schedules:
            step_ok("scheduler", f"loaded {len(schedules)} schedule(s)")
        else:
            step_ok("scheduler", "no schedules configured")

    def _should_fire(self, schedule_id: str, cron_expr: str, now: datetime) -> bool:
        """Vérifie si un schedule doit se déclencher maintenant."""
        if not cron_matches(cron_expr, now):
            return False

        last = self._last_fired.get(schedule_id)
        if last and last.minute == now.minute and last.hour == now.hour and last.date() == now.date():
            return False  # déjà déclenché cette minute

        return True

    async def _tick(self):
        """Vérifie tous les schedules et émet les événements."""
        now = datetime.now()

        for schedule in self._schedules:
            sid = schedule.get("id", "unknown")
            cron_expr = schedule.get("cron", "")
            module = schedule.get("module", "")
            action = schedule.get("action", "")
            params = schedule.get("params", {})

            if not cron_expr or not module or not action:
                continue

            if self._should_fire(sid, cron_expr, now):
                self._last_fired[sid] = now
                technical_log("scheduler", f"firing '{sid}' -> {module}.{action}")

                params_tuple = tuple(params.items()) if isinstance(params, dict) else ()

                await self._event_bus.emit(ScheduledTask(
                    task_id=sid,
                    module=module,
                    action=action,
                    params=params_tuple,
                ))

    async def run(self):
        """Boucle principale du scheduler. Vérifie toutes les 30 secondes."""
        technical_log("scheduler", "started")
        try:
            while True:
                await self._tick()
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            technical_log("scheduler", "stopped")
