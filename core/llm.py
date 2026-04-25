from core.config_manager import ConfigManager
from langchain_core.messages import SystemMessage, HumanMessage, AIMessageChunk
from langchain_ollama import ChatOllama
from utils.logging import technical_log


class LLM:
    def __init__(self):
        config = ConfigManager()

        self.model_name = config.get("llm", "model", default="mistral-small3.2:latest")
        self.base_url = config.get("llm", "base_url", default="http://localhost:11434")
        self.system_prompt = config.get("llm", "system_prompt", default="You are a helpful AI assistant.")

        technical_log("llm", f"connecting to Ollama: {self.model_name} @ {self.base_url}")

        self.llm = ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=config.get("llm", "temperature", default=0.7),
        )
        
        try:
            self.llm.invoke([HumanMessage(content="ping")])
            technical_log("llm", "Ollama connection OK")
        except Exception as e:
            technical_log("llm", f"Ollama connection failed: {e}")
            raise

    async def think(self, user_input, history=None):
        if history is None:
            history = []

        messages = [SystemMessage(content=self.system_prompt)]

        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                from langchain_core.messages import AIMessage
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_input))

        async for chunk in self.llm.astream(messages):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield chunk.content