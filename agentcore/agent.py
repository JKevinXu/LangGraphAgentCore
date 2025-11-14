"""Core Agent implementation."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict, Annotated


class AgentState(TypedDict):
    """Agent state."""
    messages: Annotated[list, add_messages]


@dataclass
class AgentConfig:
    """Agent configuration."""
    model: str = "gpt-4"
    temperature: float = 0.7
    max_iterations: int = 10


class Agent:
    """Simple LangGraph agent."""
    
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.llm = ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature
        )
        self.tools = []
        self.graph = None
    
    def add_tool(self, tool):
        """Add a tool to the agent."""
        self.tools.append(tool)
        self.graph = None  # Rebuild graph
        return self
    
    def _build_graph(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._agent_node)
        
        if self.tools:
            workflow.add_node("tools", ToolNode(self.tools))
            workflow.add_conditional_edges(
                "agent",
                lambda state: "tools" if state["messages"][-1].tool_calls else "end"
            )
            workflow.add_edge("tools", "agent")
        else:
            workflow.add_edge("agent", END)
        
        workflow.set_entry_point("agent")
        return workflow.compile()
    
    def _agent_node(self, state: AgentState) -> Dict:
        """Agent reasoning node."""
        messages = state["messages"]
        
        if self.tools:
            llm_with_tools = self.llm.bind_tools(self.tools)
            response = llm_with_tools.invoke(messages)
        else:
            response = self.llm.invoke(messages)
        
        return {"messages": [response]}
    
    def run(self, message: str) -> str:
        """Run the agent."""
        if not self.graph:
            self.graph = self._build_graph()
        
        result = self.graph.invoke({
            "messages": [HumanMessage(content=message)]
        })
        
        return result["messages"][-1].content

