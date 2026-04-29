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

    def __init__(self, stt, tts, agent, router, config: Dict[str, Any]):
        self.stt = stt
        self.tts = tts
        self.agent = agent
        self.router = router

        conv_cfg = config.get("conversation", {})
        self.inactivity_timeout = conv_cfg.get("inactivity_timeout", 30.0)
        self.max_history_turns = conv_cfg.get("max_history_turns", 100)

        self.state = ConversationState.IDLE
        self.history: List[Dict[str, str]] = []

    def reset(self):
        """Réinitialise la conversation"""
        self.state = ConversationState.IDLE
        self.history = []
        technical_log("conversation", "conversation reset")

    def activate(self):
        """Active la conversation"""
        self.state = ConversationState.ACTIVE
        technical_log("conversation", "conversation activated")

    def is_active(self) -> bool:
        """Vérifie si la conversation est active"""
        return self.state == ConversationState.ACTIVE

    def add_turn(self, user_message: str, assistant_message: str):
        """Ajoute un tour de conversation à l'historique"""
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": assistant_message})
        self._truncate_history()

    def _truncate_history(self):
        """Tronque l'historique pour respecter la limite"""
        max_messages = self.max_history_turns * 2

        if len(self.history) > max_messages:
            old_count = len(self.history)
            self.history = self.history[-max_messages:]
            technical_log("conversation", f"truncated history: {old_count} -> {len(self.history)} messages")

    async def listen_with_timeout(self) -> Optional[str]:
        """Écoute l'utilisateur avec timeout d'inactivité"""
        try:
            user_input = await asyncio.wait_for(
                asyncio.to_thread(self.stt.listen),
                timeout=self.inactivity_timeout
            )
            return user_input
        except asyncio.TimeoutError:
            self.stt.stop_listening()
            await asyncio.sleep(0.5)
            technical_log("conversation", "inactivity timeout")
            self.reset()
            return None

    async def handle_goodbye(self, user_input: str) -> bool:
        """
        Gère les messages d'adieu

        Returns:
            True si c'est un adieu (conversation terminée)
        """
        if self.router.detect_goodbye(user_input):
            goodbye_msg = self.router.get_goodbye_response()
            self.tts.speak(goodbye_msg)

            while self.tts.is_speaking():
                await asyncio.sleep(0.05)

            self.reset()
            await asyncio.sleep(2.0)
            return True

        return False

    async def process_input(self, user_input: str) -> str:
        """
        Traite une entrée utilisateur via l'agent ReAct (LLM + tools).

        Returns:
            Réponse de l'assistant
        """
        prefix = f"{CYAN}neo > "
        print(prefix, end="", flush=True)

        return await stream_llm_to_tts(
            self.agent.run(user_input, history=self.history),
            self.tts,
            prefix
        )

    async def wait_for_tts(self):
        """Attend que le TTS termine"""
        while self.tts.is_speaking():
            await asyncio.sleep(0.05)