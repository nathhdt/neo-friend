import numpy as np
import os
import sounddevice as sd
import time

from core.config_manager import ConfigManager
from openwakeword.model import Model
from openwakeword.utils import download_models
from utils.logging import technical_log


class WakeWord:
    def __init__(self):
        config = ConfigManager()

        self.enabled = config.get("wake", "enabled", default=True)
        
        if self.enabled:
            download_models()
            
            self.model_name = config.get("wake", "model", default="hey_jarvis")
            self.samplerate = config.get("wake", "samplerate", default=16000)
            self.chunk_size = config.get("wake", "chunk_size", default=1280)
            self.threshold = config.get("wake", "threshold", default=0.5)
            
            self.model = Model(
                wakeword_models=[self.model_name],
                inference_framework="onnx"
            )

    def _find_input_device(self):
        """Trouve le micro physique"""
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0 and 'Microphone' in dev['name']:
                    if 'NoMachine' not in dev['name']:
                        return i
        except Exception:
            pass
        return None

    def _open_stream(self, callback):
        """Ouvre le stream audio avec retry pour laisser CoreAudio se stabiliser"""
        device = self._find_input_device()
        max_retries = 3

        for attempt in range(max_retries):
            try:
                stream = sd.InputStream(
                    samplerate=self.samplerate,
                    channels=1,
                    blocksize=self.chunk_size,
                    callback=callback,
                    dtype='float32',
                    device=device
                )
                
                devnull = os.open(os.devnull, os.O_WRONLY)
                stderr_backup = os.dup(2)
                os.dup2(devnull, 2)
                try:
                    stream.start()
                finally:
                    os.dup2(stderr_backup, 2)
                    os.close(devnull)
                    os.close(stderr_backup)
                technical_log("wake", "waiting for wake word...")
                return stream
            except sd.PortAudioError:
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    try:
                        sd._terminate()
                        sd._initialize()
                    except Exception:
                        pass
                    device = self._find_input_device()
                else:
                    raise

    def listen(self):
        if not self.enabled:
            return True
        
        self.model = Model(
            wakeword_models=[self.model_name],
            inference_framework="onnx"
        )
        
        detected = False
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
                
                if score > self.threshold:
                    detected = True
                    break

        stream = self._open_stream(callback)

        try:
            while not detected:
                sd.sleep(100)
        except KeyboardInterrupt:
            raise
        finally:
            stream.stop()
            stream.close()
            sd.sleep(200)

        return True