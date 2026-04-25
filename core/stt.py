import mlx_whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
from pathlib import Path
from utils.logging import technical_log
from core.config_manager import ConfigManager
from core.vad import SileroVAD


class STT:
    def __init__(self):
        config = ConfigManager()

        stt_cfg = config.get("stt")
        vad_cfg = config.get("vad")

        self.model_name = stt_cfg["model"]
        self.model_path = Path(f"models/{self.model_name}")

        self.samplerate = stt_cfg.get("samplerate", 16000)

        self.vad = SileroVAD()
        self.frame_size = vad_cfg.get("frame_size", 512)
        self.silence_threshold = vad_cfg.get("silence_threshold", 40)
        
        self.should_stop = False

        technical_log("stt", f"loading model: {self.model_path}")

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                sf.write(tmp.name, np.zeros(self.samplerate), self.samplerate)
                mlx_whisper.transcribe(
                    tmp.name,
                    path_or_hf_repo=self.model_path
                )
        except Exception:
            pass

        technical_log("stt", "model loaded")

    def transcribe(self, audio):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            sf.write(tmp.name, audio, self.samplerate)
            result = mlx_whisper.transcribe(
                tmp.name,
                path_or_hf_repo=self.model_path
            )
        return result["text"].strip()

    def stop_listening(self):
        self.should_stop = True

    def listen(self):
        self.should_stop = False
        buffer = []
        recording = False
        silence_count = 0

        pre_buffer = []
        pre_buffer_size = int(self.samplerate * 0.5)

        def callback(indata, frames, time, status):
            nonlocal buffer, recording, silence_count, pre_buffer

            if self.should_stop:
                return

            audio = indata[:, 0]

            if len(audio) < self.frame_size:
                return
            
            pre_buffer.extend(audio)
            if len(pre_buffer) > pre_buffer_size:
                pre_buffer = pre_buffer[-pre_buffer_size:]

            if self.vad.is_speech(audio):
                if not recording:
                    buffer.extend(pre_buffer)

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
                    if self.should_stop:
                        break
                    if recording and silence_count >= self.silence_threshold:
                        break
                    sd.sleep(100)

        except KeyboardInterrupt:
            sd.stop()
            raise

        if len(buffer) == 0:
            return ""

        audio = np.array(buffer, dtype=np.float32)

        return self.transcribe(audio)