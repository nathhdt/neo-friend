import asyncio
import re

from utils.colors import CYAN, BOLD, BOLD_RESET, ITALIC, ITALIC_RESET, RESET


def extract_sentence(buffer: str):
    """Extrait une phrase complète ou une ligne du buffer."""
    if "\n" in buffer:
        parts = buffer.split("\n", 1)
        sentence = parts[0].strip()
        rest = parts[1] if len(parts) > 1 else ""
        if sentence:
            return sentence, rest

    match = re.search(r"(.+?[.!?])(\s|$)", buffer)
    if match:
        sentence = match.group(1).strip()
        rest = buffer[match.end():]
        return sentence, rest

    return None, buffer


def _clean_for_tts(text: str) -> str:
    """Retire les marqueurs markdown et tirets de liste pour le TTS."""
    text = re.sub(r"^\s*[-•]\s*", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return text.strip()


def markdown_to_ansi(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", rf"{BOLD}\1{BOLD_RESET}", text)
    text = re.sub(r"\*(.*?)\*", rf"{ITALIC}\1{ITALIC_RESET}", text)
    return text


async def _thinking_animation(prefix: str, stop_event: asyncio.Event, color=CYAN):
    """
    Affiche '.' '..' '...' en boucle sur la ligne courante.
    Utilise \r\033[K pour effacer proprement avant chaque réécriture.
    """
    dots = [".  ", ".. ", "..."]
    i = 0
    while not stop_event.is_set():
        print(f"\r\033[K{color}{prefix}{dots[i % 3]}{RESET}", end="", flush=True)
        i += 1
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=0.2)
        except asyncio.TimeoutError:
            pass

    print("\r\033[K", end="", flush=True)


async def stream_llm_to_tts(llm_generator, tts, prefix, color=CYAN):
    buffer = ""
    full_response = ""
    stop_animation = asyncio.Event()
    first_chunk = True

    animation_task = asyncio.create_task(
        _thinking_animation(prefix, stop_animation, color)
    )

    async for chunk in llm_generator:
        if first_chunk:
            stop_animation.set()
            await animation_task
            # Ligne vide de séparation si des logs ont été affichés (curseur pas en début de ligne)
            print(f"\r\033[K")
            print(f"{color}{prefix}", end="", flush=True)
            first_chunk = False

        # Affichage : on garde les \n pour la console
        print(f"{color}{chunk}{RESET}", end="", flush=True)

        # Buffer : on remplace \n par espace uniquement pour le découpage de phrases
        buffer += chunk.replace("\n", " ")
        full_response += chunk

        sentence, buffer = extract_sentence(buffer)
        if sentence and len(sentence) > 5:
            tts.speak(_clean_for_tts(sentence))

    if not first_chunk:
        if buffer.strip():
            tts.speak(_clean_for_tts(buffer.strip()))

        styled = markdown_to_ansi(full_response)
        print("\r\033[K", end="")
        print(f"{color}{prefix}{styled}{RESET}")
    else:
        stop_animation.set()
        await animation_task

    return full_response