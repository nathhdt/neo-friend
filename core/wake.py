import numpy as np
import sounddevice as sd
import yaml
from openwakeword.model import Model
from openwakeword.utils import download_models


class WakeWord:
    def __init__(self):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        wake_cfg = config["wake"]

        download_models()

        self.model = Model(
            wakeword_models=[wake_cfg.get("model", "hey_jarvis")],
            inference_framework="onnx"
        )

        self.samplerate = wake_cfg.get("samplerate", 16000)
        self.chunk_size = wake_cfg.get("chunk_size", 1280)
        self.threshold = wake_cfg.get("threshold", 0.5)

    def listen(self):
        detected = False
        frame_count = 0

        def callback(indata, frames, time, status):
            nonlocal detected, frame_count

            audio_int16 = np.frombuffer(
                (indata[:, 0] * 32767).astype(np.int16).tobytes(),
                dtype=np.int16
            )

            prediction = self.model.predict(audio_int16)

            frame_count += 1

            for _, score in prediction.items():
                if score > self.threshold:
                    detected = True

        with sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            blocksize=self.chunk_size,
            callback=callback,
            dtype='float32'
        ):
            while not detected:
                sd.sleep(100)

        return True