import asyncio
import subprocess
import re

from core.llm import LLM
from core.stt import STT
from core.tts import TTS
from core.wake import WakeWord
from utils.colors import CYAN, GREEN, RESET


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

    while True:
        try:
            print("\nwaiting for wake word...")
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