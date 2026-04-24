"""
Gestionnaire LLM refactorisé.
Utilise ConfigManager et corrige le bug du model_path hardcodé.
"""
from mlx_lm import load, stream_generate
from utils.logging import technical_log
from core.config_manager import ConfigManager


class LLM:
    def __init__(self):
        config = ConfigManager()
        
        self.model_name = config.get("llm", "model", default="mistral-small-v3")
        self.model_path = f"models/{self.model_name}"
        self.system_prompt = config.get("llm", "system_prompt", default="You are a helpful AI assistant.")        
        
        technical_log("llm", f"loading model: {self.model_path}")
        self.model, self.tokenizer = load(
            self.model_path, 
            tokenizer_config={"fix_mistral_regex": True}
        )
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