import asyncio
import subprocess
import re
import yaml

from core.llm import LLM
from core.stt import STT
from core.tts import TTS
from core.wake import WakeWord
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

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    back_cfg = config.get("backchannel", {})

    neo_brain = LLM()
    stt = STT()
    tts = TTS()
    wake = WakeWord()

    while True:
        try:
            technical_log("wake", "waiting for wake word...")
            wake.listen()

            print(f"\n{GREEN}you > ", end="", flush=True)
            user_input = stt.listen()
            print(f"{GREEN}{user_input}{RESET}\n")

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "stop"]:
                break

            print(f"{CYAN}neo > ", end="", flush=True)

            buffer = ""
            first_sentence_spoken = False

            async def backchannel_task():
                await asyncio.sleep(back_cfg.get("filler_after_s", 2.0))
                if not first_sentence_spoken and back_cfg.get("enabled", False):
                    tts.speak(back_cfg.get("filler_text", "Un instant."))

            task = asyncio.create_task(backchannel_task())

            async for chunk in neo_brain.think(user_input):
                print(f"{CYAN}{chunk}{RESET}", end="", flush=True)
                buffer += chunk

                sentence, buffer = extract_sentence(buffer)

                if sentence and len(sentence) > 5:
                    if not first_sentence_spoken:
                        first_sentence_spoken = True
                        if not task.done():
                            task.cancel()

                    tts.speak(sentence)

            if not task.done():
                task.cancel()

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