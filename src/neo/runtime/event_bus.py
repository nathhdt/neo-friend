"""
EventBus : pub/sub asynchrone interne.
Les handlers sont exécutés via le BackgroundRunner (fire-and-forget).
"""
from collections import defaultdict
from typing import Any, Callable, Coroutine

from neo.runtime.background import BackgroundRunner
from neo.shared.logging import technical_log


class EventBus:

    def __init__(self, background: BackgroundRunner):
        self._background = background
        self._subscribers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable[..., Coroutine]):
        """Abonne un handler async à un type d'événement."""
        self._subscribers[event_type].append(handler)
        technical_log("event_bus", f"subscribed {handler.__qualname__} -> {event_type.__name__}")

    def unsubscribe(self, event_type: type, handler: Callable):
        """Désabonne un handler."""
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: Any):
        """Émet un événement. Tous les handlers abonnés sont lancés en background."""
        event_name = type(event).__name__
        handlers = self._subscribers.get(type(event), [])

        if not handlers:
            return

        technical_log("event_bus", f"emit {event_name} -> {len(handlers)} handler(s)")

        for handler in handlers:
            self._background.submit(
                handler(event),
                name=f"event:{event_name}:{handler.__qualname__}"
            )
