"""
Événements du domaine.
Chaque événement est un dataclass immutable qui décrit ce qui s'est passé.
Les modules s'abonnent à ces événements via le bus.
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ConversationEnded:
    """Émis quand une conversation se termine (goodbye ou inactivité)."""
    history: List[Dict[str, str]]
    reason: str = "goodbye"  # "goodbye" | "timeout"
