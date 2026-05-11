"""
Événements du domaine.
Chaque événement est un dataclass immutable qui décrit ce qui s'est passé.
Les modules s'abonnent à ces événements via le bus.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class ConversationEnded:
    """Émis quand une conversation se termine (goodbye ou inactivité)."""
    history: List[Dict[str, str]]
    reason: str = "goodbye"  # "goodbye" | "timeout"


@dataclass(frozen=True)
class ScheduledTask:
    """Émis par le scheduler quand un cron se déclenche."""
    task_id: str
    module: str
    action: str
    params: Tuple[Tuple[str, Any], ...] = ()  # immutable key-value pairs

    @property
    def params_dict(self) -> Dict[str, Any]:
        return dict(self.params)
