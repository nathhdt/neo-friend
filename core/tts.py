import queue
import subprocess
import threading

from core.config_manager import ConfigManager
from utils.logging import technical_log, step_start, step_ok, step_error


class TTS:
    def __init__(self):
        config = ConfigManager()

        self.voice = config.get("tts", "voice")
        self.rate = config.get("tts", "rate")

        self.queue = queue.Queue()
        self.process = None
        self.lock = threading.Lock()
        self.running = True
        self._pending = threading.Event()

        step_start("tts", "initializing TTS engine")

        try:
            self.worker = threading.Thread(target=self._run, daemon=True)
            self.worker.start()

            step_ok("tts", "TTS ready")
        except Exception as e:
            step_error("tts", f"TTS initialization failed: {e}")
            raise

    def _run(self):
        while self.running:
            text = self.queue.get()

            if text is None:
                break

            try:
                with self.lock:
                    self.process = subprocess.Popen(
                        [
                            "say",
                            "-v", self.voice,
                            "-r", str(self.rate),
                            text
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                self._pending.clear()

                self.process.wait()

                with self.lock:
                    self.process = None

            except Exception as e:
                self._pending.clear()
                technical_log("tts", f"error: {e}")

    def speak(self, text: str):
        self._pending.set()
        self.queue.put(text)

    def is_speaking(self):
        with self.lock:
            active_process = self.process is not None

        return active_process or not self.queue.empty() or self._pending.is_set()

    def wait_until_done(self):
        while self.is_speaking():
            pass

    def stop(self):
        self.running = False

        with self.lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()

        self.queue.put(None)