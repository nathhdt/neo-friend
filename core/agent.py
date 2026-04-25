"""
Agent LangGraph.
Boucle ReAct : LLM → conditional edge → Tool execution → LLM.
"""
from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage,
    AIMessageChunk, ToolMessage
)
from langgraph.graph import StateGraph, MessagesState, END
from typing import Literal, List, Dict
from utils.logging import technical_log


class Agent:
    """Agent ReAct basé sur LangGraph avec tool calling"""

    MAX_ITERATIONS = 5

    def __init__(self, llm, tools: List, system_prompt: str):
        """
        Args:
            llm: Instance ChatOllama
            tools: Liste de LangChain Tools
            system_prompt: System prompt pour l'agent
        """
        self.system_prompt = system_prompt
        self.tools = tools
        self.tools_by_name = {t.name: t for t in tools}

        self.llm_with_tools = llm.bind_tools(tools) if tools else llm

        self.graph = self._build_graph()

        tool_names = [t.name for t in tools]
        technical_log("agent", f"ready with {len(tools)} tools: {tool_names}")

    def _build_graph(self):
        """Construit le StateGraph : agent → tools → agent → ... → END"""

        llm = self.llm_with_tools
        tools_by_name = self.tools_by_name

        async def agent_node(state: MessagesState):
            """Appel LLM avec les tools bindés"""
            response = await llm.ainvoke(state["messages"])
            return {"messages": [response]}

        async def tool_node(state: MessagesState):
            """Exécute les tool calls demandés par le LLM"""
            last = state["messages"][-1]
            results = []

            for tc in last.tool_calls:
                name = tc["name"]
                args = tc["args"]
                technical_log("agent", f"→ {name}({args})")

                tool = tools_by_name.get(name)
                if tool:
                    try:
                        result = tool.invoke(args)
                    except Exception as e:
                        result = f"Erreur: {e}"
                        technical_log("agent", f"← {name} error: {e}")
                else:
                    result = f"Outil inconnu : {name}"

                technical_log("agent", f"← {name} done")
                results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tc["id"]
                ))

            return {"messages": results}

        def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
            """Route vers tools si le LLM veut appeler un outil, sinon END"""
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return END
        
        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tool_node)
        graph.set_entry_point("agent")
        graph.add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", END: END}
        )
        graph.add_edge("tools", "agent")

        return graph.compile()

    def _build_messages(self, user_input: str, history: List[Dict[str, str]]) -> List:
        """Construit la liste de messages LangChain depuis l'historique Neo"""
        messages = [SystemMessage(content=self.system_prompt)]

        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_input))
        return messages

    async def run(self, user_input: str, history: List[Dict[str, str]] = None):
        """
        Exécute l'agent et yield les chunks de texte de la réponse finale.

        Les tool calls sont exécutés silencieusement (loggés, pas streamés).
        Seule la réponse du LLM est streamée chunk par chunk.

        Yields:
            str: Chunks de texte au fur et à mesure
        """
        if history is None:
            history = []

        messages = self._build_messages(user_input, history)
        
        config = {"recursion_limit": self.MAX_ITERATIONS * 2 + 1}

        async for msg, metadata in self.graph.astream(
            {"messages": messages},
            stream_mode="messages",
            config=config
        ):
            if (
                metadata.get("langgraph_node") == "agent"
                and isinstance(msg, AIMessageChunk)
                and msg.content
                and not getattr(msg, "tool_call_chunks", None)
            ):
                yield msg.content