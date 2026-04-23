import numpy as np
import sounddevice as sd
import yaml
from openwakeword.model import Model
from openwakeword.utils import download_models
from utils.logging import technical_log


class WakeWord:
    def __init__(self):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        wake_cfg = config["wake"]

        download_models()

        self.model_name = wake_cfg.get("model", "hey_jarvis")
        self.samplerate = wake_cfg.get("samplerate", 16000)
        self.chunk_size = wake_cfg.get("chunk_size", 1280)
        self.threshold = wake_cfg.get("threshold", 0.5)
        
        self.model = Model(
            wakeword_models=[self.model_name],
            inference_framework="onnx"
        )

    def listen(self):
        self.model = Model(
            wakeword_models=[self.model_name],
            inference_framework="onnx"
        )
        
        detected = False
        stream = None
        frame_count = 0
        max_score_seen = 0.0

        def callback(indata, frames, time, status):
            nonlocal detected, frame_count, max_score_seen

            if detected:
                return

            audio_int16 = np.frombuffer(
                (indata[:, 0] * 32767).astype(np.int16).tobytes(),
                dtype=np.int16
            )

            prediction = self.model.predict(audio_int16)

            frame_count += 1

            for key, score in prediction.items():
                if score > max_score_seen:
                    max_score_seen = score
                
                if frame_count % 20 == 0:
                    technical_log("wake", f"frame {frame_count} | {key}: {score:.4f} (max: {max_score_seen:.4f}, threshold: {self.threshold})")
                
                if score > self.threshold:
                    technical_log("wake", f"DETECTION! {key}: {score:.4f} > {self.threshold}")
                    detected = True
                    break

        stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            blocksize=self.chunk_size,
            callback=callback,
            dtype='float32'
        )

        stream.start()

        try:
            while not detected:
                sd.sleep(100)
        finally:
            stream.stop()
            stream.close()
            sd.sleep(200)

        return True