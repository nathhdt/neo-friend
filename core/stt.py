import yaml
import mlx_whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
from pathlib import Path
from utils.logging import technical_log
from core.vad import SileroVAD


class STT:
    def __init__(self):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        stt_cfg = config["stt"]
        vad_cfg = config["vad"]

        self.model_name = stt_cfg["model"]
        self.model_ref = Path(f"models/{self.model_name}")

        self.samplerate = stt_cfg.get("samplerate", 16000)

        self.vad = SileroVAD()
        self.frame_size = vad_cfg.get("frame_size", 512)
        self.silence_threshold = vad_cfg.get("silence_threshold", 40)

        technical_log("stt", "loading model...")

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                sf.write(tmp.name, np.zeros(self.samplerate), self.samplerate)
                mlx_whisper.transcribe(
                    tmp.name,
                    path_or_hf_repo=self.model_ref
                )
        except Exception:
            pass

        technical_log("stt", "model loaded")

    def transcribe(self, audio):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            sf.write(tmp.name, audio, self.samplerate)
            result = mlx_whisper.transcribe(
                tmp.name,
                path_or_hf_repo=self.model_ref
            )
        return result["text"].strip()

    def listen(self):
        buffer = []
        recording = False
        silence_count = 0

        def callback(indata, frames, time, status):
            nonlocal buffer, recording, silence_count

            audio = indata[:, 0]

            if len(audio) != self.frame_size:
                return

            if self.vad.is_speech(audio):
                recording = True
                silence_count = 0
                buffer.extend(audio)
            elif recording:
                silence_count += 1
                buffer.extend(audio)

        try:
            with sd.InputStream(
                samplerate=self.samplerate,
                channels=1,
                blocksize=self.frame_size,
                callback=callback
            ):
                while True:
                    if recording and silence_count >= self.silence_threshold:
                        break

        except KeyboardInterrupt:
            sd.stop()
            raise

        if len(buffer) == 0:
            return ""

        audio = np.array(buffer, dtype=np.float32)

        return self.transcribe(audio)