import yaml
import torch
from silero_vad import load_silero_vad


class SileroVAD:
    def __init__(self):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        vad_cfg = config["vad"]

        self.sample_rate = config["stt"].get("samplerate", 16000)
        self.frame_size = vad_cfg.get("frame_size", 512)
        self.threshold = vad_cfg.get("threshold", 0.5)

        self.model = load_silero_vad()

    def is_speech(self, audio):
        if len(audio) != self.frame_size:
            return False

        audio_tensor = torch.tensor(audio, dtype=torch.float32)

        with torch.no_grad():
            prob = self.model(audio_tensor, self.sample_rate).item()

        return prob > self.threshold