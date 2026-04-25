import re

from utils.colors import CYAN, BOLD, BOLD_RESET, ITALIC, ITALIC_RESET, RESET


def extract_sentence(buffer: str):
    """Extrait une phrase, un retour à la ligne, ou un bullet point"""
    if '\n' in buffer:
        parts = buffer.split('\n', 1)
        sentence = parts[0].strip()
        rest = parts[1] if len(parts) > 1 else ""
        if sentence:
            return sentence, rest
    
    match = re.search(r'(.+?[.!?])(\s|$)', buffer)
    if match:
        sentence = match.group(1).strip()
        rest = buffer[match.end():]
        return sentence, rest
    
    return None, buffer


def speak_text(text: str, tts):
    """Découpe un texte et l'envoie au TTS phrase par phrase"""
    buffer = text
    
    while buffer:
        sentence, buffer = extract_sentence(buffer)
        if sentence and len(sentence) > 5:
            tts.speak(sentence)
        else:
            break
    
    if buffer.strip():
        tts.speak(buffer.strip())


async def stream_llm_to_tts(llm_generator, tts, prefix, color=CYAN):
    from utils.text import markdown_to_ansi

    buffer = ""
    full_response = ""
    
    async for chunk in llm_generator:
        chunk = chunk.replace("\n", " ")

        print(f"{color}{chunk}{RESET}", end="", flush=True)

        buffer += chunk
        full_response += chunk
        
        sentence, buffer = extract_sentence(buffer)
        if sentence and len(sentence) > 5:
            tts.speak(sentence)
    
    if buffer.strip():
        tts.speak(buffer.strip())
    
    styled = markdown_to_ansi(full_response)
    
    print("\r\033[K", end="")

    print(f"{prefix}{styled}{RESET}")
    
    return full_response


def markdown_to_ansi(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", rf"{BOLD}\1{BOLD_RESET}", text)
    
    text = re.sub(r"\*(.*?)\*", rf"{ITALIC}\1{ITALIC_RESET}", text)
    
    return text