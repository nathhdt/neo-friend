import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from openwakeword.utils import download_models


class WakeWord:
    def __init__(self):
        download_models()

        self.model = Model(
            wakeword_models=["alexa"],  # ou hey_jarvis
            inference_framework="onnx"
        )

        self.samplerate = 16000
        self.frame_size = 512
        self.threshold = 0.3

        self._frame_count = 0

    def listen(self):
        detected = False

        def callback(indata, frames, time, status):
            nonlocal detected

            audio = indata[:, 0]

            if len(audio) != self.frame_size:
                return

            audio = audio.astype(np.float32)

            # normalisation légère (PAS RMS agressif)
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val

            # 🔥 IMPORTANT : on envoie DIRECT le frame
            prediction = self.model.predict(audio)

            # debug utile (pas spam)
            self._frame_count += 1
            if self._frame_count % 10 == 0:
                print({k: float(v) for k, v in prediction.items()})

            for key, score in prediction.items():
                if score > self.threshold:
                    print(f"[wake] DETECTED {key} ({score:.2f})")
                    detected = True

        with sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            blocksize=self.frame_size,
            callback=callback
        ):
            while not detected:
                pass

        return True