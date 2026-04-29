"""
EarconPlayer : sons système courts via NSSound (pyobjc).
NSSound bypasse les conflits avec sounddevice.
"""
from AppKit import NSSound
from pathlib import Path

from core.config_manager import ConfigManager
from utils.logging import step_ok, step_error


SYSTEM_SOUNDS_DIR = Path("/System/Library/Sounds")


class EarconPlayer:

    def __init__(self):
        config = ConfigManager()
        cfg = config.get("earcons") or {}

        self.sounds = {
            "listening": cfg.get("listening", "Pop.aiff"),
            "captured":  cfg.get("captured",  "Tink.aiff"),
            "goodbye":   cfg.get("goodbye",   "Glass.aiff"),
            "error":     cfg.get("error",     "Basso.aiff"),
        }

        missing = [
            name for name, filename in self.sounds.items()
            if not (SYSTEM_SOUNDS_DIR / filename).exists()
        ]
        if missing:
            step_error("earcons", f"missing sound files: {', '.join(missing)}")
        else:
            step_ok("earcons", "ready")

    def play(self, name: str):
        """Joue un earcon via NSSound (non bloquant, compatible sounddevice).

        Args:
            name: clé de l'earcon ("listening", "captured", "goodbye", "error")
        """
        filename = self.sounds.get(name)
        if not filename:
            return

        path = SYSTEM_SOUNDS_DIR / filename
        if not path.exists():
            return

        sound = NSSound.alloc().initWithContentsOfFile_byReference_(str(path), True)
        if sound:
            sound.play()