from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import AgentState
from baseline_nodes import naive_rag_node, naive_answer_node

workflow = StateGraph(AgentState)

workflow.add_node("naive_rag", naive_rag_node)
workflow.add_node("naive_answer", naive_answer_node)

workflow.add_edge(START, "naive_rag")
workflow.add_edge("naive_rag", "naive_answer")
workflow.add_edge("naive_answer", END)

memory = MemorySaver()
baseline_app = workflow.compile(checkpointer=memory)