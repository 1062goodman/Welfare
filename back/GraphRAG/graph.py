from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import AgentState
from nodes import (
    graphrag_search_node, 
    graphrag_answer_node)

# ---------------------------------------------------------
workflow = StateGraph(AgentState)
workflow.add_node("graphrag_search", graphrag_search_node)
workflow.add_node("graphrag_answer", graphrag_answer_node)

workflow.add_edge(START, "graphrag_search")
workflow.add_edge("graphrag_search", "graphrag_answer")
workflow.add_edge("graphrag_answer", END)

memory = MemorySaver()
graphrag_only_app = workflow.compile(checkpointer=memory)