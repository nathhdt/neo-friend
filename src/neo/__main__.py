"""
Point d'entrée principal de Neo.
"""
import asyncio
import warnings

import sounddevice as sd

from neo.adapters.earcons import EarconPlayer
from neo.adapters.lancedb_memory import MemoryManager
from neo.adapters.macos_tts import TTS
from neo.adapters.mlx_stt import STT
from neo.adapters.ollama import LLM
from neo.adapters.wake import WakeWord
from neo.domain.agent import Agent
from neo.domain.conversation import ConversationManager
from neo.domain.events import ConversationEnded
from neo.infra.config import ConfigManager
from neo.infra.router import Router
from neo.runtime.background import BackgroundRunner
from neo.runtime.event_bus import EventBus
from neo.runtime.scheduler import Scheduler
from neo.shared.colors import BLUE, PINK, RESET
from neo.shared.logging import technical_log

warnings.filterwarnings("ignore", category=DeprecationWarning, module="langgraph")


class Neo:
    """Neo - Orchestrateur principal"""

    def __init__(self):
        self.config = ConfigManager()

        # runtime
        self.background = BackgroundRunner()
        self.event_bus = EventBus(self.background)
        self.scheduler = Scheduler(
            self.event_bus,
            self.config.get("schedules", default=[]) or []
        )

        # adapters
        self.llm = LLM()
        self.stt = STT()
        self.tts = TTS()
        self.wake = WakeWord()
        self.earcons = EarconPlayer()

        # memory + injection LLM
        self.memory = MemoryManager()
        self.memory.set_llm(self.llm.llm)

        # modules
        self.router = Router(event_bus=self.event_bus, background=self.background)

        # agent
        self.agent = Agent(
            llm=self.llm.llm,
            tools=self.router.get_all_tools(),
            system_prompt=self.llm.system_prompt
        )

        # conversation
        self.conversation = ConversationManager(
            stt=self.stt,
            tts=self.tts,
            agent=self.agent,
            router=self.router,
            memory=self.memory,
            earcons=self.earcons,
            event_bus=self.event_bus,
            config=self.config.config
        )

        # subscriptions
        self.event_bus.subscribe(ConversationEnded, self.memory.on_conversation_ended)

        self.wake_enabled = self.config.get("wake", "enabled", default=True)

    async def wait_for_wake_word(self):
        if self.wake_enabled:
            await asyncio.to_thread(self.wake.listen)
            technical_log("wake", "wake word detected")
        else:
            technical_log("wake", "wake word disabled, conversation always active")

    async def handle_user_input(self, user_input: str) -> bool:
        if await self.conversation.handle_goodbye(user_input):
            return True

        response = await self.conversation.process_input(user_input)
        self.conversation.add_turn(user_input, response)
        await self.conversation.wait_for_tts()

        return True

    async def conversation_loop(self):
        while True:
            try:
                if not self.conversation.is_active():
                    await self.wait_for_wake_word()
                    self.conversation.activate()

                await self.conversation.wait_for_tts()

                print(f"\n{PINK}you > ", end="", flush=True)

                self.earcons.play("listening")
                await asyncio.sleep(0.3)

                user_input = await self.conversation.listen_with_timeout()

                if user_input is None:
                    print()
                    await self.conversation.end_conversation(reason="timeout")
                    await asyncio.sleep(0.5)
                    continue

                print(f"{PINK}{user_input}{RESET}\n")

                if not user_input:
                    continue

                if not self.router.detect_goodbye(user_input):
                    self.earcons.play("captured")

                should_continue = await self.handle_user_input(user_input)
                if not should_continue:
                    break

            except KeyboardInterrupt:
                break

    async def _run(self):
        """Lance le scheduler et la boucle de conversation en parallèle."""
        scheduler_task = asyncio.create_task(self.scheduler.run())

        try:
            await self.conversation_loop()
        finally:
            print(f"\n{BLUE}stopping...{RESET}")
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
            self.tts.stop()
            sd.stop()
            await self.background.shutdown()

    def run(self):
        asyncio.run(self._run())


def main():
    try:
        neo = Neo()
        neo.run()
    except KeyboardInterrupt:
        print()
    finally:
        sd.stop()


if __name__ == "__main__":
    main()