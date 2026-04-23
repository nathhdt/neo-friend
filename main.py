import asyncio
import subprocess
import re
import yaml

from core.llm import LLM
from core.stt import STT
from core.tts import TTS
from core.wake import WakeWord
from core.router import Router
from utils.colors import CYAN, GREEN, RESET
from utils.logging import technical_log


def extract_sentence(buffer: str):
    match = re.search(r'(.+?[.!?])(\s|$)', buffer)
    if match:
        sentence = match.group(1).strip()
        rest = buffer[match.end():]
        return sentence, rest
    return None, buffer


async def main():
    subprocess.run(["clear"])

    neo_brain = LLM()
    stt = STT()
    tts = TTS()
    wake = WakeWord()
    router = Router()

    conversation_active = False

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        INACTIVITY_TIMEOUT = config.get("conversation", {}).get("inactivity_timeout", 30.0)
        WAKE_ENABLED = config.get("wake", {}).get("enabled", True)

    while True:
        try:
            if not conversation_active:
                if WAKE_ENABLED:
                    technical_log("wake", "waiting for wake word...")
                    wake.listen()
                    technical_log("wake", "wake word detected, conversation active")
                else:
                    technical_log("wake", "wake word disabled, conversation always active")
                
                conversation_active = True

            print(f"\n{GREEN}you > ", end="", flush=True)
            
            async def listen_with_timeout():
                try:
                    return await asyncio.wait_for(
                        asyncio.to_thread(stt.listen),
                        timeout=INACTIVITY_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    stt.stop_listening()
                    await asyncio.sleep(0.5)
                    raise
            
            try:
                user_input = await listen_with_timeout()
            except asyncio.TimeoutError:
                print("\n")
                technical_log("wake", "inactivity timeout, returning to wake word mode")
                conversation_active = False
                await asyncio.sleep(0.5)
                continue
            
            print(f"{GREEN}{user_input}{RESET}\n")

            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "stop"]:
                break
            
            if router.detect_goodbye(user_input):
                goodbye_msg = router.get_goodbye_response()
                print(f"{CYAN}neo > {goodbye_msg}{RESET}\n")
                tts.speak(goodbye_msg)
                
                while tts.is_speaking():
                    await asyncio.sleep(0.05)
                
                conversation_active = False
                technical_log("wake", "conversation ended, returning to wake word mode")
                await asyncio.sleep(2.0)
                continue

            print(f"{CYAN}neo > ", end="", flush=True)

            buffer = ""

            async for chunk in neo_brain.think(user_input):
                print(f"{CYAN}{chunk}{RESET}", end="", flush=True)
                buffer += chunk

                sentence, buffer = extract_sentence(buffer)

                if sentence and len(sentence) > 5:
                    tts.speak(sentence)

            if buffer.strip():
                tts.speak(buffer.strip())

            while tts.is_speaking():
                await asyncio.sleep(0.05)

            print()

        except KeyboardInterrupt:
            print("\nStopping...")
            tts.stop()
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()