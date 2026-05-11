from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from neo.infra.config import ConfigManager
from neo.shared.logging import step_start, step_ok, step_error


class LLM:
    def __init__(self):
        config = ConfigManager()

        self.model_name = config.get("llm", "model", default="gpt-oss:20b")
        self.base_url = config.get("llm", "base_url", default="http://localhost:11434")
        self.system_prompt = config.get("llm", "system_prompt", default="You are a helpful AI assistant.")

        step_start("llm", f"connecting to Ollama: {self.model_name} @ {self.base_url}")

        self.llm = ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=config.get("llm", "temperature", default=0.7),
        )

        try:
            self.llm.invoke([HumanMessage(content="ping")])
            step_ok("llm", "Ollama connection OK")
        except Exception as e:
            step_error("llm", f"Ollama connection failed: {e}")
            raise
