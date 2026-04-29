"""
Gestionnaire de conversation centralisé.
Responsabilités : état, historique, timeouts, orchestration STT/TTS/Agent.
"""
import asyncio

from enum import Enum
from typing import Optional, Dict, Any, List
from utils.colors import CYAN
from utils.logging import technical_log
from utils.text import stream_llm_to_tts


class ConversationState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    GOODBYE = "goodbye"


class ConversationManager:
    """Gère le cycle de vie complet d'une conversation"""

    def __init__(self, stt, tts, agent, router, memory, config: Dict[str, Any]):
        self.stt = stt
        self.tts = tts
        self.agent = agent
        self.router = router
        self.memory = memory

        conv_cfg = config.get("conversation", {})
        self.inactivity_timeout = conv_cfg.get("inactivity_timeout", 30.0)
        self.max_history_turns = conv_cfg.get("max_history_turns", 100)

        self.state = ConversationState.IDLE
        self.history: List[Dict[str, str]] = []

    def _set_state(self, new_state: ConversationState):
        if self.state != new_state:
            technical_log("conversation", f"state: {self.state.value} -> {new_state.value}")
            self.state = new_state

    def reset(self):
        self._set_state(ConversationState.IDLE)
        self.history = []

    def activate(self):
        self._set_state(ConversationState.ACTIVE)

    def is_active(self) -> bool:
        return self.state == ConversationState.ACTIVE

    def add_turn(self, user_message: str, assistant_message: str):
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": assistant_message})
        self._truncate_history()

    def _truncate_history(self):
        max_messages = self.max_history_turns * 2
        if len(self.history) > max_messages:
            old_count = len(self.history)
            self.history = self.history[-max_messages:]
            technical_log("conversation", f"truncated history: {old_count} -> {len(self.history)} messages")

    async def listen_with_timeout(self) -> Optional[str]:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.stt.listen),
                timeout=self.inactivity_timeout
            )
        except asyncio.TimeoutError:
            self.stt.stop_listening()
            await asyncio.sleep(0.5)
            technical_log("conversation", "inactivity timeout")
            return None

    async def handle_goodbye(self, user_input: str, llm) -> bool:
        """
        Gère les messages d'adieu.
        Transition : ACTIVE -> GOODBYE -> IDLE.
        Extrait les souvenirs en parallèle du TTS — aucun délai perçu.

        Returns:
            True si c'est un adieu
        """
        if not self.router.detect_goodbye(user_input):
            return False

        self._set_state(ConversationState.GOODBYE)
        self.tts.speak(self.router.get_goodbye_response())

        history_snapshot = self.history.copy()
        await asyncio.gather(
            self._wait_tts(),
            self.memory.extract(history_snapshot, llm),
        )

        self.reset()
        await asyncio.sleep(2.0)
        return True

    async def process_input(self, user_input: str) -> str:
        """
        Traite une entrée utilisateur via l'agent ReAct.
        Recall mémoire injecté dans le contexte avant génération.

        Returns:
            Réponse de l'assistant
        """
        memory_context = self.memory.recall(user_input)

        prefix = f"{CYAN}neo > "
        print(prefix, end="", flush=True)

        return await stream_llm_to_tts(
            self.agent.run(user_input, history=self.history, memory_context=memory_context),
            self.tts,
            prefix
        )

    async def _wait_tts(self):
        while self.tts.is_speaking():
            await asyncio.sleep(0.05)

    async def wait_for_tts(self):
        await self._wait_tts()