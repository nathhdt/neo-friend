"""
MemoryManager : mémoire persistante vectorielle pour Neo.

Pipeline :
  recall(query)  → top-K souvenirs pertinents injectés dans le prompt
  extract(history, llm) → extraction LLM des faits mémorables en fin de conversation
  store(facts)   → embedding + déduplication + stockage LanceDB
"""
import asyncio
import json
import numpy as np
import os

from core.config_manager import ConfigManager
from datetime import datetime
from pathlib import Path
from typing import List
from utils.logging import step_start, step_ok, step_error, technical_log

_devnull = os.open(os.devnull, os.O_WRONLY)
_stderr_backup = os.dup(2)
os.dup2(_devnull, 2)
try:
    import lancedb
finally:
    os.dup2(_stderr_backup, 2)
    os.close(_devnull)
    os.close(_stderr_backup)


SCHEMA = {
    "content": str,
    "importance": int,
    "created_at": str,
}

EXTRACT_PROMPT = """Tu es un système d'extraction de mémoire pour un assistant IA.

Analyse cette conversation et extrais les faits importants à mémoriser sur l'utilisateur :
préférences, habitudes, projets en cours, informations personnelles, contexte récurrent.

Conversation :
{history}

Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après, sans balises markdown :
{{
  "memories": [
    {{"content": "fait mémorable en une phrase", "importance": 4}},
    {{"content": "autre fait", "importance": 2}}
  ]
}}

Règles :
- importance : 1 (anecdotique) à 5 (crucial)
- Omets les faits génériques ou sans intérêt durable
- Maximum 5 faits par conversation
- Si rien à mémoriser, retourne {{"memories": []}}
"""


class _SilentStderr:
    """Context manager : redirige stderr fd vers /dev/null (coupe les warnings Rust/C++)."""
    def __enter__(self):
        self._devnull = os.open(os.devnull, os.O_WRONLY)
        self._backup = os.dup(2)
        os.dup2(self._devnull, 2)
    def __exit__(self, *_):
        os.dup2(self._backup, 2)
        os.close(self._devnull)
        os.close(self._backup)


class MemoryManager:

    def __init__(self):
        config = ConfigManager()
        mem_cfg = config.get("memory") or {}

        self.enabled = mem_cfg.get("enabled", True)
        if not self.enabled:
            technical_log("memory", "disabled")
            return

        db_path = Path(mem_cfg.get("db_path", "data/memory"))
        embedding_model = mem_cfg.get("model", "sentence-transformers/all-MiniLM-L6-v2")
        embedding_path = Path(mem_cfg.get("location", "models")) / embedding_model
        self.recall_top_k = mem_cfg.get("recall_top_k", 5)
        self.dedup_threshold = mem_cfg.get("dedup_threshold", 0.95)
        
        model_source = str(embedding_path) if embedding_path.exists() else embedding_model

        step_start("memory", f"loading embedding model: {embedding_model}")
        try:
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
            os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"

            devnull = os.open(os.devnull, os.O_WRONLY)
            stderr_backup = os.dup(2)
            os.dup2(devnull, 2)
            try:
                from sentence_transformers import SentenceTransformer
                self.encoder = SentenceTransformer(model_source)
            finally:
                os.dup2(stderr_backup, 2)
                os.close(devnull)
                os.close(stderr_backup)

            step_ok("memory", "embedding model ready")
        except Exception as e:
            step_error("memory", f"failed to load embedding model: {e}")
            raise

        step_start("memory", f"opening LanceDB at {db_path}")
        try:
            db_path.mkdir(parents=True, exist_ok=True)
            self.db = lancedb.connect(str(db_path))
            self.table = self._init_table()
            count = self.table.count_rows()
            step_ok("memory", f"ready ({count} memories)")
        except Exception as e:
            step_error("memory", f"failed to open LanceDB: {e}")
            raise

    def _init_table(self):
        """Ouvre ou crée la table memories avec le bon schéma."""
        if "memories" in self.db.table_names():
            return self.db.open_table("memories")
        
        dim = self.encoder.get_sentence_embedding_dimension()
        dummy = {
            "vector": np.zeros(dim, dtype=np.float32).tolist(),
            "content": "__init__",
            "importance": 0,
            "created_at": datetime.now().isoformat(),
        }
        table = self.db.create_table("memories", data=[dummy])
        table.delete("content = '__init__'")

        return table

    def _embed(self, text: str) -> np.ndarray:
        return self.encoder.encode(text, normalize_embeddings=True)

    def recall(self, query: str) -> str:
        """
        Recherche les souvenirs les plus pertinents pour une requête.

        Returns:
            Bloc texte à injecter dans le system prompt, ou "" si rien.
        """
        if not self.enabled:
            return ""

        try:
            count = self.table.count_rows()
            if count == 0:
                return ""

            vector = self._embed(query).tolist()
            k = min(self.recall_top_k, count)

            with _SilentStderr():
                results = (
                    self.table.search(vector)
                    .limit(k)
                    .to_list()
                )

            if not results:
                return ""
            
            facts = [r["content"] for r in results if r["importance"] >= 2]
            if not facts:
                facts = [r["content"] for r in results]

            lines = "\n".join(f"- {f}" for f in facts)
            return f"Ce que tu sais sur l'utilisateur :\n{lines}"

        except Exception as e:
            technical_log("memory", f"recall failed: {e}")
            return ""

    def store(self, facts: List[dict]):
        """
        Stocke une liste de faits après déduplication.

        Args:
            facts: [{"content": str, "importance": int}, ...]
        """
        if not self.enabled or not facts:
            return

        for fact in facts:
            content = fact.get("content", "").strip()
            importance = int(fact.get("importance", 3))

            if not content:
                continue

            vector = self._embed(content)
            
            try:
                count = self.table.count_rows()
                if count > 0:
                    with _SilentStderr():
                        results = (
                            self.table.search(vector.tolist())
                            .limit(1)
                            .to_list()
                        )
                    if results:
                        dist = results[0].get("_distance", 1.0)
                        cosine_sim = 1.0 - (dist ** 2) / 2.0
                        if cosine_sim >= self.dedup_threshold:
                            technical_log("memory", f"dedup skip: {content[:50]}...")
                            continue
            except Exception:
                pass

            self.table.add([{
                "vector": vector.tolist(),
                "content": content,
                "importance": importance,
                "created_at": datetime.now().isoformat(),
            }])
            technical_log("memory", f"stored [{importance}]: {content[:60]}")

    async def extract(self, history: List[dict], llm) -> None:
        """
        Extrait et stocke les faits mémorables d'une conversation.
        Appelé en fin de conversation, après le goodbye.

        Args:
            history: historique Neo [{"role": ..., "content": ...}]
            llm: instance ChatOllama (self.llm.llm depuis main)
        """
        if not self.enabled or not history:
            return
        
        lines = []
        for msg in history:
            role = "Utilisateur" if msg["role"] == "user" else "Neo"
            lines.append(f"{role}: {msg['content']}")
        history_text = "\n".join(lines)

        prompt = EXTRACT_PROMPT.format(history=history_text)

        try:
            from langchain_core.messages import HumanMessage
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:-1])

            data = json.loads(raw)
            facts = data.get("memories", [])

            if facts:
                technical_log("memory", f"extracting {len(facts)} facts from conversation")
                await asyncio.to_thread(self.store, facts)
            else:
                technical_log("memory", "nothing to memorize")

        except json.JSONDecodeError as e:
            technical_log("memory", f"extract JSON parse failed: {e}")
        except Exception as e:
            technical_log("memory", f"extract failed: {e}")