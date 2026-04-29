"""
Point d'entrée principal de Neo.
"""
import asyncio

from core.agent import Agent
from core.config_manager import ConfigManager
from core.conversation import ConversationManager
from core.llm import LLM
from core.memory import MemoryManager
from core.router import Router
from core.stt import STT
from core.tts import TTS
from core.wake import WakeWord
from utils.colors import CYAN, GREEN, RESET
from utils.logging import technical_log


class Neo:
    """Neo - Orchestrateur principal"""

    def __init__(self):
        self.config = ConfigManager()

        self.llm = LLM()
        self.stt = STT()
        self.tts = TTS()
        self.wake = WakeWord()
        self.router = Router()
        self.memory = MemoryManager()

        self.agent = Agent(
            llm=self.llm.llm,
            tools=self.router.get_all_tools(),
            system_prompt=self.llm.system_prompt
        )

        self.conversation = ConversationManager(
            stt=self.stt,
            tts=self.tts,
            agent=self.agent,
            router=self.router,
            memory=self.memory,
            config=self.config.config
        )

        self.wake_enabled = self.config.get("wake", "enabled", default=True)

    async def wait_for_wake_word(self):
        if self.wake_enabled:
            self.wake.listen()
            technical_log("wake", "wake word detected")
        else:
            technical_log("wake", "wake word disabled, conversation always active")

    async def handle_user_input(self, user_input: str) -> bool:
        if await self.conversation.handle_goodbye(user_input, self.llm.llm):
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

                print(f"\n{GREEN}you > ", end="", flush=True)

                user_input = await self.conversation.listen_with_timeout()

                if user_input is None:
                    print()
                    await self.memory.extract(self.conversation.history.copy(), self.llm.llm)
                    self.conversation.reset()
                    await asyncio.sleep(0.5)
                    continue

                print(f"{GREEN}{user_input}{RESET}\n")

                if not user_input:
                    continue

                should_continue = await self.handle_user_input(user_input)
                if not should_continue:
                    break

            except KeyboardInterrupt:
                print(f"\n{CYAN}stopping...")
                self.tts.stop()
                import sounddevice as sd
                sd.stop()
                break

    def run(self):
        asyncio.run(self.conversation_loop())


def main():
    try:
        neo = Neo()
        neo.run()
    except KeyboardInterrupt:
        print()
    finally:
        import sounddevice as sd
        sd.stop()


if __name__ == "__main__":
    main()