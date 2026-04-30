from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from huangclaw.agent.prompts import FINALIZER_PROMPT, SYSTEM_PROMPT
from huangclaw.config import Settings, get_settings
from huangclaw.llm import build_chat_model
from huangclaw.tools import get_builtin_tools


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int


class HuangClawAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.tools = get_builtin_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.llm = build_chat_model(self.settings).bind_tools(self.tools)
        self.final_llm = build_chat_model(self.settings)
        self.app = self._build_graph()

    def ask(self, question: str) -> str:
        result = self.app.invoke(
            {"messages": [HumanMessage(content=question)], "iterations": 0},
            config={"recursion_limit": self.settings.max_agent_iterations * 2 + 4},
        )
        return str(result["messages"][-1].content)

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", self._tools_node)
        graph.add_node("finalize", self._finalize_node)
        graph.set_entry_point("agent")
        graph.add_conditional_edges(
            "agent",
            self._route_after_agent,
            {"tools": "tools", "finalize": "finalize", END: END},
        )
        graph.add_edge("tools", "agent")
        graph.add_edge("finalize", END)
        return graph.compile()

    def _agent_node(self, state: AgentState) -> dict:
        response = self.llm.invoke([SystemMessage(content=SYSTEM_PROMPT), *state["messages"]])
        return {
            "messages": [response],
            "iterations": state.get("iterations", 0) + 1,
        }

    def _tools_node(self, state: AgentState) -> dict:
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", []) or []
        tool_messages: list[ToolMessage] = []

        for call in tool_calls:
            name = call.get("name")
            args = call.get("args") or {}
            tool_call_id = call.get("id", name or "tool")
            selected_tool = self.tool_map.get(name or "")

            if selected_tool is None:
                content = f"Unknown tool: {name}"
            else:
                try:
                    content = str(selected_tool.invoke(args))
                except Exception as exc:
                    content = f"Tool {name} failed: {exc}"

            tool_messages.append(
                ToolMessage(content=content, name=name or "unknown", tool_call_id=tool_call_id)
            )

        return {"messages": tool_messages}

    def _finalize_node(self, state: AgentState) -> dict:
        response = self.final_llm.invoke(
            [SystemMessage(content=FINALIZER_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    def _route_after_agent(self, state: AgentState) -> Literal["tools", "finalize", "__end__"]:
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", []) or []
        if not tool_calls:
            return END
        if state.get("iterations", 0) >= self.settings.max_agent_iterations:
            return "finalize"
        return "tools"


@lru_cache(maxsize=1)
def get_agent() -> HuangClawAgent:
    return HuangClawAgent()
