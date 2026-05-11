"""
EarconPlayer : sons système courts via NSSound (pyobjc).
NSSound bypasse les conflits avec sounddevice.
"""
from AppKit import NSSound
from pathlib import Path

from neo.domain.ports import EarconsPort
from neo.infra.config import ConfigManager
from neo.shared.logging import step_ok, step_error


SYSTEM_SOUNDS_DIR = Path("/System/Library/Sounds")


class EarconPlayer(EarconsPort):

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
        filename = self.sounds.get(name)
        if not filename:
            return

        path = SYSTEM_SOUNDS_DIR / filename
        if not path.exists():
            return

        sound = NSSound.alloc().initWithContentsOfFile_byReference_(str(path), True)
        if sound:
            sound.play()
