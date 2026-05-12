from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Type


class ModuleBase(ABC):

    def __init__(self):
        self.name = self.__class__.__name__
        self.enabled = True
        self.event_bus = None       # injecté par le router
        self.background = None      # injecté par le router
        self._tool_registry = {}    # peuplé par le router après chargement

    @abstractmethod
    def get_tools(self) -> List:
        """Retourne les LangChain Tools exposés par ce module."""
        pass

    def get_subscriptions(self) -> Dict[Type, Callable]:
        """Événements auxquels ce module réagit.

        Returns:
            {EventType: handler_method} — le router enregistre
            chaque paire sur le bus automatiquement.
        """
        return {}

    def invoke_tool(self, name: str, args: dict = None) -> Any:
        """Appelle un tool d'un autre module par son nom.

        Permet l'inter-communication entre modules sans couplage direct.
        Le registre est peuplé par le router après le chargement de tous les modules.
        """
        tool = self._tool_registry.get(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' not found in registry")
        return tool.invoke(args or {})

    def submit_background(self, coro, name: str = ""):
        """Raccourci pour lancer une tâche background depuis un module."""
        if self.background is None:
            raise RuntimeError(f"Module {self.name}: background runner not injected")
        task_name = name or f"{self.name}:background"
        return self.background.submit(coro, name=task_name)

    def on_load(self):
        pass

    def on_unload(self):
        pass
