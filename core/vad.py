import torch

from core.config_manager import ConfigManager
from silero_vad import load_silero_vad


class SileroVAD:
    def __init__(self):
        config = ConfigManager()

        self.sample_rate = config.get("vad", "samplerate", default=16000)
        self.frame_size = config.get("vad", "frame_size", default=512)
        self.threshold = config.get("vad", "threshold", default=0.5)

        self.model = load_silero_vad()

    def is_speech(self, audio):
        if len(audio) != self.frame_size:
            return False

        audio_tensor = torch.tensor(audio, dtype=torch.float32)

        with torch.no_grad():
            prob = self.model(audio_tensor, self.sample_rate).item()

        return prob > self.threshold