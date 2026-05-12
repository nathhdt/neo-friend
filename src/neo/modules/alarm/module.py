"""
Module Alarm : réveil intelligent avec briefing matinal.

Scénario :
  1. Le scheduler déclenche "prepare_briefing" 10 min avant le réveil
  2. Le module appelle les tools configurés (météo, calendrier, mails)
     et stocke le résultat dans self._briefing
  3. Le scheduler déclenche "ring" à l'heure du réveil
  4. Le module joue le son d'alarme en boucle
  5. L'utilisateur dit "hey jarvis" → le wake word stoppe l'alarme
  6. L'agent appelle get_morning_briefing → lit le compte-rendu
"""
import asyncio
import yaml

from AppKit import NSSound
from datetime import datetime
from langchain_core.tools import tool
from pathlib import Path
from typing import Callable, Dict, List, Type

from neo.domain.events import ScheduledTask
from neo.modules.base import ModuleBase
from neo.shared.logging import step_ok, step_error, technical_log


SYSTEM_SOUNDS_DIR = Path("/System/Library/Sounds")


class AlarmModule(ModuleBase):

    def __init__(self):
        super().__init__()
        self._config = self._load_config()
        self._briefing: str | None = None
        self._briefing_time: datetime | None = None
        self._ringing = False
        self._alarm_sound: NSSound | None = None

    def _load_config(self) -> dict:
        path = Path(__file__).parent / "config.yaml"
        if path.exists():
            with open(path) as f:
                return (yaml.safe_load(f) or {}).get("alarm", {})
        return {}

    def on_load(self):
        sound_file = self._config.get("sound", "Funk.aiff")
        sound_path = SYSTEM_SOUNDS_DIR / sound_file
        if not sound_path.exists():
            step_error("alarm", f"sound not found: {sound_path}")
        else:
            step_ok("alarm", "ready")

    def get_subscriptions(self) -> Dict[Type, Callable]:
        return {ScheduledTask: self._on_scheduled}

    # ── event handlers ───────────────────────────────────────────

    async def _on_scheduled(self, event: ScheduledTask):
        if event.module != "alarm":
            return

        if event.action == "prepare_briefing":
            await self._prepare_briefing()
        elif event.action == "ring":
            await self._ring()
        elif event.action == "stop":
            self._stop_ring()

    # ── briefing ─────────────────────────────────────────────────

    async def _prepare_briefing(self):
        """Appelle les tools configurés et compile le briefing."""
        tool_names = self._config.get("briefing_tools", [])

        if not tool_names:
            technical_log("alarm", "no briefing tools configured")
            return

        technical_log("alarm", f"preparing briefing ({len(tool_names)} tools)")
        parts = []

        for name in tool_names:
            try:
                result = await asyncio.to_thread(self.invoke_tool, name)
                parts.append(f"[{name}]\n{result}")
                technical_log("alarm", f"briefing: {name} ok")
            except Exception as e:
                parts.append(f"[{name}]\nindisponible ({e})")
                technical_log("alarm", f"briefing: {name} failed: {e}")

        self._briefing = "\n\n".join(parts)
        self._briefing_time = datetime.now()
        technical_log("alarm", "briefing ready")

    # ── alarm ring ───────────────────────────────────────────────

    async def _ring(self):
        """Joue le son d'alarme en boucle jusqu'à interruption."""
        sound_file = self._config.get("sound", "Funk.aiff")
        sound_path = SYSTEM_SOUNDS_DIR / sound_file

        if not sound_path.exists():
            technical_log("alarm", f"sound not found: {sound_path}")
            return

        self._ringing = True
        technical_log("alarm", "ringing")

        self._alarm_sound = NSSound.alloc().initWithContentsOfFile_byReference_(
            str(sound_path), True
        )

        while self._ringing and self._alarm_sound:
            self._alarm_sound.play()
            await asyncio.sleep(2.0)

        technical_log("alarm", "stopped")

    def _stop_ring(self):
        self._ringing = False
        if self._alarm_sound:
            self._alarm_sound.stop()
            self._alarm_sound = None

    # ── tools LLM ────────────────────────────────────────────────

    def get_tools(self) -> List:
        module = self

        @tool
        def get_morning_briefing() -> str:
            """Donne le compte-rendu du matin : météo, agenda, mails. Utilise cet outil quand l'utilisateur vient de se réveiller, demande son briefing, ou veut savoir ce qui l'attend aujourd'hui."""
            if module._briefing is None:
                return "Pas de briefing disponible. Aucun briefing n'a été préparé."

            age = ""
            if module._briefing_time:
                minutes = int((datetime.now() - module._briefing_time).total_seconds() / 60)
                if minutes > 0:
                    age = f" (préparé il y a {minutes} min)"

            # consomme le briefing (one-shot)
            briefing = module._briefing
            module._briefing = None
            module._briefing_time = None

            # stoppe l'alarme si elle sonne encore
            module._stop_ring()

            return f"Briefing matinal{age} :\n\n{briefing}"

        @tool
        def stop_alarm() -> str:
            """Arrête l'alarme en cours. Utilise cet outil quand l'utilisateur demande d'arrêter, couper ou éteindre l'alarme ou le réveil."""
            if module._ringing:
                module._stop_ring()
                return "Alarme arrêtée."
            return "Aucune alarme en cours."

        return [get_morning_briefing, stop_alarm]
