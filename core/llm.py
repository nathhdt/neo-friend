import yaml
from mlx_lm import load, stream_generate
from utils.logging import technical_log


class LLM:
    def __init__(self):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        self.model_path = config["llm"]["model"]
        self.system_prompt = config["llm"]["system_prompt"]
        
        self.model_path = "models/mistral-small-v3"
        technical_log("llm", "loading llm model...")
        self.model, self.tokenizer = load(self.model_path, tokenizer_config={"fix_mistral_regex": True})
        technical_log("llm", "model loaded")

    async def think(self, user_input, history=None):
        """
        Génère une réponse en tenant compte de l'historique
        
        Args:
            user_input: Message actuel de l'utilisateur
            history: Liste de messages [{role, content}, ...] (optionnel)
        """
        if history is None:
            history = []
        
        system_message = {"role": "system", "content": self.system_prompt}
        messages = [system_message] + history + [{"role": "user", "content": user_input}]
        
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        for chunk in stream_generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=1024,
        ):
            yield chunk.text