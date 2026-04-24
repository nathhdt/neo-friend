import asyncio
import subprocess
import yaml

from core.llm import LLM
from core.stt import STT
from core.tts import TTS
from core.wake import WakeWord
from core.router import Router
from core.module_base import ModuleResponse
from utils.colors import CYAN, GREEN, RESET
from utils.logging import technical_log
from utils.text import speak_text, stream_llm_to_tts


def truncate_history(history, max_turns):
    """
    Tronque l'historique pour garder les N derniers tours
    
    Args:
        history: Liste de messages
        max_turns: Nombre maximum de tours (user + assistant = 1 tour)
    
    Returns:
        Liste tronquée
    """
    max_messages = max_turns * 2
    
    if len(history) > max_messages:
        old_count = len(history)
        history = history[-max_messages:]
        technical_log("memory", f"truncated history: {old_count} -> {len(history)} messages")
    
    return history


async def main():
    subprocess.run(["clear"])

    neo_brain = LLM()
    stt = STT()
    tts = TTS()
    wake = WakeWord()
    router = Router()

    conversation_active = False
    conversation_history = []

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        INACTIVITY_TIMEOUT = config.get("conversation", {}).get("inactivity_timeout", 30.0)
        WAKE_ENABLED = config.get("wake", {}).get("enabled", True)
        MAX_HISTORY_TURNS = config.get("conversation", {}).get("max_history_turns", 50)

    technical_log("memory", f"conversation history limit: {MAX_HISTORY_TURNS} turns ({MAX_HISTORY_TURNS * 2} messages)")

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
                conversation_history = []
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
                conversation_history = []
                technical_log("wake", "conversation ended, returning to wake word mode")
                await asyncio.sleep(2.0)
                continue
            
            context = {
                'tts': tts,
                'stt': stt,
                'config': config,
                'llm': neo_brain
            }
            
            module_response = await router.route(user_input, context)
            
            if module_response:
                if isinstance(module_response, str):
                    print(f"{CYAN}neo > {module_response}{RESET}\n")
                    speak_text(module_response, tts)
                    
                    conversation_history.append({"role": "user", "content": user_input})
                    conversation_history.append({"role": "assistant", "content": module_response})
                    
                    conversation_history = truncate_history(conversation_history, MAX_HISTORY_TURNS)
                    
                    while tts.is_speaking():
                        await asyncio.sleep(0.05)
                    
                    print()
                    continue
                
                elif isinstance(module_response, ModuleResponse):
                    import json
                    
                    data_json = json.dumps(module_response.content, indent=2, ensure_ascii=False)
                    
                    enriched_prompt = f"""L'utilisateur a demandé : "{user_input}"

Voici les données récupérées :
{data_json}

Métadonnées : {module_response.metadata}

{module_response.instructions}

Réponds à l'utilisateur de manière naturelle et conversationnelle en français."""
                    
                    print(f"{CYAN}neo > ", end="", flush=True)
                    
                    response = await stream_llm_to_tts(
                        neo_brain.think(enriched_prompt, history=conversation_history), 
                        tts
                    )
                    
                    conversation_history.append({"role": "user", "content": user_input})
                    conversation_history.append({"role": "assistant", "content": response})
                    
                    conversation_history = truncate_history(conversation_history, MAX_HISTORY_TURNS)
                    
                    while tts.is_speaking():
                        await asyncio.sleep(0.05)
                    
                    print()
                    continue
            
            conversation_history.append({"role": "user", "content": user_input})
            
            print(f"{CYAN}neo > ", end="", flush=True)
            
            response = await stream_llm_to_tts(
                neo_brain.think(user_input, history=conversation_history), 
                tts
            )
            
            conversation_history.append({"role": "assistant", "content": response})
            
            conversation_history = truncate_history(conversation_history, MAX_HISTORY_TURNS)

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