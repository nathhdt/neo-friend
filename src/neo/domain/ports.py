"""
Ports : interfaces abstraites du domaine.
Le domaine dépend de ces contrats, jamais des implémentations concrètes.
"""
from abc import ABC, abstractmethod
from typing import List, Dict


class STTPort(ABC):
    @abstractmethod
    def listen(self) -> str: ...

    @abstractmethod
    def stop_listening(self): ...


class TTSPort(ABC):
    @abstractmethod
    def speak(self, text: str): ...

    @abstractmethod
    def is_speaking(self) -> bool: ...

    @abstractmethod
    def stop(self): ...


class MemoryPort(ABC):
    @abstractmethod
    def recall(self, query: str) -> str: ...

    @abstractmethod
    def store(self, facts: List[dict]): ...

    @abstractmethod
    async def extract(self, history: List[Dict[str, str]], llm) -> None: ...


class WakeWordPort(ABC):
    @abstractmethod
    def listen(self) -> bool: ...


class VADPort(ABC):
    @abstractmethod
    def is_speech(self, audio) -> bool: ...


class EarconsPort(ABC):
    @abstractmethod
    def play(self, name: str): ...
