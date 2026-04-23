import yaml
import subprocess
import threading
import queue
from utils.logging import technical_log


class TTS:
    def __init__(self):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        self.voice = config["tts"].get("voice", "Amelie")
        self.rate = str(config["tts"].get("rate", 180))

        self.queue = queue.Queue()
        self.process = None
        self.lock = threading.Lock()
        self.running = True

        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

        technical_log("tts", "ready")

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
                            "-r", self.rate,
                            text
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                self.process.wait()

                with self.lock:
                    self.process = None

            except Exception as e:
                technical_log("tts", f"error: {e}")

    def speak(self, text: str):
        self.queue.put(text)

    def is_speaking(self):
        with self.lock:
            active_process = self.process is not None

        return active_process or not self.queue.empty()

    def wait_until_done(self):
        while self.is_speaking():
            pass

    def stop(self):
        self.running = False

        with self.lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()

        self.queue.put(None)