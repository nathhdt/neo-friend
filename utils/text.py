import re


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