"""
Point d'entrée principal de Neo.
Architecture simplifiée avec délégation aux gestionnaires.
"""
import asyncio
import subprocess

from core.llm import LLM
from core.stt import STT
from core.tts import TTS
from core.wake import WakeWord
from core.router import Router
from core.conversation import ConversationManager
from core.config_manager import ConfigManager
from utils.colors import CYAN, GREEN, RESET
from utils.logging import technical_log


class Neo:
    """Assistant IA Neo - Orchestrateur principal"""
    
    def __init__(self):
        # configuration
        self.config = ConfigManager()
        
        # core components
        self.llm = LLM()
        self.stt = STT()
        self.tts = TTS()
        self.wake = WakeWord()
        self.router = Router()
        
        self.conversation = ConversationManager(
            stt=self.stt,
            tts=self.tts,
            llm=self.llm,
            router=self.router,
            config=self.config.config
        )
        
        self.wake_enabled = self.config.get("wake", "enabled", default=True)
    
    async def wait_for_wake_word(self):
        """Attend le wake word si activé"""
        if self.wake_enabled:
            technical_log("wake", "waiting for wake word...")
            self.wake.listen()
            technical_log("wake", "wake word detected")
        else:
            technical_log("wake", "wake word disabled, conversation always active")
    
    async def handle_user_input(self, user_input: str) -> bool:
        """
        Traite l'entrée utilisateur
        
        Returns:
            True pour continuer, False pour arrêter l'app
        """
        if user_input.lower() in ["exit", "quit", "stop"]:
            return False
        
        if await self.conversation.handle_goodbye(user_input):
            return True
        
        response = await self.conversation.process_input(user_input)
        self.conversation.add_turn(user_input, response)
        
        await self.conversation.wait_for_tts()
        print()
        
        return True
    
    async def conversation_loop(self):
        """Boucle de conversation principale"""
        while True:
            try:
                if not self.conversation.is_active():
                    await self.wait_for_wake_word()
                    self.conversation.activate()
                
                print(f"\n{GREEN}you > ", end="", flush=True)
                
                user_input = await self.conversation.listen_with_timeout()
                
                if user_input is None:
                    print()
                    await asyncio.sleep(0.5)
                    continue
                
                print(f"{GREEN}{user_input}{RESET}\n")
                
                if not user_input:
                    continue
                
                should_continue = await self.handle_user_input(user_input)
                if not should_continue:
                    break
            
            except KeyboardInterrupt:
                print("\nStopping...")
                self.tts.stop()
                break
    
    def run(self):
        """Lance Neo"""
        subprocess.run(["clear"])
        asyncio.run(self.conversation_loop())


def main():
    """Point d'entrée"""
    try:
        neo = Neo()
        neo.run()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()