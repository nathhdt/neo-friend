"""
Agent LangGraph.
Boucle ReAct : LLM → conditional edge → Tool execution → LLM.
"""
from datetime import datetime
from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage,
    AIMessageChunk, ToolMessage
)
from langgraph.graph import StateGraph, MessagesState, END
from typing import Literal, List, Dict

from neo.infra.config import ConfigManager
from neo.shared.colors import CYAN, RESET
from neo.shared.logging import step_start, step_ok, step_error


def _tool_log(message: str):
    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    print(f"\r\033[K{CYAN}{now} - [agent] {message}{RESET}")


class Agent:
    """Agent ReAct basé sur LangGraph avec tool calling"""

    def __init__(self, llm, tools: List, system_prompt: str):
        config = ConfigManager()

        self.max_iterations = int(config.get("agent", "max_iterations", default=5))
        self.system_prompt = system_prompt
        self.tools = tools
        self.tools_by_name = {t.name: t for t in tools}

        step_start("agent", "initializing agent")

        try:
            self.llm_with_tools = llm.bind_tools(tools) if tools else llm
            self.graph = self._build_graph()
            step_ok("agent", f"ready with {len(tools)} tools")
        except Exception as e:
            step_error("agent", f"initialization failed: {e}")
            raise

    def _build_graph(self):
        llm = self.llm_with_tools
        tools_by_name = self.tools_by_name

        async def agent_node(state: MessagesState):
            response = await llm.ainvoke(state["messages"])
            return {"messages": [response]}

        async def tool_node(state: MessagesState):
            last = state["messages"][-1]
            results = []

            for tc in last.tool_calls:
                name = tc["name"]
                args = tc["args"]

                _tool_log(f"→ {name}({args})")

                tool = tools_by_name.get(name)
                if tool:
                    try:
                        result = tool.invoke(args)
                    except Exception as e:
                        result = f"Erreur: {e}"
                        _tool_log(f"← {name} error: {e}")
                else:
                    result = f"Outil inconnu : {name}"

                _tool_log(f"← {name} result: {str(result).replace(chr(10), ' ')[:10]}...")
                results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tc["id"]
                ))

            return {"messages": results}

        def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return END

        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tool_node)
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")

        return graph.compile()

    def _build_messages(
        self,
        user_input: str,
        history: List[Dict[str, str]],
        memory_context: str = "",
    ) -> List:
        system_content = self.system_prompt
        if memory_context:
            system_content = f"{memory_context}\n\n{system_content}"

        messages = [SystemMessage(content=system_content)]

        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_input))
        return messages

    async def run(
        self,
        user_input: str,
        history: List[Dict[str, str]] = None,
        memory_context: str = "",
    ):
        if history is None:
            history = []

        messages = self._build_messages(user_input, history, memory_context)
        config = {"recursion_limit": self.max_iterations * 2 + 1}

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
