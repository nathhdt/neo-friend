from abc import ABC, abstractmethod
from typing import List


class ModuleBase(ABC):

    def __init__(self):
        self.name = self.__class__.__name__
        self.enabled = True

    @abstractmethod
    def get_tools(self) -> List:
        """Retourne les LangChain Tools exposés par ce module."""
        pass

    def on_load(self):
        pass

    def on_unload(self):
        pass